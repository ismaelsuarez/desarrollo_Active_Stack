# Funcionalidades

Organizadas por **épica** y luego por **historia de usuario** (formato US-NNN). Cada historia indica su versión: **v1** (entra en el MVP del 2026-10-19) o **backlog** (diferida). Los criterios de aceptación son verificables y alimentan las especificaciones de los changes.

## Trazabilidad con los casos de uso confirmados

| Caso de uso | Historias que lo cubren |
|-------------|-------------------------|
| CU-1 Paciente reserva, confirma, cancela o reprograma | US-001 a US-004, US-013 a US-018 |
| CU-2 Recepción: confirmación automática (correo automático, WhatsApp con un clic) | US-022, US-025, US-030 a US-035 |
| CU-3 Sin solapamientos; sobreturnos solo con autorización | US-023, US-024, US-029 |
| CU-4 Profesional ve su agenda con el estado de cada turno | US-026 a US-028 |
| CU-5 Administrador ve las ausencias | US-040 |

## Épica 1: Cuenta del paciente

### US-001 — Registrarse desde el enlace público (v1)
**Como** paciente
**Quiero** crear mi cuenta con usuario y contraseña desde el enlace de reserva
**Para** poder reservar y gestionar mis turnos sin llamar

**Criterios de aceptación**:
- [ ] El formulario pide nombre y apellido, teléfono, correo, DNI, obra social (opcional), usuario y contraseña.
- [ ] La contraseña se almacena solo como hash y no se muestra ni se registra.
- [ ] Se crea la cuenta con rol `paciente` y la ficha de paciente asociada.
- [ ] Si el DNI ya tiene una ficha, no se crea una segunda ni se vincula en forma automática: se guarda una solicitud de vinculación con el DNI declarado (RN-49, RN-62).
- [ ] La respuesta y el correo de verificación son idénticos exista o no el DNI. Esto no impide deducir, desde el rechazo de la reserva de una cuenta con el correo verificado, que un DNI ya figuraba en el consultorio: riesgo residual aceptado y acotado (RN-62, DD-19).
- [ ] El registro tiene un límite de solicitudes por origen (la dirección del cliente tomada del encabezado de reenvío con la cantidad de saltos de proxy de la configuración; sin origen, rige un límite global; se guarda solo su hash con clave y se purga a las 24 horas) y responde 429 al superarlo; el intento cuenta aunque después falle la validación o el registro (RN-62, DD-21).
- [ ] Un paciente con un DNI nuevo reserva por su cuenta, sin pasar por Recepción.
- [ ] Dos registros simultáneos con el mismo DNI nuevo dejan una sola ficha y una solicitud, con la misma respuesta para ambos.
- [ ] El formulario no envía el consultorio: lo resuelve el servidor (RN-59).
- [ ] Se envía el correo de verificación.

**Reglas relacionadas**: RN-01, RN-04, RN-47, RN-48, RN-49, RN-58, RN-59, RN-62

### US-002 — Verificar el correo (v1)
**Como** paciente
**Quiero** confirmar mi correo con un enlace
**Para** activar mi cuenta

**Criterios de aceptación**:
- [ ] El enlace es de un solo uso y vence; un enlace usado o vencido muestra un error claro.
- [ ] Hasta verificar, el ingreso y la reserva están bloqueados y se ofrece reenviar el correo.
- [ ] Verificar el correo marca `email_verificado` y permite ingresar.

**Reglas relacionadas**: RN-02, RN-03

### US-003 — Ingresar al sistema (v1)
**Como** usuario (cualquier rol)
**Quiero** ingresar con mi usuario y contraseña
**Para** acceder a las funciones que mi rol permite

**Criterios de aceptación**:
- [ ] El ingreso devuelve un JWT con usuario, `consultorio_id` y rol, y una sesión renovable.
- [ ] Tras varios intentos fallidos la cuenta se bloquea de forma temporal.
- [ ] El mensaje de error no distingue entre usuario inexistente y contraseña incorrecta.
- [ ] Un paciente con correo sin verificar no ingresa.

