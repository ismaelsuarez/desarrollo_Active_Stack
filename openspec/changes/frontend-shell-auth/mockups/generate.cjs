const fs = require('fs');
const dir = __dirname;
const field = (label, placeholder = '', type = 'text') => `<div class="field"><label>${label}</label><input type="${type}" placeholder="${placeholder}"></div>`;
const button = (text, extra = '') => `<span class="button ${extra}">${text}</span>`;
const card = (title, body, extra = '') => `<section class="card ${extra}"><h2>${title}</h2>${body}</section>`;
const msg = (text, type = '') => `<div class="message ${type}">${text}</div>`;
const action = (...items) => `<div class="actions">${items.join('')}</div>`;
const shell = (role, intro, menu) => `<section class="card"><div class="role">${role}</div><div class="shell"><aside class="side"><span class="active">Inicio</span><span>Mi cuenta</span><span>Cerrar sesión</span></aside><div class="content"><h3>Hola, ${role.toLowerCase()}</h3><p>${intro}</p><p class="hint">${menu}</p></div></div></section>`;
const pages = [
  ['acceso','Ingreso y recuperación','Acceso simple y mensajes que no revelan si existe una cuenta.', [
    card('Ingresar', '<p>Usá los datos de tu cuenta para continuar.</p>' + field('Usuario o correo','Tu usuario o correo') + field('Contraseña','Tu contraseña','password') + '<a href="#">Olvidé mi contraseña</a>' + action(button('Ingresar')) + '<hr class="divider"><p>¿Todavía no tenés cuenta? <a href="#">Crear cuenta</a></p>'),
    card('Cuando algo requiere atención', msg('<strong>No pudimos ingresar.</strong><br>Revisá tus datos e intentá nuevamente.','error') + msg('<strong>Verificá tu correo para ingresar.</strong><br>Podés solicitar otro enlace.','warning') + action(button('Reenviar enlace','secondary')) + msg('<strong>El servicio está demorando.</strong><br>Estamos intentando nuevamente.','warning')),
    card('Recuperar contraseña', '<p>Ingresá tu correo para solicitar un enlace.</p>' + field('Correo electrónico','nombre@ejemplo.com','email') + action(button('Enviar enlace'),button('Volver','secondary')) + msg('Si los datos corresponden a una cuenta, recibirás un correo con los próximos pasos.','success')),
    card('Reenviar verificación', '<p>Ingresá tu correo y solicitá un nuevo enlace de verificación.</p>' + field('Correo electrónico','nombre@ejemplo.com','email') + action(button('Solicitar enlace')) + msg('Si corresponde, recibirás un correo con los próximos pasos.','success'))
  ]],
  ['registro','Crear una cuenta','Registro de paciente y aceptación explícita del aviso vigente.', [
    card('Tus datos','<p>Completá tus datos para crear tu cuenta.</p><div class="form-grid">' + field('Nombre','Nombre') + field('Apellido','Apellido') + field('DNI','DNI') + field('Teléfono','Teléfono') + field('Correo electrónico','nombre@ejemplo.com','email') + field('Obra social (opcional)','Obra social') + field('Nombre de usuario','Elegí un usuario') + field('Contraseña','Elegí una contraseña','password') + '</div><hr class="divider"><h3>Aviso de privacidad</h3><p class="hint">Texto y versión obtenidos desde el servicio. El aviso completo se mostrará aquí.</p><div class="message">Aviso de privacidad · versión vigente<br><span class="hint">Contenido ilustrativo sujeto a la respuesta de la API.</span></div><label class="check"><input type="checkbox"> <span>Leí y acepto el aviso de privacidad.</span></label>' + action(button('Crear cuenta','disabled'),button('Volver a ingresar','secondary')),'wide'),
    card('Si el aviso no está disponible',msg('No pudimos cargar el aviso de privacidad. Intentá nuevamente antes de crear tu cuenta.','warning') + action(button('Volver a cargar','secondary'))),
    card('Si el aviso cambió',msg('El aviso de privacidad se actualizó. Revisá la nueva versión y aceptala para continuar.','warning') + '<label class="check"><input type="checkbox"> <span>Leí y acepto el aviso actualizado.</span></label>')
  ]],
  ['enlaces','Enlaces y confirmaciones','Resultados claros para los enlaces recibidos por correo.', [
    card('Verificación de correo',msg('<strong>Tu correo fue verificado.</strong><br>Ya podés ingresar a tu cuenta.','success') + action(button('Ir a ingresar'))),
    card('Enlace no disponible',msg('<strong>No pudimos usar este enlace.</strong><br>Puede estar vencido o ya haber sido utilizado.','error') + action(button('Solicitar otro enlace','secondary'))),
    card('Restablecer contraseña','<p>Elegí una nueva contraseña para tu cuenta.</p>' + field('Nueva contraseña','Nueva contraseña','password') + field('Confirmar contraseña','Repetí la contraseña','password') + action(button('Guardar contraseña')) + msg('Tu contraseña fue actualizada. Ya podés ingresar.','success')),
    card('Confirmación de turno',msg('<strong>Tu turno fue confirmado.</strong><br>Gracias por confirmar tu asistencia.','success') + msg('<strong>No pudimos confirmar el turno.</strong><br>El enlace puede haber vencido. Contactá al consultorio.','error')),
    card('Mientras verificamos','<p>Estamos procesando tu enlace. Por favor, esperá un momento.</p>' + msg('Si el servicio demora, te avisaremos cómo continuar.','warning'))
  ]],
  ['cuenta','Mi cuenta','Opciones personales según los permisos de cada rol.', [
    card('Datos de contacto','<p>Disponible para pacientes.</p>' + field('Correo electrónico','nombre@ejemplo.com','email') + field('Teléfono','Teléfono') + '<p class="hint">Si cambiás el correo, tendrás que verificarlo nuevamente.</p>' + action(button('Guardar cambios')) + msg('Tus datos se actualizaron. Revisá tu correo para verificarlo.','success')),
    card('Cambiar contraseña',field('Contraseña actual','Tu contraseña actual','password') + field('Nueva contraseña','Nueva contraseña','password') + field('Confirmar nueva contraseña','Repetí la contraseña','password') + action(button('Actualizar contraseña')) + msg('La contraseña actual no coincide. Revisala e intentá nuevamente.','error')),
    card('Sesión cerrada','<p>Tu sesión se cerró en este dispositivo.</p>' + msg('No pudimos confirmar el cierre en el servidor. Si es necesario, volvé a intentarlo.','warning') + action(button('Ir a ingresar','secondary')))
  ]],
  ['roles','Navegación según tu rol','La estructura inicial presenta solo las opciones disponibles para cada persona. Las funciones de agenda se agregan en cambios posteriores.', [
    shell('Paciente','Desde acá podrás gestionar tu cuenta.','Las opciones de turnos se incorporarán más adelante.'),
    shell('Recepción','Este es tu espacio de trabajo.','Las funciones de recepción se incorporarán más adelante.'),
    shell('Profesional','Este es tu espacio de trabajo.','La agenda profesional se incorporará más adelante.'),
    shell('Administrador','Este es tu espacio de administración.','Las funciones de administración se incorporarán más adelante.'),
    card('Administrativo','<p>Tu cuenta está activa. Las funciones para este rol todavía no están disponibles.</p>' + action(button('Mi cuenta','secondary'))),
    card('Acceso restringido',msg('No tenés permiso para ver esta sección.','error') + action(button('Volver a mi inicio','secondary'))),
    card('Cargando sesión','<p>Estamos verificando tu sesión. Esperá un momento.</p>' + msg('El servicio está tardando más de lo habitual.','warning')),
    card('Página no encontrada','<p>No encontramos la página que buscabas.</p>' + action(button('Ir al inicio','secondary')))
  ]]
];
for (const [name,title,intro,cards] of pages) {
 const html = `<!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${title} · Mockup C-11</title><link rel="stylesheet" href="mockups.css"><script src="../../../../design-system/brand.js" defer></script></head><body><header><div class="brand"><img src="../../../../design-system/assets/logo.svg" alt="Logo provisional"><span data-brand-name>Sistema de Turnos y Agenda Odontológica</span></div><div class="tag">MOCKUP C-11<br>Revisión pendiente</div></header><main><div class="eyebrow">Propuesta · C-11</div><h1>${title}</h1><p class="intro">${intro}</p><nav aria-label="Vistas del mockup"><a href="acceso.html">Acceso</a><a href="registro.html">Registro</a><a href="enlaces.html">Enlaces</a><a href="cuenta.html">Cuenta</a><a href="roles.html">Roles</a></nav><div class="grid">${cards.join('')}</div><p class="footer">Referencia estática para revisión visual. Los campos y botones son ilustrativos y no envían datos. Nombre y logo provisionales.</p></main></body></html>`;
 fs.writeFileSync(dir + '/' + name + '.html', html);
}
