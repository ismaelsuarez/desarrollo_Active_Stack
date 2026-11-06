import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('**/api/v1/**', async route => {
    const { pathname } = new URL(route.request().url());
    if (pathname.endsWith('/auth/refresh')) return route.fulfill({ json: { access_token: 'test-token' } });
    if (pathname.endsWith('/auth/me')) return route.fulfill({ json: { id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', email_verificado: true } });
    if (pathname.endsWith('/consultorio')) return route.fulfill({ json: { modo_liberacion: 'manual', horas_confirmacion: 48, horas_recordatorio: 24, horas_liberacion: 12, horas_limite_paciente: 4, telefono: null, minutos_granularidad: 15, dias_anticipacion_maxima: 30, max_turnos_activos_paciente: 3 } });
    if (pathname.endsWith('/usuarios') && route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      return route.fulfill({ json: { id: 42, nombre_usuario: body.nombre_usuario, email: body.email, rol: body.rol, activo: true } });
    }
    return route.fulfill({ json: [] });
  });
  await page.goto('/configuracion');
  await expect(page.getByText('No hay personal registrado.')).toBeVisible();
});

test('recorre el formulario de personal con Tab y envía con Enter', async ({ page }) => {
  const user = page.getByLabel('Usuario', { exact: true });
  await user.focus();
  await page.keyboard.type('ana');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Correo', { exact: true })).toBeFocused();
  await page.keyboard.type('ana@example.test');
  await page.keyboard.press('Tab');
  await expect(page.getByLabel('Contraseña inicial')).toBeFocused();
  await page.keyboard.type('clave-ejemplo-123');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('combobox', { name: 'Rol', exact: true })).toBeFocused();
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Crear personal' })).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.getByText('Personal guardado.')).toBeVisible();
  await expect(page.getByText(/ana@example\.test/)).toBeVisible();
});

test('permite dígitos y rechaza notación exponencial en duración', async ({ page }) => {
  const duration = page.getByLabel('Duración en minutos');
  await duration.focus();
  await page.keyboard.type('1e2');
  await expect(duration).toHaveValue('12');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('button', { name: 'Crear prestación' })).toBeFocused();
  await page.keyboard.press('Shift+Tab');
  await expect(duration).toBeFocused();
});