**Reglas relacionadas**: RN-02, RN-06, RN-09

### US-004 — Recuperar la contraseña (v1)
**Como** usuario
**Quiero** restablecer mi contraseña desde un enlace enviado a mi correo
**Para** recuperar el acceso si la olvido

**Criterios de aceptación**:
- [ ] La solicitud responde igual exista o no el correo.
- [ ] El enlace es de un solo uso y vence.
- [ ] Al restablecer, se revocan las sesiones activas.

**Reglas relacionadas**: RN-03, RN-04, RN-05

### US-005 — Gestionar mi cuenta (v1)
**Como** usuario
**Quiero** cambiar mi contraseña y ver mis datos de acceso
**Para** mantener segura mi cuenta

**Criterios de aceptación**:
- [ ] Cambiar la contraseña exige la contraseña actual.
- [ ] Un paciente puede actualizar su teléfono y correo; cambiar el correo exige verificarlo de nuevo.

**Reglas relacionadas**: RN-02, RN-04

## Épica 2: Usuarios, roles y control de acceso

### US-006 — Gestionar usuarios del personal (v1)
**Como** Administrador
**Quiero** crear y desactivar cuentas de personal con su rol
**Para** que cada persona acceda solo a lo que le corresponde

**Criterios de aceptación**:
- [ ] Se pueden crear usuarios con los roles `administrador`, `recepcion`, `profesional` y `administrativo`.
- [ ] Un usuario `profesional` se asocia a un profesional de la agenda.
- [ ] Desactivar un usuario impide su ingreso y conserva su historial.
- [ ] Cada usuario tiene un único rol.

**Reglas relacionadas**: RN-07, RN-08

### US-007 — Control de acceso por rol y por atributos (v1)
**Como** Administrador
**Quiero** que el sistema aplique permisos por rol y políticas por atributos
**Para** que cada usuario vea y modifique solo lo que corresponde

**Criterios de aceptación**:
- [ ] Un profesional solo ve su propia agenda y sus propios pacientes.
- [ ] Ningún usuario accede a datos de otro consultorio.
- [ ] Un turno `atendido` no se edita ni se cancela.
- [ ] El paciente solo cancela o reprograma hasta 24 horas antes y solo sus turnos.
- [ ] El rol Administrativo existe con permisos reservados y sin acceso funcional.

**Reglas relacionadas**: RN-19, RN-33, RN-35, RN-38, RN-50, RN-56 (ver [11](11_politicas_de_acceso_abac.md))

## Épica 3: Configuración de la agenda

### US-008 — Gestionar profesionales y boxes (v1)
**Como** Administrador
**Quiero** dar de alta profesionales, cada uno con su box fijo
**Para** que la agenda refleje la estructura real del consultorio

**Criterios de aceptación**:
- [ ] Cada profesional tiene exactamente un box y un box no se comparte.
- [ ] Se pueden desactivar profesionales sin perder sus turnos históricos.

**Reglas relacionadas**: RN-10

### US-009 — Definir el horario semanal (v1)
**Como** Administrador
**Quiero** cargar el horario semanal de cada profesional, con uno o más bloques por día
**Para** que solo se ofrezcan turnos en horarios de atención

**Criterios de aceptación**:
- [ ] Cada profesional tiene su horario propio.
- [ ] No se aceptan bloques superpuestos del mismo día.
- [ ] La disponibilidad pública respeta el horario cargado.

**Reglas relacionadas**: RN-11, RN-14

### US-010 — Registrar excepciones y bloqueos de agenda (v1)
**Como** Administrador
**Quiero** cargar feriados, vacaciones, ausencias y bloqueos puntuales
**Para** que esos días y horarios no admitan turnos

**Criterios de aceptación**:
- [ ] Una excepción sin profesional aplica a todos (por ejemplo un feriado).
- [ ] Las excepciones bloquean la disponibilidad pública y el alta de turnos.
- [ ] Si hay turnos en el período, el sistema los lista y exige resolverlos de forma explícita.

