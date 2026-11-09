import { expect, test } from '@playwright/test';

test('portada pública adaptable y accesos a reserva e ingreso', async ({ page }) => {
  let fail = false; let empty = false; let delay: Promise<void> | null = null; const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !message.text().includes('Failed to load resource')) errors.push(message.text()); });
  page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') errors.push(request.url()); });
  page.on('response', response => { const url = new URL(response.url()); if (response.status() >= 400 && !url.pathname.endsWith('/auth/refresh') && !(fail && url.pathname.endsWith('/publico/consultorio'))) errors.push(`${response.status()} ${url.pathname}`); });
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({status: 401, json: {detail: 'No autorizado'}});
    if (delay && path.includes('/publico/')) await delay;
    if (path.endsWith('/publico/consultorio')) return fail ? route.fulfill({status: 500, json: {}}) : route.fulfill({json: {nombre: 'Consultorio Ejemplo', direccion: null, telefono: null, zona_horaria: 'America/Argentina/Buenos_Aires'}});
    if (path.endsWith('/publico/prestaciones')) return route.fulfill({json: empty ? [] : [{id: 1, nombre: 'Consulta odontológica', duracion_min: 30}, {id: 2, nombre: 'Limpieza dental', duracion_min: 40}]});
    return route.fulfill({json: []});
  });
  for (const [name, width, height] of [['mobile', 390, 844], ['desktop', 1440, 900]] as const) {
    fail = false; await page.setViewportSize({width, height}); await page.goto('/');
    await expect(page.getByRole('heading', {name: /cuidar tu sonrisa/i})).toBeVisible();
    await expect(page.getByRole('banner')).toHaveCount(1);
    await expect(page.getByText('Consulta odontológica')).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    await expect(page.getByRole('link', {name: 'Ver turnos disponibles'}).first()).toHaveAttribute('href', '/reservar');
    await expect(page.getByRole('link', {name: 'Ingresar a mi cuenta'})).toHaveAttribute('href', '/ingresar');
    await page.screenshot({path: `test-results/landing/portada-${name}.png`, fullPage: true});
    fail = true; await page.reload(); await expect(page.getByRole('alert')).toContainText('No pudimos cargar');
    await expect(page.getByRole('link', {name: 'Ver turnos disponibles'}).first()).toBeVisible();
    await page.screenshot({path: `test-results/landing/error-${name}.png`, fullPage: true});
    fail = false; await page.getByRole('button', {name: 'Volver a cargar'}).click();
    await expect(page.getByRole('alert')).toHaveCount(0);
    await page.keyboard.press('Tab');
    expect(await page.evaluate(() => document.activeElement?.tagName)).not.toBe('BODY');
    empty = true; await page.reload(); await expect(page.getByText('No hay prestaciones para mostrar por el momento.')).toBeVisible();
    await page.screenshot({path: `test-results/landing/vacio-${name}.png`, fullPage: true}); empty = false;
    let release!: () => void; delay = new Promise(resolve => { release = resolve; });
    await page.reload({waitUntil: 'domcontentloaded'}); await expect(page.getByText('Estamos cargando los datos del consultorio…')).toBeVisible();
    await page.screenshot({path: `test-results/landing/carga-${name}.png`, fullPage: true}); release(); delay = null;
    await expect(page.getByText('Consulta odontológica')).toBeVisible();
  }
  await page.goto('/');
  await page.getByRole('link', {name: 'Ver turnos disponibles'}).first().click();
  await expect(page).toHaveURL(/\/reservar$/);
  await expect(page.getByRole('heading', {name: 'Reservá tu turno'})).toBeVisible();
  await page.goto('/');
  await page.getByRole('link', {name: 'Ingresar a mi cuenta'}).click();
  await expect(page).toHaveURL(/\/ingresar$/);
  await expect(page.getByLabel('Usuario o correo')).toBeVisible();
  expect(errors).toEqual([]);
});
