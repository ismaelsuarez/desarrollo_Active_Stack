# Actores y Roles

## Actores del sistema

| Actor | Descripción | Cómo interactúa |
|-------|-------------|-----------------|
| Administrador/dueño | Responsable del consultorio. Configura agendas, profesionales, prestaciones y reglas, y mide las ausencias. | Aplicación web autenticada. Ve todas las agendas. Autoriza sobreturnos. |
| Recepción | Da, mueve, confirma y cancela turnos. Autoriza sobreturnos con aviso al profesional. Envía los mensajes de WhatsApp. | Aplicación web autenticada. Ve todas las agendas. Usa su propio WhatsApp para enviar mensajes preparados. |
| Profesional | Odontólogo con agenda propia y un box fijo. | Aplicación web autenticada. Ve solo su agenda y sus pacientes. Marca atendido o ausente en sus turnos. Recibe avisos de sobreturnos. |
| Paciente | Persona que reserva atención. Tiene cuenta propia (usuario y contraseña). | Enlace público de reserva: se registra, verifica su correo, ingresa y gestiona sus turnos. Rol `paciente` en los claims del JWT. |
| Administrativo | Facturación, cobro a obras sociales, documentación, contratos y liquidaciones. | En la v1 solo existen el rol y sus permisos reservados; no hay pantallas ni funciones propias. |
| Sistema (trabajos programados) | Barrido idempotente dentro de la API que emite solicitudes de confirmación, recordatorios y liberaciones automáticas. | Actor no humano. Sus acciones se registran en el historial del turno con `usuario_id` nulo. |
| Servidor SMTP | Servicio externo de envío de correo. | Recibe los mensajes que genera el barrido (y los correos de cuenta que envía la API). |
| WhatsApp de Recepción | Canal externo operado por una persona. | Recepción abre el enlace con el mensaje prellenado y lo envía. |

Nombres de rol en el código: `administrador`, `recepcion`, `profesional`, `paciente`, `administrativo`. Cada usuario tiene exactamente un rol (RN-08). La agenda de un profesional puede pertenecer a una cuenta de rol `administrador` cuando el administrador también atiende (DD-24).

## RBAC — Matriz de permisos

Convención de permisos:

- **C** crear, **R** leer, **U** modificar, **X** cancelar o liberar (cambio de estado).
- No existe borrado físico de turnos, pacientes ni usuarios: se desactivan o cambian de estado. Por eso no hay permiso D.
- Un asterisco (`*`) indica que el permiso del rol está **acotado por políticas de atributos** (ABAC). El rol habilita la acción; la política decide si aplica a ese recurso concreto. Ver [11_politicas_de_acceso_abac.md](11_politicas_de_acceso_abac.md).
- `Res.` significa permisos reservados: el rol existe, pero no tiene funciones en la v1.

| Recurso | Administrador | Recepción | Profesional | Paciente | Administrativo |
|---------|---------------|-----------|-------------|----------|----------------|
| Consultorio y parámetros (modo de liberación, horas) | R U | R | R | — | Res. |
| Usuarios del personal | C R U | — | R (propio) | — | Res. |
| Cuenta propia (cambiar contraseña, datos de acceso) | R U | R U | R U | R U | Res. |
| Profesionales y boxes | C R U | R | R (propio) | R (datos públicos) | Res. |
| Horario semanal | C R U | R | R* (propio) | — (se expone como disponibilidad) | Res. |
| Excepciones y bloqueos de agenda | C R U | R | R* (propio) | — (se expone como disponibilidad) | Res. |
| Catálogo de prestaciones | C R U | R | R | R (datos públicos) | Res. |
| Pacientes (ficha) | C R U | C R U | R* (solo de su agenda) | R U* (solo la propia) | Res. |
| Solicitudes de vinculación de cuenta (RN-62) | R U | R U | — | — | Res. |
| Vínculo cuenta-ficha: ver la cuenta vinculada, desvincular una cuenta y reactivar una ficha inactiva (RN-63) | R U | R U | — | — | Res. |
| Agenda (vista) | R (todas) | R (todas) | R* (solo la propia) | — | Res. |
| Turnos | C R U X* | C R U X* | R* (solo propios), U* (estado) | C R* U* X* (solo propios) | Res. |
| Autorización de sobreturno | C R | C R | R* (los que le afectan), U* (respuesta) | — | — |
| Historial del turno | R | R | R* (propios) | — | Res. |
| Notificaciones y mensajes de WhatsApp preparados | R U | R U | — | — | — |
| Indicador de ausentismo | R | — | — | — | Res. |

Notas:

- **Profesional** `U*` sobre turnos significa únicamente marcar `atendido` o `ausente` en turnos de su agenda (RN-38). No crea, mueve ni cancela turnos.
- **Paciente** `C` sobre turnos significa reservar para sí mismo. `U*` es reprogramar y `X*` cancelar, ambos sujetos a la ventana de 24 horas (RN-33).
- **Solicitudes de vinculación**: las crea el sistema al registrarse un paciente con un DNI que ya tiene ficha. `R` es ver la lista (con o sin el filtro de estado); `U` es resolverlas: vincular la cuenta con la ficha elegida o rechazar la solicitud, tras verificar la identidad, también para una solicitud ya rechazada (RN-49, RN-62). Cuando la solicitud está `vinculada`, la lista devuelve la ficha vinculada (identificador, nombre y apellido). Endpoints: `GET /solicitudes-vinculacion?estado=`, `POST /solicitudes-vinculacion/{id}/vincular` y `POST /solicitudes-vinculacion/{id}/rechazar`.
- **Vínculo cuenta-ficha** (RN-63): `R` es ver la cuenta vinculada a una ficha: el detalle de la ficha (`GET /pacientes/{id}`) devuelve a Recepción y Administrador el identificador, el nombre de usuario, el correo y si está verificado, o nada si la ficha no tiene cuenta; el Profesional y el Paciente no reciben datos de la cuenta y no se devuelve ningún otro dato (minimización, RN-58). `U` es desvincular la cuenta de una ficha, con un motivo obligatorio (la ficha conserva datos y turnos, la cuenta queda sin ficha y se revocan sus sesiones renovables), y reactivar una ficha inactiva, que la v1 solo puede tener por datos cargados o corregidos fuera de la aplicación (no hay una acción que desactive una ficha, SU-47). Endpoints: `POST /pacientes/{id}/desvincular` y `POST /pacientes/{id}/reactivar`. Acciones `paciente.desvincular` y `paciente.reactivar` en [11](11_politicas_de_acceso_abac.md).
- **Recepción** no administra horarios ni excepciones en la v1; ver pregunta abierta en [10](10_preguntas_abiertas.md).
- **Administrativo**: todas las celdas son reservadas. Cuando existan sus funciones se completará la matriz.

## Rutas públicas

Accesibles sin autenticación. Todas son de lectura, o bien parte del ciclo de alta, ingreso y recuperación de cuenta. En estas rutas no hay sesión y el cliente nunca envía el `consultorio_id`. El criterio es el tipo de flujo y no el prefijo de la ruta: una ruta que recibe un token de un solo uso enviado por correo, o un token de renovación (`POST /auth/verificar-email`, `POST /auth/restablecer-password`, `POST /turnos/confirmar-por-enlace`, `POST /auth/refresh`), toma el consultorio de la fila a la que apunta el token; las demás rutas sin token (`POST /auth/login`, `POST /auth/registro`, `POST /auth/reenviar-verificacion`, `POST /auth/recuperar-password` y las lecturas públicas `/publico/*`) toman el único consultorio activo de la v1 desde la configuración del servidor, con una sola dependencia (RN-59, DD-16).

### API (prefijo `/api/v1`)

| Ruta | Propósito |
|------|-----------|
| `GET /health` | Verificación de estado del servicio |
| `GET /publico/consultorio` | Nombre, teléfono y datos de contacto del consultorio (el teléfono se muestra cuando el paciente ya no puede autogestionar, RN-33) |
| `GET /publico/aviso-privacidad` | Texto y versión vigentes del aviso de privacidad, con el nombre, el domicilio y el contacto del consultorio; el registro exige aceptar esa versión (RN-65) |
| `GET /publico/prestaciones` | Prestaciones activas con su duración |
| `GET /publico/profesionales` | Profesionales activos (nombre y apellido) |
| `GET /publico/disponibilidad` | Horarios libres por profesional y prestación (sin datos de otros pacientes) |
| `POST /auth/registro` | Alta de cuenta de paciente (RN-01) |
| `POST /auth/verificar-email` | Verificación del correo con token (RN-02, RN-03) |
| `POST /auth/reenviar-verificacion` | Reenvío del correo de verificación |
| `POST /auth/login` | Ingreso (RN-09 limita los intentos) |
| `POST /auth/refresh` | Renovación del token de acceso |
| `POST /auth/recuperar-password` | Solicitud de recuperación (respuesta uniforme, RN-05) |
| `POST /auth/restablecer-password` | Cambio de contraseña con token |
| `POST /turnos/confirmar-por-enlace` | Confirmación con token de un solo uso recibido por correo (**Suposición** SU-12 en [09](09_decisiones_y_supuestos.md)) |

### Frontend

| Ruta | Propósito |
|------|-----------|
| `/reservar` | Enlace público de reserva: servicios, profesionales y disponibilidad. Reservar exige cuenta verificada. |
| `/registro` | Registro de paciente |
| `/verificar-email` | Destino del enlace de verificación |
| `/login` | Ingreso |
| `/recuperar` y `/restablecer` | Recuperación de contraseña |
| `/confirmar` | Destino del enlace de confirmación del correo (SU-12) |

El resto de las rutas del frontend requiere sesión y se resuelve según el rol. La documentación interactiva de la API (`/docs`) se publica en desarrollo y se restringe en producción (**Suposición** SU-06).

## Rutas privadas por rol (resumen)

| Rol | Pantallas principales |
|-----|-----------------------|
| Paciente | Mis turnos, reservar, reprogramar, cancelar, mi cuenta |
| Profesional | Agenda del día propia, detalle del turno, responder aviso de sobreturno |
| Recepción | Agenda de todos los profesionales, alta y movimiento de turnos, sin confirmar, sobreturnos, notificaciones y WhatsApp, pacientes, solicitudes de vinculación de cuenta y vínculo cuenta-ficha (desvincular, reactivar) |
| Administrador | Todo lo de Recepción más profesionales, horarios, bloqueos, prestaciones, usuarios, parámetros del consultorio e indicador de ausentismo |
| Administrativo | Sin pantallas en la v1 |