**Reglas relacionadas**: RN-12, RN-14, RN-16

### US-011 — Gestionar el catálogo de prestaciones (v1)
**Como** Administrador
**Quiero** editar el catálogo inicial de prestaciones y sus duraciones
**Para** que cada turno ocupe el tiempo real de la prestación

**Criterios de aceptación**:
- [ ] Se parte de un catálogo inicial editable con duraciones sugeridas (a confirmar por el consultorio).
- [ ] Se pueden crear, editar y desactivar prestaciones.
- [ ] Cambiar una duración no altera turnos ya creados.

**Reglas relacionadas**: RN-13, RN-15

### US-012 — Configurar los parámetros del consultorio (v1)
**Como** Administrador
**Quiero** elegir el modo de liberación (automático o manual) y ver los plazos vigentes
**Para** adaptar el comportamiento a la forma de trabajo del consultorio

**Criterios de aceptación**:
- [ ] El modo de liberación se puede cambiar entre `automatico` y `manual`.
- [ ] Los plazos iniciales son 48 h (confirmación), 24 h (recordatorio), 12 h (liberación) y 24 h (límite del paciente).
- [ ] El teléfono del consultorio se carga y se muestra al paciente cuando ya no puede autogestionar.

**Reglas relacionadas**: RN-27, RN-28, RN-33

## Épica 4: Reserva online del paciente

### US-013 — Ver la disponibilidad desde el enlace público (v1)
**Como** paciente
**Quiero** ver prestaciones, profesionales y horarios libres
**Para** elegir cuándo reservar

**Criterios de aceptación**:
- [ ] La disponibilidad se calcula con el horario semanal, las excepciones, la duración de la prestación y los turnos existentes.
- [ ] Se puede consultar sin ingresar, pero reservar exige cuenta verificada.
- [ ] No se expone información de otros pacientes.

**Reglas relacionadas**: RN-11, RN-12, RN-13, RN-14, RN-17

### US-014 — Reservar un turno (v1)
**Como** paciente
**Quiero** reservar un turno con un profesional y una prestación
**Para** no depender de que me atiendan el teléfono

**Criterios de aceptación**:
- [ ] El turno se crea `pendiente` con la duración de la prestación.
- [ ] Si otro paciente toma el mismo horario antes, se muestra un aviso y alternativas.
- [ ] Se programan los hitos de confirmación, recordatorio y liberación.
- [ ] El paciente recibe un correo con el resumen del turno.
- [ ] Una cuenta sin ficha (solicitud de vinculación `pendiente` o `rechazada`) no puede reservar y recibe un mensaje de que debe comunicarse con el consultorio para verificar su cuenta, sin mención del DNI (RN-62).

**Reglas relacionadas**: RN-13, RN-17, RN-23, RN-24, RN-29, RN-62

### US-015 — Ver mis turnos (v1)
**Como** paciente
**Quiero** ver mis turnos futuros y pasados con su estado
**Para** saber qué tengo agendado

**Criterios de aceptación**:
- [ ] Solo se listan los turnos del paciente autenticado.
- [ ] Cada turno muestra estado, fecha, hora, profesional y prestación.
- [ ] Las acciones disponibles dependen del estado y del plazo de 24 horas.

**Reglas relacionadas**: RN-35, RN-33

### US-016 — Confirmar mi turno (v1)
**Como** paciente
**Quiero** confirmar mi turno desde la cuenta o desde el enlace del correo
**Para** evitar que se libere

**Criterios de aceptación**:
- [ ] El turno `pendiente` pasa a `confirmado`.
- [ ] Un turno ya `liberado` no se puede confirmar y se ofrece reservar de nuevo.
- [ ] El enlace del correo es de un solo uso y solo permite confirmar (no cancelar).

**Reglas relacionadas**: RN-30, RN-27

### US-017 — Cancelar mi turno (v1)
**Como** paciente
**Quiero** cancelar mi turno hasta 24 horas antes
**Para** liberar el horario sin llamar

