import { expect, test } from '@playwright/test';

test('panel de equipo en móvil y escritorio', async ({ page }) => {
  test.setTimeout(90_000);
  const errors: string[] = []; let currentScreen = '';
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', message => { if (message.type() === 'error' && !message.text().includes('Failed to load resource')) errors.push(message.text()); });
  page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') errors.push(request.url()); });
  page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
  await page.route('**/api/v1/**', async route => {
    const url = new URL(route.request().url()); const path = url.pathname;
    if (path.endsWith('/auth/refresh')) return route.fulfill({json: {access_token: 'test'}});
    if (path.endsWith('/auth/me')) return route.fulfill({json: {id: 1, consultorio_id: 1, nombre_usuario: 'admin', email: 'admin@example.test', rol: 'administrador', email_verificado: true}});
    if (path.endsWith('/publico/consultorio')) return route.fulfill({json: {nombre: 'Consultorio de ejemplo', zona_horaria: 'America/Argentina/Buenos_Aires'}});
    if (path.endsWith('/agenda/contexto')) return route.fulfill({json: {profesional_id: null}});
    if (path.endsWith('/profesionales') && currentScreen === 'agenda') return route.fulfill({json: [{id: 2, nombre: 'Profesional', apellido: 'de ejemplo', activo: true}]});
    if (path.endsWith('/agenda')) return route.fulfill({json: [{id: 1, inicio: '2026-11-09T12:00:00Z', paciente_nombre: 'Paciente', paciente_apellido: 'de ejemplo', estado: 'pendiente', es_sobreturno: false, acciones_permitidas: []}]});
    if (path.endsWith('/consultorio')) return route.fulfill({json: {modo_liberacion: 'manual', horas_confirmacion: 48, horas_recordatorio: 24, horas_liberacion: 12, horas_limite_paciente: 4, telefono: null, minutos_granularidad: 15, dias_anticipacion_maxima: 30, max_turnos_activos_paciente: 3}});
    if (path.endsWith('/pacientes') || path.endsWith('/solicitudes-vinculacion')) return route.fulfill({json: {items: [], total: 0, limit: 20, offset: 0}});
    if (path.endsWith('/notificaciones/indicadores')) return route.fulfill({json: {fallidas: 0, programada_mas_antigua_segundos: null, enviando: 0, enviando_mas_antigua_segundos: null, correos_del_dia: 0, limite_diario: 500, alerta: false, ultimo_barrido: null}});
    if (path.endsWith('/indicadores/ausentismo')) return route.fulfill({json: {resumen: {ausentes: 0, atendidos: 0, cancelados: 0, liberados: 0, sin_cierre: 0, tasa: null}, evolucion: [], profesionales: []}});
    return route.fulfill({json: []});
  });
  const screens = [['inicio','/administrador','Hola, admin'],['cuenta','/cuenta','Mi cuenta'],['agenda','/agenda','Agenda'],['pacientes','/pacientes','Pacientes'],['solicitudes','/solicitudes','Solicitudes de vinculación'],['notificaciones','/notificaciones','Notificaciones'],['estado','/estado-operativo','Salud operativa'],['configuracion','/configuracion','Configuración del consultorio'],['ausentismo','/ausentismo','Indicador de ausentismo']] as const;
  for (const [size,width,height] of [['mobile',390,844],['desktop',1440,900]] as const) {
    await page.setViewportSize({width,height});
    for (const [name,path,title] of screens) {
      currentScreen = name; await page.goto(path); await expect(page.getByRole('heading',{name:title,exact:true}).first()).toBeVisible();
      if (name === 'agenda') { await page.getByRole('combobox', {name: 'Profesional', exact: true}).selectOption('2'); await expect(page.getByRole('region', {name: 'Turnos del día'})).toContainText('Paciente de ejemplo'); }
      await page.waitForLoadState('networkidle');
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${name} ${size}`).toBe(true);
      await page.screenshot({path:`test-results/equipo/${name}-${size}.png`,fullPage:true});
    }
    await page.goto('/agenda');
    if (size === 'mobile') {
      await page.getByRole('button',{name:'☰ Menú'}).click();
      await expect(page.getByRole('button',{name:'☰ Menú'})).toHaveAttribute('aria-expanded', 'true');
      await page.screenshot({path:'test-results/equipo/menu-mobile.png',fullPage:true});
    }
    await page.getByRole('navigation',{name:'Navegación principal'}).getByRole('link',{name:'Mi cuenta'}).click();
    await page.getByRole('link',{name:'← Volver'}).click();
    await expect(page).toHaveURL(/\/agenda$/);
  }
  expect(errors).toEqual([]);
});
