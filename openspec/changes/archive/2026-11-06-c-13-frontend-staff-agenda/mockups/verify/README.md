# Verificación visual manual pendiente

No se pudo iniciar Playwright: busca Chrome en una ruta inexistente. No se generaron capturas ni se inspeccionaron visualmente las pantallas implementadas; tampoco se revisaron consola, red o teclado en navegador. El mockup aprobado es `../index.html`, sistema de diseño revisión 2.

Con el backend y frontend locales en funcionamiento y datos de prueba, abrir la aplicación e iniciar sesión con los roles indicados. Comparar cada caso con el mockup en ventana de 390×844 y de 1440×900, incluidos foco visible, orden de tabulación, etiquetas, mensajes, consola y solicitudes fallidas.

| Vista o estado | Rol | Revisar |
| --- | --- | --- |
| Agenda diaria, selección, carga, vacío y error | Recepción, Administrador | `#agenda`: profesional, fecha, hora del consultorio, estados y sobreturno. |
| Agenda propia y sin agenda | Profesional | `#profesional`: solo su agenda y sin controles para crear turno. |
| Detalle y acciones por estado | Recepción y Profesional | `#detalle`, `#profesional-turno`: acceso a ficha, botones permitidos y actualización. |
| Alta de turno y ficha | Recepción | `#nuevo`, `#ficha-nueva`: búsqueda, creación separada, resultado parcial, validación y envío incierto. |
| Conflicto y movimiento | Recepción | `#conflicto`, `#mover`: datos conservados, opciones orientativas y hora manual. |
| Autorización, aviso y respuesta | Recepción, Profesional, Administrador con agenda | `#autorizar`, `#sobreturno`, `#responder`: motivo, autorización, aviso y rechazo sin cancelación. |
| Pacientes, ficha, historial y edición | Recepción y Profesional | `#pacientes`, `#ficha`, `#ficha-profesional`: paginación, privacidad de cuenta y permisos. |
| Desvinculación y reactivación | Recepción | `#desvincular`, `#reactivar`: motivo, conflicto y recarga. |
| Solicitudes | Recepción | `#solicitudes`, `#resolver`: estados, selección de ficha, correo sin verificar, conflicto y actualización. |

Registrar para cada diferencia: prioridad, pantalla, viewport, comportamiento esperado, observado y pasos para reproducir. No marcar coincidencia hasta completar la revisión.