**Criterios de aceptación**:
- [ ] La acción está disponible solo hasta 24 horas antes del inicio.
- [ ] Pasado el plazo se muestra el teléfono del consultorio.
- [ ] El hueco queda libre de inmediato y el turno queda `cancelado` con registro de quién y cuándo.
- [ ] El paciente recibe un correo que confirma la cancelación, que comunica algo ya ocurrido y no se omite porque el turno ya esté `cancelado`.

**Reglas relacionadas**: RN-22, RN-33, RN-35, RN-36

### US-018 — Reprogramar mi turno (v1)
**Como** paciente
**Quiero** mover mi turno a otro horario hasta 24 horas antes
**Para** adaptarlo a mi disponibilidad

**Criterios de aceptación**:
- [ ] Solo se ofrecen horarios válidos.
- [ ] Si el nuevo horario no está disponible, el turno original se mantiene.
- [ ] El turno vuelve a `pendiente`, se reinician los hitos (las notificaciones `programada` o `preparada` de solicitud de confirmación y de recordatorio del ciclo anterior pasan a `omitida`, en todos los canales) y se limpia la marca "sin confirmar" (RN-32).
- [ ] El cambio queda en el historial.

**Reglas relacionadas**: RN-32, RN-33, RN-37

## Épica 5: Gestión de turnos por Recepción

### US-019 — Dar un turno (v1)
**Como** Recepción
**Quiero** crear un turno a nombre de un paciente (por ejemplo, por teléfono)
**Para** atender a quien no usa el enlace público

**Criterios de aceptación**:
- [ ] Se busca al paciente o se crea su ficha mínima en el momento.
- [ ] Se valida horario, excepciones y solapamiento.
- [ ] Se puede marcar `confirmado` si el paciente lo confirma en el acto.

**Reglas relacionadas**: RN-14, RN-17, RN-23, RN-47

### US-020 — Mover un turno (v1)
**Como** Recepción
**Quiero** reprogramar un turno en cualquier momento antes de que sea atendido
**Para** resolver cambios del paciente o del consultorio

**Criterios de aceptación**:
- [ ] No hay límite de anticipación para el personal.
- [ ] Un turno `atendido` no se puede mover.
- [ ] Se notifica al paciente del cambio (US-034).

**Reglas relacionadas**: RN-19, RN-34, RN-37

### US-021 — Cancelar un turno (v1)
**Como** Recepción
**Quiero** cancelar un turno con motivo
**Para** liberar el horario cuando el paciente o el consultorio no pueden asistir

**Criterios de aceptación**:
- [ ] Queda `cancelado` con quién, cuándo y motivo.
- [ ] Un turno `atendido` no se puede cancelar.

**Reglas relacionadas**: RN-19, RN-34, RN-36

### US-022 — Confirmar un turno por el paciente (v1)
**Como** Recepción
**Quiero** marcar un turno como confirmado cuando el paciente me confirma por teléfono o WhatsApp
**Para** reflejar la confirmación sin esperar el correo

**Criterios de aceptación**:
- [ ] El turno `pendiente` pasa a `confirmado` y queda registrado quién lo confirmó.
- [ ] No se puede confirmar un turno `liberado`.

**Reglas relacionadas**: RN-23, RN-30

### US-023 — Prevención de solapamientos (v1)
**Como** Recepción
**Quiero** que el sistema impida superponer turnos de un profesional
**Para** evitar el desorden en la atención

**Criterios de aceptación**:
- [ ] Un turno que se superpone a otro activo del mismo profesional es rechazado.
- [ ] La verificación se hace en la base de datos y soporta reservas concurrentes.
- [ ] `cancelado` y `liberado` no bloquean el horario.

**Reglas relacionadas**: RN-10, RN-17, RN-22, RN-24

### US-024 — Autorizar un sobreturno (v1)
**Como** Recepción
**Quiero** otorgar un sobreturno con aviso al profesional afectado
**Para** atender un caso excepcional de forma ordenada

