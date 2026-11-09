import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'example-token' } });
    if (url.pathname.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'recepcion', email: 'recepcion@example.test', rol: 'recepcion', email_verificado: true } });
    if (url.pathname.endsWith('/publico/consultorio')) return route.fulfill({ json: { zona_horaria: 'America/Argentina/Buenos_Aires' } });
    if (url.pathname.endsWith('/notificaciones/indicadores')) return route.fulfill({ json: { fallidas: 1, programada_mas_antigua_segundos: 720, enviando: 2, enviando_mas_antigua_segundos: 1080, correos_del_dia: 420, limite_diario: 500, alerta: true, ultimo_barrido: { iniciado_en: '2020-01-01T00:00:00Z' } } });
    if (url.pathname.endsWith('/notificaciones') && url.searchParams.get('canal') === 'whatsapp') return route.fulfill({ json: [{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }] });
    if (url.pathname.endsWith('/notificaciones')) return route.fulfill({ json: [] });
    if (url.pathname.endsWith('/turnos/42')) return route.fulfill({ json: { id: 42, estado: 'pendiente', paciente_nombre: 'Ana', paciente_apellido: 'Pérez', acciones_permitidas: ['confirmar', 'cancelar', 'liberar'], es_sobreturno: false } });
    if (url.pathname.endsWith('/turnos')) return route.fulfill({ json: [] });
    return route.fulfill({ status: 404, json: {} });
  });
  await page.goto('/notificaciones');
  await expect(page.getByText('Recordatorio')).toBeVisible();
});

test('navega entre bandejas con Tab y Enter', async ({ page }) => {
  const whatsapp = page.getByRole('button', { name: 'WhatsApp preparado', exact: true });
  await whatsapp.focus();
  await page.keyboard.press('Tab');
  const email = page.getByRole('button', { name: 'Correos fallidos', exact: true });
  await expect(email).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByText('No hay notificaciones en esta bandeja.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Correos fallidos' })).toBeVisible();
  await page.keyboard.press('Shift+Tab');
  await expect(whatsapp).toBeFocused();
});

test('visualiza la bandeja en celular y escritorio', async ({ page }) => {
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await expect(page.getByRole('heading', { name: 'Notificaciones', exact: true })).toBeVisible();
    if (name === 'mobile') {
      await page.getByRole('button', { name: '☰ Menú' }).click();
      const nav = page.getByRole('navigation', { name: 'Navegación principal' });
      await expect(nav.getByRole('link', { name: 'Notificaciones' })).toHaveAttribute('aria-current', 'page');
      await page.getByRole('button', { name: '☰ Menú' }).click();
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/notifications/${name}.png`, fullPage: true });
  }
});

test('visualiza turnos y salud en celular y escritorio', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await page.route('**/api/v1/auth/me', route => route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', email_verificado: true } }));
  await page.route('**/api/v1/turnos?*', route => route.fulfill({ json: [{ id: 42, paciente_nombre: 'Ana', paciente_apellido: 'Pérez', inicio: '2026-11-06T12:00:00Z', acciones_permitidas: ['confirmar', 'cancelar', 'liberar'] }] }));
  await page.reload();
  await expect(page.getByRole('heading', { name: 'Notificaciones', exact: true })).toBeVisible();
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto('/sin-confirmar');
    await expect(page.getByText('Ana Pérez')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/notifications/turnos-${name}.png`, fullPage: true });
    await page.getByRole('button', { name: 'Ver turno 42' }).click();
    await expect(page.getByRole('button', { name: 'Liberar turno' })).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/detalle-${name}.png`, fullPage: true });
    await page.goto('/estado-operativo');
    await expect(page.getByText(/Alerta de cuota/)).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/notifications/salud-${name}.png`, fullPage: true });
  }
  expect(errors).toEqual([]);
});

