# Reglas de Negocio

Cada regla tiene un código único `RN-NN` (numeración correlativa, agrupada por dominio) para trazabilidad desde [06](06_funcionalidades.md), [07](07_flujos_principales.md) y [11](11_politicas_de_acceso_abac.md).

Convenciones:

- Las reglas marcadas **(Suposición)** no provienen literalmente de las fuentes; están registradas con su justificación en [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md).
- Los valores de horas (48, 24, 12, 24) provienen de las fuentes y se guardan como parámetros del consultorio con esos valores iniciales (SU-25).
- Los **hitos** se miden hacia atrás desde el inicio del turno.

## Resumen de la línea de tiempo de un turno

```text
   reserva          T-48 h              T-24 h             T-12 h          T (inicio)
      │                │                   │                  │                │
 pendiente ──► solicitud de ──► recordatorio ──► liberación automática ──► atendido / ausente
              confirmación      (RN-26)          (RN-27) o marca
              (RN-25)                            "sin confirmar" (RN-28)

 Hasta T-24 h el paciente puede cancelar o reprogramar por su cuenta (RN-33).
 Desde T-24 h debe llamar al consultorio.
```

## Dominio: Cuentas y autenticación

- **RN-01**: Solo los pacientes se registran por su cuenta desde el enlace público. El registro crea un `usuario` con rol `paciente` y su ficha de `paciente`.
- **RN-02**: Un paciente no puede ingresar ni reservar hasta verificar su correo. Mientras no esté verificado se ofrece reenviar el correo de verificación.
- **RN-03**: Los tokens de verificación de correo y de recuperación de contraseña son de un solo uso, vencen y se guardan hasheados. Un token usado o vencido se rechaza. La duración se define en el diseño (ver [10](10_preguntas_abiertas.md)).
- **RN-04**: Las contraseñas se almacenan únicamente como hash con un algoritmo adaptativo con sal. Nunca se registran en logs ni se devuelven por la API.
- **RN-05**: La recuperación de contraseña se hace con un enlace de un solo uso enviado al correo verificado. La respuesta a la solicitud es idéntica exista o no el correo, para no revelar qué cuentas existen. Al restablecer, se revocan las sesiones activas del usuario.
- **RN-06**: El JWT incluye como mínimo el identificador del usuario, `consultorio_id` y `rol` (incluido `paciente`). Los claims los emite solo el servidor al autenticar; el cliente no puede fijarlos.
- **RN-07 (Suposición)**: Las cuentas de personal (administrador, recepción, profesional, administrativo) las crea el Administrador. No hay autorregistro de personal.
- **RN-08 (Suposición)**: Cada usuario tiene exactamente un rol en la v1.
- **RN-09**: Los intentos fallidos de ingreso se limitan por cuenta y origen, con bloqueo temporal. Los umbrales y la duración del bloqueo se definen en el diseño.

## Dominio: Agenda y disponibilidad

- **RN-10**: Cada profesional tiene un box fijo, y un box pertenece a un solo profesional. Como consecuencia, validar los solapamientos por profesional alcanza para validar por box.
- **RN-11**: Cada profesional tiene su horario semanal propio, con uno o más bloques por día de la semana. Solo se ofrecen turnos dentro de esos bloques. Los bloques del mismo día no pueden superponerse.
- **RN-12**: Las excepciones por fecha (feriado, vacaciones, ausencia, bloqueo puntual) bloquean la agenda. Una excepción sin profesional (por ejemplo un feriado) aplica a todos los profesionales del consultorio.
- **RN-13**: La duración de un turno es la de la prestación elegida. El catálogo de prestaciones es editable por el Administrador. Las duraciones del catálogo inicial son sugerencias que el consultorio debe confirmar.
- **RN-14**: Un turno debe quedar completo dentro de un bloque del horario semanal del profesional y no puede intersectar una excepción. Los turnos no se parten entre bloques.
- **RN-15**: Cambiar la duración o desactivar una prestación no modifica los turnos ya creados; solo afecta a los nuevos.
- **RN-16 (Suposición)**: Si se crea una excepción sobre un período que ya tiene turnos, el sistema lo advierte y lista los turnos afectados. No los cancela en silencio: el personal debe cancelarlos o reprogramarlos de forma explícita, y el paciente recibe aviso (ver US-034 en [06](06_funcionalidades.md)).

## Dominio: Turnos y solapamientos

- **RN-17**: Un profesional no puede tener dos turnos superpuestos. Los turnos `cancelado` y `liberado` no cuentan. Los sobreturnos autorizados (RN-39) son la única excepción. La garantía final la da la base de datos (ver [04](04_modelo_de_datos.md)).
- **RN-18**: Los estados del turno son `pendiente`, `confirmado`, `ausente`, `atendido`, `cancelado` y `liberado`. Las transiciones permitidas son:

| Desde | Hacia | Quién o qué lo dispara | Condición |
|-------|-------|------------------------|-----------|
| (alta) | `pendiente` | Paciente o personal al reservar | RN-23 |
| `pendiente` | `confirmado` | Paciente, Recepción o Administrador | RN-30 |
| `pendiente` | `cancelado` | Paciente, Recepción o Administrador | RN-33, RN-34 |
| `pendiente` | `liberado` | Sistema (modo automático) o Recepción/Administrador (modo manual) | RN-27, RN-28 |
| `confirmado` | `cancelado` | Paciente, Recepción o Administrador | RN-33, RN-34 |
| `confirmado` | `pendiente` | Reprogramación | RN-32 |
| `pendiente` o `confirmado` | `atendido` | Profesional (propio), Recepción o Administrador | A partir de la hora de inicio |
| `pendiente` o `confirmado` | `ausente` | Profesional (propio), Recepción o Administrador | RN-44 |
| `ausente` | `atendido` | Recepción o Administrador (corrección) | Queda en el historial |

- **RN-19**: Un turno `atendido` no puede editarse ni cancelarse. Los estados `cancelado` y `liberado` son finales. `ausente` solo admite la corrección a `atendido` (RN-18).
- **RN-20 (Suposición)**: Existe el estado `liberado`, distinto de `cancelado`, para los turnos sin confirmar que se liberan por falta de confirmación (automática o manualmente). Se separa de `cancelado` para medir cuántos turnos se pierden por falta de confirmación frente a cuántos cancela el paciente o el personal, y para informar al paciente la causa.
- **RN-21**: Todo cambio de estado y toda reprogramación se registra en el historial con el actor (o el sistema), la fecha y hora y el estado anterior y nuevo.
- **RN-22**: Un turno `cancelado` o `liberado` libera el hueco de inmediato y queda disponible para nuevas reservas.
- **RN-23 (Suposición)**: Todo turno nace `pendiente`, sea reservado por el paciente o por Recepción. Recepción puede marcarlo `confirmado` en el momento de la reserva si el paciente lo confirma por teléfono o por WhatsApp.
- **RN-24**: Si dos reservas compiten por el mismo hueco, solo una prospera. La otra recibe un aviso de horario ocupado y se le ofrecen alternativas.

## Dominio: Confirmación, recordatorio y liberación

- **RN-25**: 48 horas antes del turno, el sistema pide confirmación: envía un correo automático y deja preparado el mensaje de WhatsApp para Recepción. Aplica a los turnos `pendiente`.
- **RN-26 (Suposición)**: 24 horas antes del turno, el sistema envía un recordatorio por correo (y deja preparado el de WhatsApp). Se envía a los turnos `pendiente` y `confirmado`; para los `pendiente` el texto advierte que serán liberados si no se confirman.
- **RN-27**: En modo automático (por defecto), un turno que sigue `pendiente` 12 horas antes del inicio pasa a `liberado` y el hueco queda disponible. **(Suposición)** El sistema avisa al paciente por correo que su turno fue liberado.
- **RN-28**: En modo manual, configurable por consultorio, el turno que sigue sin confirmar 12 horas antes **no** se libera: queda `pendiente` con la marca "sin confirmar", visible para Recepción en una lista dedicada. Recepción decide si llama al paciente o libera el turno.
- **RN-29 (Suposición)**: Si un turno se crea o reprograma cuando uno o más hitos ya vencieron, esos hitos se omiten (no se envían retroactivamente). La liberación automática solo se aplica a un turno si el hito de solicitud de confirmación pudo emitirse después de su creación o última reprogramación; en caso contrario el turno queda con la marca "sin confirmar" para que Recepción decida. Ver pregunta abierta en [10](10_preguntas_abiertas.md).
- **RN-30**: El paciente confirma desde su cuenta. **(Suposición)** También puede confirmar con un enlace de un solo uso incluido en el correo, sin ingresar la contraseña, para reducir la fricción antes de la liberación. Recepción y Administrador pueden confirmar por el paciente cuando este lo hace por teléfono o WhatsApp. No se puede confirmar un turno ya `liberado`; el paciente debe reservar de nuevo.
- **RN-31**: Si un envío de correo falla, se reintenta de forma acotada y, si persiste el fallo, la notificación queda `fallida` y visible para Recepción, que puede avisar por WhatsApp. Un envío fallido no cambia por sí mismo el estado del turno.
- **RN-32 (Suposición)**: Reprogramar un turno vuelve su estado a `pendiente` y reinicia el ciclo de hitos con los nuevos horarios (se incrementa `ciclo_confirmacion` y las notificaciones pendientes anteriores pasan a `omitida`).

## Dominio: Cancelación y reprogramación

- **RN-33**: El paciente puede cancelar o reprogramar su turno por su cuenta hasta 24 horas antes de su inicio. Pasado ese plazo, la interfaz bloquea la acción y muestra el teléfono del consultorio para que llame.
- **RN-34**: Recepción y Administrador pueden cancelar o reprogramar un turno en cualquier momento mientras no esté `atendido` (RN-19).
- **RN-35**: Un paciente solo ve y opera sobre sus propios turnos.
- **RN-36**: Cancelar no borra el turno: pasa a `cancelado` y se registra quién, cuándo y, opcionalmente, el motivo.
- **RN-37**: Reprogramar es un cambio atómico: el nuevo horario se valida (RN-14, RN-17) y se reserva antes de liberar el anterior. Si el nuevo horario no está disponible, el turno original permanece intacto. Se conserva el mismo turno y se registra la reprogramación en el historial.
- **RN-38 (Suposición)**: El Profesional solo puede marcar `atendido` o `ausente` en turnos de su propia agenda. No crea, mueve ni cancela turnos; eso lo hace Recepción.