**Criterios de aceptación**:
- [ ] El sobreturno exige una autorización explícita y un motivo.
- [ ] Se registra al autorizante, la fecha y el aviso al profesional.
- [ ] El sobreturno aparece marcado en la agenda.
- [ ] No se otorga fuera del horario del profesional ni sobre un bloqueo.

**Reglas relacionadas**: RN-39, RN-40, RN-41, RN-42, RN-43

### US-025 — Resolver turnos sin confirmar (v1)
**Como** Recepción
**Quiero** ver la lista de turnos "sin confirmar" cuando el consultorio está en modo manual, o cuando un turno no cumplió las condiciones de la liberación automática
**Para** decidir si llamo al paciente o libero el turno

**Criterios de aceptación**:
- [ ] A las 12 horas, un turno `pendiente` en modo manual queda marcado "sin confirmar" y no se libera.
- [ ] En modo automático, un turno cuya solicitud de confirmación no fue enviada queda marcado "sin confirmar" y no se libera (RN-60). Dentro del mismo ciclo no se vuelve a evaluar para la liberación automática aunque esa solicitud se envíe después: decide Recepción.
- [ ] El barrido no selecciona ni marca un turno `pendiente` cuyo inicio ya pasó, y no lo reevalúa en cada barrido; ese turno se marca `atendido` o `ausente` (RN-44).
- [ ] Al reprogramar un turno marcado, la marca se limpia y sale de la lista (RN-32).
- [ ] Recepción puede confirmar, cancelar o liberar el turno desde la lista.
- [ ] Liberar deja el turno en `liberado` y el hueco disponible.

**Reglas relacionadas**: RN-28, RN-22, RN-29, RN-32, RN-44, RN-60

## Épica 6: Agenda del profesional

### US-026 — Ver mi agenda del día (v1)
**Como** Profesional
**Quiero** ver mi agenda del día con el estado de cada turno
**Para** saber a quién esperar

**Criterios de aceptación**:
- [ ] Solo se muestra la agenda propia.
- [ ] Cada turno muestra paciente, prestación, hora y estado (pendiente, confirmado, ausente, atendido).
- [ ] Los sobreturnos aparecen marcados.

**Reglas relacionadas**: RN-18, RN-42, RN-50

### US-027 — Marcar un turno como atendido (v1)
**Como** Profesional
**Quiero** marcar un turno como atendido
**Para** registrar que el paciente fue atendido

**Criterios de aceptación**:
- [ ] Solo en turnos propios y a partir de la hora de inicio.
- [ ] Un turno `atendido` ya no se puede editar ni cancelar.

**Reglas relacionadas**: RN-18, RN-19, RN-38

### US-028 — Marcar un turno como ausente (v1)
**Como** Profesional
**Quiero** marcar que el paciente no se presentó
**Para** que el consultorio mida las ausencias

**Criterios de aceptación**:
- [ ] Solo en turnos propios y una vez pasada la hora de inicio.
- [ ] Recepción y Administrador pueden hacerlo en cualquier agenda.
- [ ] El cambio queda en el historial.

**Reglas relacionadas**: RN-21, RN-38, RN-44

### US-029 — Recibir y responder el aviso de sobreturno (v1)
**Como** Profesional
**Quiero** enterarme de un sobreturno que afecta mi agenda y poder responder
**Para** que mi agenda no cambie sin mi conocimiento

**Criterios de aceptación**:
- [ ] El aviso se genera al otorgarse el sobreturno y queda registrado.
- [ ] El profesional puede aprobar o rechazar y la respuesta queda registrada.
- [ ] Solo ve los sobreturnos de su propia agenda.

**Reglas relacionadas**: RN-40, RN-41

## Épica 7: Notificaciones

### US-030 — Solicitud de confirmación por correo (v1)
**Como** Recepción
**Quiero** que el sistema pida confirmación 48 horas antes por correo
**Para** no confirmar a mano

