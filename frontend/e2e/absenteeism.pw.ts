import { expect, test } from '@playwright/test';

test('presenta el indicador en móvil y escritorio sin desbordes ni errores', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await page.route('**/api/v1/**', route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test' } });
    if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'test@example.test', rol: 'administrador', email_verificado: true } });
    if (path.endsWith('/publico/consultorio')) return route.fulfill({ json: { zona_horaria: 'America/Argentina/Buenos_Aires' } });
    if (path.endsWith('/profesionales')) return route.fulfill({ json: [{ id: 1, nombre: 'Ana', apellido: 'Pérez' }] });
    if (path.endsWith('/notificaciones/indicadores')) return route.fulfill({ json: { fallidas: 0, enviando: 0 } });
    if (path.endsWith('/turnos')) return route.fulfill({ json: [] });
    if (path.endsWith('/notificaciones')) return route.fulfill({ json: [] });
    if (path.endsWith('/indicadores/ausentismo')) {
      const counts = { ausentes: 12, atendidos: 84, cancelados: 8, liberados: 5, sin_cierre: 3, tasa: 0.125 };
      return route.fulfill({ json: { resumen: counts, evolucion: [{ ...counts, mes: '2026-08', tasa: 0.1 }, { ...counts, mes: '2026-09', tasa: 0.15 }, { ...counts, mes: '2026-10' }], profesionales: [{ ...counts, profesional_id: 1, nombre: 'Ana Pérez' }] } });
    }
    return route.fulfill({ status: 404, json: {} });
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto('/ausentismo');
    await expect(page.getByRole('cell', { name: 'Ana Pérez' })).toBeVisible();
    if (name === 'mobile') {
      await page.getByRole('button', { name: '☰ Menú' }).click();
      const nav = page.getByRole('navigation', { name: 'Navegación principal' });
      const current = nav.getByRole('link', { name: 'Ausentismo' });
      await expect(current).toHaveAttribute('aria-current', 'page');
      await expect(current).toBeVisible();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/absenteeism/${name}.png`, fullPage: true });
    if (name === 'mobile') {
      const nav = page.getByRole('navigation', { name: 'Navegación principal' });
      await nav.getByRole('link', { name: 'Inicio' }).focus();
      await page.keyboard.press('Tab');
      await expect(nav.getByRole('link', { name: 'Mi cuenta' })).toBeFocused();
      await page.getByRole('button', { name: '☰ Menú' }).click();
    }
  }
  expect(errors).toEqual([]);
  let failed = false;
  await page.route('**/api/v1/indicadores/ausentismo?*', route => failed
    ? route.fulfill({ status: 500, json: { detail: 'error de prueba' } })
    : route.fulfill({ json: { resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] } }));
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    failed = false;
    await page.goto('/ausentismo');
    await expect(page.getByText('Sin datos para este período.')).toBeVisible();
    await page.screenshot({ path: `test-results/absenteeism/vacio-${name}.png`, fullPage: true });
    failed = true;
    await page.getByRole('button', { name: 'Consultar' }).click();
    await expect(page.getByRole('alert')).toHaveText(/No pudimos cargar el indicador/);
    await page.screenshot({ path: `test-results/absenteeism/error-${name}.png`, fullPage: true });
    failed = false;
    await page.getByRole('button', { name: 'Reintentar', exact: true }).click();
    await expect(page.getByText('Sin datos para este período.')).toBeVisible();
  }
  await page.route('**/api/v1/indicadores/ausentismo?*', async route => {
    await new Promise(resolve => setTimeout(resolve, 1000));
    await route.fulfill({ json: { resumen: { ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null }, evolucion: [], profesionales: [] } });
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto('/ausentismo');
    await expect(page.getByRole('status')).toHaveText('Cargando indicador…');
    await page.screenshot({ path: `test-results/absenteeism/carga-${name}.png`, fullPage: true });
    await expect(page.getByText('Sin datos para este período.')).toBeVisible();
  }
});