## Dominio: Sobreturnos

- **RN-39**: Un sobreturno es un turno que se superpone a otro del mismo profesional. Solo lo otorgan Recepción o Administrador, con autorización explícita en el momento. Los pacientes nunca pueden generar un sobreturno.
- **RN-40**: Todo sobreturno exige avisar al profesional afectado, y el aviso queda registrado. **(Suposición)** La respuesta del profesional (aprobado o rechazado) se registra si la da, pero no bloquea el otorgamiento; ver pregunta abierta en [10](10_preguntas_abiertas.md).
- **RN-41**: Se registra quién autorizó el sobreturno, cuándo y el motivo.
- **RN-42**: Los sobreturnos se muestran marcados en la agenda y en las vistas del turno.
- **RN-43 (Suposición)**: Un sobreturno debe respetar el horario semanal del profesional y sus excepciones (RN-11, RN-12): no se otorga fuera de horario ni sobre un bloqueo.

## Dominio: Ausentismo

- **RN-44**: Un turno solo puede marcarse `ausente` una vez que pasó su hora de inicio. Lo marcan el Profesional (en su propia agenda), Recepción o Administrador.
- **RN-45 (Suposición)**: La tasa de ausentismo de un período es `ausentes / (atendidos + ausentes)`, sobre los turnos cuya hora ya llegó. Se presenta por profesional y por período, junto con la cantidad de turnos `liberado` y `cancelado` para no ocultar otras pérdidas. La definición exacta se valida con el Administrador.
- **RN-46**: El indicador de ausentismo lo ve el Administrador. El rol Administrativo tiene el permiso reservado.

## Dominio: Pacientes

- **RN-47 (Suposición)**: La ficha mínima contiene nombre y apellido, teléfono, correo, DNI, obra social y notas. Son obligatorios nombre, apellido, teléfono, correo y DNI; obra social y notas son opcionales. La reserva online pide los mismos datos.
- **RN-48**: El DNI es único por consultorio. No se admite una segunda ficha con el mismo DNI.
- **RN-49 (Suposición)**: Si un paciente se registra con un DNI que ya tiene ficha creada por Recepción, el sistema no vincula la cuenta de forma automática (para impedir que alguien reclame la ficha de otra persona). Recepción verifica la identidad y vincula manualmente.
- **RN-50**: El Profesional ve únicamente a los pacientes con turnos en su propia agenda. Recepción y Administrador ven todos los pacientes del consultorio. El paciente ve solo su propia ficha.
- **RN-51**: La obra social es solo un dato de texto. No hay validación, convenio ni cobertura en la v1.

## Dominio: Comunicación

- **RN-52**: Para WhatsApp, el sistema arma el texto del mensaje y un enlace `wa.me` con el teléfono y el texto prellenado. Recepción lo abre y lo envía con un clic. Recepción marca la notificación como enviada (`enviada_manual`); el sistema no puede verificar la entrega. No se usa la API oficial de WhatsApp Business en la v1.
- **RN-53 (Suposición)**: Los teléfonos se normalizan a formato internacional, con código de país de Argentina por defecto, para construir el enlace de WhatsApp.
- **RN-54 (Suposición)**: Los mensajes de correo y WhatsApp contienen solo lo necesario: nombre del paciente, fecha, hora, profesional, consultorio y la acción requerida. No incluyen datos de salud ni la prestación detallada.

## Dominio: Multiconsultorio y protección de datos

- **RN-55**: Toda tabla que pertenece a un consultorio lleva `consultorio_id`, y toda consulta se filtra por el `consultorio_id` del token.
- **RN-56**: Ningún usuario accede a datos de otro consultorio (atributo "consultorio" de las políticas, ver [11](11_politicas_de_acceso_abac.md)).
- **RN-57**: En la v1 hay un único consultorio activo. El alta de consultorios y su administración están fuera de alcance.
- **RN-58**: Desde la v1 se almacenan datos personales de pacientes, por lo que la Ley 25.326 aplica aunque la auditoría y el consentimiento estén diferidos. Mientras tanto se aplica el mínimo: datos limitados a los de RN-47, acceso restringido por rol y atributos, contraseñas hasheadas, comunicación por HTTPS y sin borrado físico de fichas. El riesgo queda registrado en [09](09_decisiones_y_supuestos.md).

## Dominio: Excepciones globales

- Un turno `atendido` es inmutable (RN-19) sin excepción, ni siquiera para el Administrador.
- La prevención de solapamientos (RN-17) y el aislamiento por consultorio (RN-55) se garantizan en la base de datos y en las políticas, no solo en la interfaz.
- Ninguna regla de esta lista usa borrado físico; la trazabilidad prevalece (RN-21, RN-36).