**Criterios de aceptación**:
- [ ] El correo se envía automáticamente a los turnos `pendiente` 48 horas antes.
- [ ] Incluye el enlace para confirmar y el plazo de liberación.
- [ ] El envío queda registrado; dos barridos simultáneos nunca envían la misma notificación y, ante una caída entre el envío y su registro, el correo puede repetirse (entrega al menos una vez, RN-61).

**Reglas relacionadas**: RN-25, RN-29, RN-30, RN-54, RN-61

### US-031 — Recordatorio 24 horas antes (v1)
**Como** paciente
**Quiero** recibir un recordatorio
**Para** acordarme del turno

**Criterios de aceptación**:
- [ ] El recordatorio se envía 24 horas antes a los turnos `pendiente` y `confirmado`.
- [ ] Para los `pendiente`, el texto advierte la liberación solo si ese turno puede liberarse de forma automática (RN-60); en otro caso solo le pide que confirme.

**Reglas relacionadas**: RN-26, RN-54, RN-60

### US-032 — Liberación automática de turnos sin confirmar (v1)
**Como** Recepción
**Quiero** que un turno sin confirmar se libere solo 12 horas antes
**Para** reutilizar el hueco

**Criterios de aceptación**:
- [ ] En modo automático el turno `pendiente` pasa a `liberado` 12 horas antes, solo si la solicitud de confirmación de su ciclo actual está `enviada` y el turno todavía no comenzó (RN-60).
- [ ] Si la solicitud falló, fue omitida o sigue `programada` o `enviando`, el turno queda `pendiente` con la marca "sin confirmar" para que decida Recepción.
- [ ] Un turno cuyo inicio ya pasó queda fuera de la selección del barrido y nunca se libera de forma automática (la actualización condicional también exige que no haya comenzado).
- [ ] El hueco queda disponible y el paciente recibe un aviso, que no se omite por estar el turno `liberado` (comunica ese hecho).
- [ ] En modo manual no se libera (ver US-025).

**Reglas relacionadas**: RN-20, RN-22, RN-27, RN-28, RN-60

### US-033 — Mensaje de WhatsApp con un clic (v1)
**Como** Recepción
**Quiero** que el sistema prepare el mensaje de WhatsApp y lo envíe con un clic
**Para** confirmar por WhatsApp sin redactar cada mensaje

**Criterios de aceptación**:
- [ ] Una lista muestra las notificaciones de WhatsApp pendientes de enviar.
- [ ] El clic abre WhatsApp con el teléfono y el texto prellenados.
- [ ] Recepción marca la notificación como enviada y queda registrado quién.
- [ ] El mensaje no incluye datos de salud.

**Reglas relacionadas**: RN-52, RN-53, RN-54

### US-034 — Avisar al paciente de cambios hechos por el personal (v1)
**Como** paciente
**Quiero** recibir un aviso si el consultorio cancela o mueve mi turno
**Para** enterarme sin tener que consultarlo

**Criterios de aceptación**:
- [ ] Una cancelación o reprogramación hecha por el personal genera un correo al paciente.
- [ ] Se prepara también el mensaje de WhatsApp para Recepción.
- [ ] La resolución de turnos afectados por una excepción (RN-16) usa el mismo aviso.
- [ ] El aviso comunica algo que ya ocurrió, así que no se omite porque el turno ya esté cancelado o reprogramado; solo la solicitud de confirmación y el recordatorio dependen del estado y el ciclo del turno ("Vigencia por tipo" en [04](04_modelo_de_datos.md)).

**Reglas relacionadas**: RN-16, RN-34, RN-54

### US-035 — Gestionar envíos fallidos (v1)
**Como** Recepción
**Quiero** ver las notificaciones de correo que fallaron
**Para** avisar al paciente por otro medio

**Criterios de aceptación**:
- [ ] Los fallos se reintentan de forma acotada y luego quedan `fallida`.
- [ ] La lista de fallidas es visible para Recepción y Administrador.
- [ ] Un fallo no cambia el estado del turno.

**Reglas relacionadas**: RN-31

## Épica 8: Pacientes

