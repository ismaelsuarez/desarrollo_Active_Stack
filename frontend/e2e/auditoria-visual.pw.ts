import { expect, test } from '@playwright/test';

test('estados corregidos de auditoría en móvil y escritorio', async ({ page }) => {
  let rol = 'paciente';
  let fallaConsultorio = false;
  let fallaProfesionales = false;
  let resolverBusqueda: (() => void) | undefined;
  const errores: string[] = [];
  page.on('pageerror', error => errores.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !message.text().includes('Failed to load resource')) errores.push(message.text()); });
  page.on('response', response => {
    const path = new URL(response.url()).pathname;
    const esperado = (fallaConsultorio && path.endsWith('/publico/consultorio'))
      || (fallaProfesionales && path.endsWith('/publico/profesionales'))
      || path.endsWith('/auth/restablecer-password');
    if (response.status() >= 400 && !esperado) errores.push(`${response.status()} ${path}`);
  });
  page.on('requestfailed', request => {
    if (request.failure()?.errorText !== 'net::ERR_ABORTED') errores.push(request.url());
  });
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test' } });
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'ana', email: 'a@example.test', rol, email_verificado: true } });
    if (path.endsWith('/publico/consultorio')) return fallaConsultorio ? route.fulfill({ status: 500, json: {} }) : route.fulfill({ json: { nombre: 'Consultorio', telefono: null, zona_horaria: 'America/Argentina/Buenos_Aires' } });
    if (path.endsWith('/publico/profesionales')) return fallaProfesionales ? route.fulfill({ status: 500, json: {} }) : route.fulfill({ json: [{ id: 2, nombre: 'Ana Pérez' }] });
    if (path.endsWith('/publico/prestaciones')) return route.fulfill({ json: [{ id: 1, nombre: 'Consulta', duracion_min: 30 }] });
    if (path.endsWith('/publico/disponibilidad')) {
      await new Promise<void>(resolve => { resolverBusqueda = resolve; });
      return route.fulfill({ json: [] });
    }
    if (path.endsWith('/turnos')) return route.fulfill({ json: [{ id: 3, profesional_id: 2, prestacion_id: 1, prestacion_nombre: 'Consulta', inicio: '2026-11-20T13:00:00Z', fin: '2026-11-20T13:30:00Z', estado: 'pendiente', acciones_permitidas: ['reprogramar'] }] });
    if (path.endsWith('/auth/restablecer-password')) return route.fulfill({ status: 503, json: {} });
    if (path.endsWith('/notificaciones/8/whatsapp')) return route.fulfill({ json: { enlace_whatsapp: 'https://example.test/' } });
    if (path.endsWith('/notificaciones')) return route.fulfill({ json: [{ id: 8, turno_id: 3, tipo: 'recordatorio', programada_para: '2026-11-20T13:00:00Z' }] });
    if (path.endsWith('/notificaciones/indicadores')) return route.fulfill({ json: { fallidas: 0, enviando: 0 } });
    if (path.endsWith('/indicadores/ausentismo')) return route.fulfill({ json: { resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] } });
    if (path.endsWith('/profesionales')) return route.fulfill({ json: [] });
    return route.fulfill({ json: [] });
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    const shot = async (state: string) => page.screenshot({ path: `test-results/auditoria/${state}-${name}.png`, fullPage: true });
    await page.setViewportSize({ width, height });
    rol = 'paciente'; fallaConsultorio = false; fallaProfesionales = false;
    await page.goto('/reservar');
    await page.getByLabel('Prestación').selectOption('1');
    await page.getByLabel('Profesional').selectOption('2');
    await page.getByLabel('Fecha').fill('2026-11-20');
    if (name === 'desktop') {
      const positions = await Promise.all(['Prestación', 'Profesional', 'Fecha'].map(label => page.getByLabel(label).evaluate(element => element.getBoundingClientRect().top)));
      expect(Math.max(...positions) - Math.min(...positions)).toBeLessThanOrEqual(4);
    }
    await page.getByRole('button', { name: 'Buscar horarios' }).click();
    await expect(page.getByText('Buscando horarios…')).toBeVisible();
    await shot('busqueda');
    resolverBusqueda?.();
    await expect(page.getByText('No encontramos horarios para esta fecha.')).toBeVisible();

    fallaConsultorio = true;
    await page.goto('/reservar');
    await expect(page.getByRole('button', { name: 'Volver a cargar' })).toBeVisible();
    await shot('error-catalogo');

    fallaConsultorio = false; fallaProfesionales = true;
    await page.goto('/mis-turnos');
    await expect(page.getByText('Profesional no disponible')).toBeVisible();
    await expect(page.getByText(/No pudimos cargar los datos de profesionales/)).toBeVisible();
    await shot('turnos-parciales');
    expect(await page.getByRole('heading', { name: 'Mis turnos' }).evaluate(element => element === document.activeElement)).toBe(true);
    await page.getByRole('button', { name: 'Reprogramar' }).click();
    await page.getByLabel('Nueva fecha').fill('2026-11-21');
    await page.getByRole('button', { name: 'Buscar horarios' }).click();
    await expect(page.getByText('Buscando horarios…')).toBeVisible();
    await shot('reprogramacion');
    resolverBusqueda?.();
    await expect(page.getByText('No encontramos horarios para esta fecha.')).toBeVisible();

    fallaProfesionales = false;
    await page.goto('/restablecer-password#token=prueba');
    await page.getByLabel('Nueva contraseña').fill('contraseña-ejemplo');
    await page.getByRole('button', { name: 'Restablecer contraseña' }).click();
    await expect(page.getByRole('alert')).toContainText('No pudimos confirmar el cambio');
    await shot('restablecimiento-incierto');

    await page.goto('/paciente');
    await expect(page.getByText('Reservá un turno o revisá tus turnos desde el menú.')).toBeVisible();
    if (name === 'desktop') {
      const positions = await page.getByRole('navigation', { name: 'Navegación de la cuenta' }).getByRole('link').evaluateAll(elements => elements.map(element => element.getBoundingClientRect().top));
      expect(new Set(positions).size).toBe(1);
    }
    await shot('inicio-paciente');

    rol = 'administrador';
    await page.goto('/ausentismo');
    await expect(page.getByText('Sin datos para este período.')).toBeVisible();
    await shot('ausentismo');

    rol = 'recepcion';
    await page.goto('/notificaciones');
    await page.getByRole('button', { name: 'Abrir WhatsApp 8' }).click();
    await expect(page.getByRole('alert')).toContainText('el enlace no es válido');
    await shot('whatsapp');
  }
  expect(errores).toEqual([]);
});
