import { expect, test } from '@playwright/test';

test('historial paginado en móvil y escritorio', async ({ page }) => {
  let fail = false;
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') errors.push(request.url()); });
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()); const path = url.pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({json: {access_token: 'test'}});
    if (path.endsWith('/auth/me')) return route.fulfill({json: {id: 1, consultorio_id: 1, nombre_usuario: 'recepcion', email: 'r@example.test', rol: 'recepcion', email_verificado: true}});
    if (path.endsWith('/pacientes/2/turnos')) {
      if (url.searchParams.get('offset') === '20') return fail ? route.fulfill({status: 503, json: {}}) : route.fulfill({json: [{id: 21, inicio: '2026-08-12', estado: 'atendido'}]});
      return route.fulfill({json: Array.from({length: 21}, (_, i) => ({id: i + 1, inicio: `2026-11-${String(i + 1).padStart(2, '0')}`, estado: 'atendido'}))});
    }
    if (path.endsWith('/pacientes/2')) return route.fulfill({json: {id: 2, nombre: 'María', apellido: 'Pérez', dni: '12345678', telefono: '011 5555-0101', email: 'maria@example.com', activo: true}});
    if (path.endsWith('/pacientes')) return route.fulfill({json: {items: [{id: 2, nombre: 'María', apellido: 'Pérez', activo: true}], total: 1}});
    return route.fulfill({json: []});
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    await page.setViewportSize({width, height}); await page.goto('/pacientes');
    await page.getByRole('button', {name: 'María Pérez'}).click();
    await expect(page.getByText('Página 1')).toBeVisible();
    await page.screenshot({path: `test-results/historial/primera-${name}.png`, fullPage: true});
    fail = true; await page.getByRole('button', {name: 'Siguiente historial'}).click();
    await expect(page.getByRole('button', {name: 'Reintentar historial'})).toBeVisible();
    await page.screenshot({path: `test-results/historial/error-${name}.png`, fullPage: true});
    fail = false; await page.getByRole('button', {name: 'Reintentar historial'}).click();
    await expect(page.getByText('Página 2')).toBeVisible();
    await page.screenshot({path: `test-results/historial/siguiente-${name}.png`, fullPage: true});
  }
  expect(errors).toEqual([]);
});