### US-036 — Ficha mínima de paciente (v1)
**Como** Recepción
**Quiero** crear y editar la ficha mínima del paciente
**Para** tener los datos necesarios para dar turnos

**Criterios de aceptación**:
- [ ] La ficha guarda nombre y apellido, teléfono, correo, DNI, obra social (dato de texto) y notas.
- [ ] El DNI es único por consultorio.
- [ ] No hay borrado físico de fichas.

**Reglas relacionadas**: RN-47, RN-48, RN-51, RN-58

### US-037 — Buscar pacientes (v1)
**Como** Recepción
**Quiero** buscar pacientes por apellido, DNI o teléfono
**Para** dar turnos con rapidez

**Criterios de aceptación**:
- [ ] La búsqueda acepta apellido, DNI y teléfono.
- [ ] El Profesional solo encuentra pacientes de su agenda.

**Reglas relacionadas**: RN-50

### US-038 — Historial de turnos del paciente (v1)
**Como** Recepción
**Quiero** ver los turnos pasados y futuros de un paciente con su estado
**Para** conocer su historial de asistencia

**Criterios de aceptación**:
- [ ] Se listan todos los turnos del paciente con estado.
- [ ] El Profesional ve solo los turnos del paciente que pertenecen a su agenda.

**Reglas relacionadas**: RN-21, RN-50

### US-039 — Vincular una cuenta con una ficha existente (v1)
**Como** Recepción
**Quiero** vincular la cuenta de un paciente con su ficha preexistente luego de verificar su identidad
**Para** evitar fichas duplicadas

**Criterios de aceptación**:
- [ ] Recepción ve la lista de solicitudes de vinculación (DNI declarado, correo de la cuenta y si está verificado, ficha existente) y puede consultar todas, sin filtrar por estado, para detectar intentos sospechosos. En una solicitud `vinculada`, la lista muestra la ficha vinculada.
- [ ] El detalle de la ficha muestra a Recepción y Administrador la cuenta vinculada (identificador, nombre de usuario, correo y si está verificado) o nada si no tiene cuenta; el Profesional no recibe datos de la cuenta (RN-63).
- [ ] La vinculación es manual, se resuelve desde la solicitud (vincular con la ficha elegida o rechazar con motivo opcional) y queda registrada con quién y cuándo.
- [ ] Una ficha ya vinculada a una cuenta, una ficha inactiva o una cuenta con el correo sin verificar no se pueden vincular (409). Vincular bloquea primero la fila de la ficha elegida y escribe después la solicitud (por el estado que Recepción vio) y la ficha (activa y sin cuenta), las dos de forma condicional y en una sola transacción: una solicitud ya vinculada responde 409, y dos vínculos simultáneos sobre la misma ficha, o de la misma solicitud con dos fichas, dejan uno solo y el otro recibe 409 sin cambiar nada, tampoco el estado de su solicitud. Un interbloqueo o un fallo de serialización del motor (`40P01`, `40001`) también responde 409, y una ficha que no existe en el consultorio responde 404.
- [ ] Al rechazar, si el correo de la cuenta está verificado, el paciente recibe un correo que le pide comunicarse con el consultorio, sin el motivo ni el DNI; con el correo sin verificar no se envía ningún correo y la cuenta, al verificar, ve el rechazo de la reserva (403).
- [ ] Después de un rechazo, Recepción puede vincular la cuenta con la ficha correcta o crear una ficha nueva y vincularla; el paciente no reintenta por su cuenta.
- [ ] Si la ficha correcta está ocupada por otra cuenta o inactiva, Recepción dispone de una salida (US-041, US-042).
- [ ] Hasta que se vincula, la cuenta no puede reservar en línea.

**Reglas relacionadas**: RN-48, RN-49, RN-62, RN-63

### US-041 — Desvincular una cuenta de una ficha (v1)
**Como** Recepción
**Quiero** desvincular una cuenta de paciente de su ficha, indicando el motivo
**Para** corregir un vínculo hecho por error o la ficha que tomó otra persona, sin perder la ficha ni sus turnos