test('visualiza correo fallido en ambos tamaños', async ({ page }) => {
  await page.route('**/api/v1/notificaciones?*', route => {
    const url = new URL(route.request().url());
    return route.fulfill({ json: url.searchParams.get('canal') === 'email' ? [{ id: 9, turno_id: 42, tipo: 'solicitud_confirmacion', programada_para: '2026-11-06T12:00:00Z' }] : [{ id: 8, turno_id: 42, tipo: 'recordatorio', programada_para: '2026-11-06T12:00:00Z' }] });
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.getByRole('button', { name: 'Correos fallidos', exact: true }).click();
    await expect(page.getByText('Solicitud de confirmación')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/correo-${name}.png`, fullPage: true });
  }
});

test('muestra correo vacío y error recuperable', async ({ page }) => {
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.getByRole('button', { name: 'Correos fallidos', exact: true }).click();
    await expect(page.getByText('No hay notificaciones en esta bandeja.')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/correo-vacio-${name}.png`, fullPage: true });
    await page.getByRole('button', { name: 'WhatsApp preparado', exact: true }).click();
    await expect(page.getByText('Recordatorio')).toBeVisible();
  }
  await page.route('**/api/v1/notificaciones?*', route => route.fulfill({ status: 500, json: { detail: 'error de prueba' } }));
  await page.getByRole('button', { name: 'Correos fallidos', exact: true }).click();
  await expect(page.getByRole('alert')).toHaveText(/No pudimos cargar/);
  await page.screenshot({ path: 'test-results/notifications/error-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: 'test-results/notifications/error-mobile.png', fullPage: true });
});

test('estados secundarios de WhatsApp en ambos tamaños', async ({ page }) => {
  await page.route('**/api/v1/notificaciones/8/whatsapp', route => route.fulfill({ json: { enlace_whatsapp: 'https://wa.me/5491112345678?text=Hola' } }));
  await page.evaluate(() => { window.open = () => null; });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.getByRole('button', { name: 'Abrir WhatsApp 8' }).click();
    await expect(page.getByRole('link', { name: 'Abrir enlace seguro de WhatsApp' })).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/popup-${name}.png`, fullPage: true });
    await page.route('**/api/v1/notificaciones/8/marcar-enviada', route => route.fulfill({ status: 409, json: { detail: 'conflicto simulado' } }));
    await page.getByRole('button', { name: 'Marcar enviada 8' }).click();
    await expect(page.getByText('La notificación cambió. Revisá su estado.')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/conflicto-${name}.png`, fullPage: true });
    await page.unroute('**/api/v1/notificaciones/8/marcar-enviada');
    await page.route('**/api/v1/notificaciones/8/marcar-enviada', route => route.abort('failed'));
    await page.getByRole('button', { name: 'Marcar enviada 8' }).click();
    await expect(page.getByText('No pudimos confirmar el resultado. Revisá el estado antes de reintentar.')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/incierto-${name}.png`, fullPage: true });
    await page.unroute('**/api/v1/notificaciones/8/marcar-enviada');
  }
});

test('salud sin barridos y error en ambos tamaños', async ({ page }) => {
  await page.route('**/api/v1/auth/me', route => route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', email_verificado: true } }));
  await page.route('**/api/v1/notificaciones/indicadores', route => route.fulfill({ json: { fallidas: 0, programada_mas_antigua_segundos: null, enviando: 0, enviando_mas_antigua_segundos: null, correos_del_dia: 0, limite_diario: 500, alerta: false, ultimo_barrido: null } }));
  await page.reload();
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.route('**/api/v1/notificaciones/indicadores', route => route.fulfill({ json: { fallidas: 0, programada_mas_antigua_segundos: null, enviando: 0, enviando_mas_antigua_segundos: null, correos_del_dia: 0, limite_diario: 500, alerta: false, ultimo_barrido: null } }));
    await page.goto('/estado-operativo');
    await expect(page.getByText('Sin barridos registrados.')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/salud-sin-barrido-${name}.png`, fullPage: true });
    await page.route('**/api/v1/notificaciones/indicadores', route => route.fulfill({ status: 500, json: { detail: 'error simulado' } }));
    await page.reload();
    await expect(page.getByText('No pudimos cargar los indicadores.')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/salud-error-${name}.png`, fullPage: true });
    await page.unroute('**/api/v1/notificaciones/indicadores');
  }
});

test('carga y consola de pantallas principales', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
  page.on('requestfailed', request => errors.push(`${request.url()}: ${request.failure()?.errorText}`));
  await page.route('**/api/v1/notificaciones?*', async route => {
    await new Promise(resolve => setTimeout(resolve, 1200));
    await route.fulfill({ json: [] });
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({ width, height });
    await page.goto('/notificaciones');
    await expect(page.getByText('Cargando notificaciones…')).toBeVisible();
    await page.screenshot({ path: `test-results/notifications/carga-${name}.png`, fullPage: true });
    await expect(page.getByText('No hay notificaciones en esta bandeja.')).toBeVisible();
    await page.getByRole('button', { name: 'Correos fallidos', exact: true }).click();
    await expect(page.getByText('Cargando notificaciones…')).toBeVisible();
    await expect(page.getByText('No hay notificaciones en esta bandeja.')).toBeVisible();
  }
  expect(errors).toEqual([]);
});
