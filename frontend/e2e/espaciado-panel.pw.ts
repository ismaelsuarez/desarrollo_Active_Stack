import { expect, test } from '@playwright/test';

for (const [width, height] of [[1440, 900], [390, 844]]) {
  test(`controles separados y alineados a ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height });
    await page.route('**/api/v1/**', async route => {
      const path = new URL(route.request().url()).pathname;
      if (path.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test' } });
      if (path.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', email_verificado: true } });
      if (path.endsWith('/publico/consultorio')) return route.fulfill({ json: { nombre: 'Consultorio de ejemplo', zona_horaria: 'America/Argentina/Buenos_Aires' } });
      if (path.endsWith('/usuarios')) return route.fulfill({ json: [{ id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', activo: true }] });
      if (path.endsWith('/prestaciones')) return route.fulfill({ json: [{ id: 1, nombre: 'Consulta', duracion_min: 30, activa: true, sugerida: false }] });
      if (path.endsWith('/solicitudes-vinculacion') || path.endsWith('/pacientes')) return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
      return route.fulfill({ json: [] });
    });
    await page.goto('/configuracion');
    const editStaff = page.getByRole('button', { name: 'Editar admin' });
    const deactivateStaff = page.getByRole('button', { name: 'Desactivar admin' });
    await expect(editStaff).toBeVisible();
    const staffFirst = await editStaff.boundingBox(); const staffSecond = await deactivateStaff.boundingBox();
    expect(staffFirst && staffSecond && (staffSecond.x - (staffFirst.x + staffFirst.width) >= 8 || staffSecond.y - (staffFirst.y + staffFirst.height) >= 8)).toBeTruthy();
    const edit = page.getByRole('button', { name: 'Editar Consulta' });
    const deactivate = page.getByRole('button', { name: 'Desactivar Consulta' });
    await expect(edit).toBeVisible();
    const first = await edit.boundingBox(); const second = await deactivate.boundingBox();
    expect(first && second && (second.x - (first.x + first.width) >= 8 || second.y - (first.y + first.height) >= 8)).toBeTruthy();
    await page.screenshot({ path: `test-results/espaciado/prestaciones-${width}.png`, fullPage: true });

    await page.goto('/solicitudes');
    const state = page.getByRole('combobox', { name: 'Estado', exact: true });
    const refresh = page.getByRole('button', { name: 'Actualizar solicitudes' });
    await expect(state).toBeVisible();
    const selectBox = await state.boundingBox(); const buttonBox = await refresh.boundingBox();
    expect(selectBox && buttonBox).toBeTruthy();
    if (selectBox && buttonBox) {
      if (buttonBox.y >= selectBox.y + selectBox.height) expect(buttonBox.y - (selectBox.y + selectBox.height)).toBeGreaterThanOrEqual(8);
      else {
        expect(Math.abs((selectBox.y + selectBox.height) - (buttonBox.y + buttonBox.height))).toBeLessThanOrEqual(2);
        expect(buttonBox.x - (selectBox.x + selectBox.width)).toBeGreaterThanOrEqual(8);
      }
    }
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await page.screenshot({ path: `test-results/espaciado/solicitudes-${width}.png`, fullPage: true });
  });
}