**Criterios de aceptación**:
- [ ] Solo Recepción y Administrador desvinculan (`paciente.desvincular`); Profesional y Paciente reciben 403.
- [ ] Antes de desvincular, Recepción ve qué cuenta tiene la ficha en el detalle de la ficha (US-039).
- [ ] El motivo es obligatorio; sin motivo se rechaza (422).
- [ ] La ficha conserva sus datos y sus turnos; la cuenta queda sin ficha y no puede reservar (403 con el mensaje de que debe comunicarse con el consultorio, sin mencionar el DNI).
- [ ] Los refresh tokens de la cuenta se revocan en la misma transacción: no puede renovar su sesión. El token de acceso ya emitido sigue válido hasta vencer (JD-12, sin corregir), pero no le da acceso a la ficha ni a sus turnos: el token nunca lleva la ficha y el vínculo vigente se lee en cada solicitud (RN-06, RN-63).
- [ ] La solicitud de la cuenta queda `rechazada` con el motivo, quién lo hizo, cuándo y de qué ficha se la desvinculó; si la cuenta no tenía solicitud, se crea. No se envía ningún correo.
- [ ] Una ficha sin cuenta responde 409; dos desvinculaciones simultáneas de la misma ficha dejan una sola y la otra recibe 409.
- [ ] La cuenta desvinculada se puede vincular de nuevo con la ficha correcta (US-039).

**Reglas relacionadas**: RN-02, RN-06, RN-62, RN-63

### US-042 — Reactivar una ficha inactiva (v1)
**Como** Recepción
**Quiero** reactivar una ficha inactiva
**Para** poder vincularle la cuenta de su titular

**Criterios de aceptación**:
- [ ] Solo Recepción y Administrador reactivan (`paciente.reactivar`); Profesional y Paciente reciben 403.
- [ ] La ficha pasa a `activo = true` sin cambiar sus datos ni sus turnos; reactivar una ficha ya activa responde 409.
- [ ] Con la ficha reactiva, vincular la cuenta funciona (US-039).
- [ ] La v1 no tiene ninguna acción que desactive una ficha: `activo = false` solo existe para fichas cargadas o corregidas fuera de la aplicación, y reactivar sirve para recuperarlas (SU-47).

**Reglas relacionadas**: RN-47, RN-63

## Épica 9: Indicadores

### US-040 — Indicador de ausentismo (v1)
**Como** Administrador
**Quiero** ver cuántos turnos se pierden por ausencias
**Para** medir si el problema mejora

**Criterios de aceptación**:
- [ ] Muestra la cantidad de turnos `ausente` y la tasa de ausentismo por período y por profesional.
- [ ] Muestra también los turnos `liberado` y `cancelado` del período.
- [ ] Solo el Administrador lo ve.

**Reglas relacionadas**: RN-44, RN-45, RN-46

## Épica 10: Backlog (fuera de la v1)

En el orden de prioridad acordado.

| ID | Historia | Versión | Notas |
|----|----------|---------|-------|
| US-B01 | Auditoría y consentimiento de datos conforme a la Ley 25.326 | backlog (1) | Planificada, diferida de la v1. Riesgo: se almacenan datos personales desde la v1 (RN-58). |
| US-B02 | Lista de espera con relleno automático de huecos por cancelación | backlog (2) | |
| US-B03 | Seña o pago por Mercado Pago al reservar | backlog (3) | |
| US-B04 | Recall automático de controles periódicos | backlog (4) | |
| US-B05 | Conversación por la API oficial de WhatsApp Business, con envío automático de confirmaciones | backlog (5) | Reemplazaría el envío semimanual (RN-52). |
| US-B06 | Facturación ARCA, cobro y liquidación con obras sociales, contratos y documentación | backlog (6) | Funciones del rol Administrativo. |
| US-B07 | Odontograma, periodontograma, presupuestos y planes de tratamiento | backlog (7) | |
| US-B08 | Importación desde planilla o Google Calendar | backlog (8) | Diferida, sin fecha. |
