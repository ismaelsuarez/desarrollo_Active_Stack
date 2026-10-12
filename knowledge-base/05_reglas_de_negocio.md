# Reglas de Negocio

Cada regla tiene un código único `RN-NN` (numeración correlativa, agrupada por dominio) para trazabilidad desde [06](06_funcionalidades.md), [07](07_flujos_principales.md) y [11](11_politicas_de_acceso_abac.md).

Convenciones:

- Las reglas marcadas **(Suposición)** no provienen literalmente de las fuentes; están registradas con su justificación en [09_decisiones_y_supuestos.md](09_decisiones_y_supuestos.md).
- Los valores de horas (48, 24, 12, 24) provienen de las fuentes y se guardan como parámetros del consultorio con esos valores iniciales (SU-25).
- Los **hitos** se miden hacia atrás desde el inicio del turno.
- RN-59 a RN-63 se agregaron el 2026-10-11 con las decisiones del dueño del proyecto (DD-16 a DD-21 en [09](09_decisiones_y_supuestos.md)). Quedan dentro de su dominio, sin renumerar las reglas existentes. El mismo día se ampliaron RN-06, RN-26, RN-28, RN-32, RN-58, RN-59, RN-60, RN-61 y RN-62 tras los rejuicios de la auditoría (`discovery/auditoria-base-2026-10-09.md`).

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

- **RN-01**: Solo los pacientes se registran por su cuenta desde el enlace público. El registro crea un `usuario` con rol `paciente` y su ficha de `paciente`. Si el DNI ya tiene ficha en el consultorio, no crea una segunda: crea una solicitud de vinculación (RN-49, RN-62).
- **RN-02**: Un paciente no puede ingresar ni reservar hasta verificar su correo. Mientras no esté verificado se ofrece reenviar el correo de verificación. Una cuenta de paciente que no tiene ficha (porque su solicitud de vinculación está `pendiente` o `rechazada`, RN-62) tampoco puede reservar en línea: la reserva se rechaza con 403 y el mensaje de que debe comunicarse con el consultorio para verificar su cuenta, sin mencionar el DNI.
- **RN-03**: Los tokens de verificación de correo y de recuperación de contraseña son de un solo uso, vencen y se guardan hasheados. Un token usado o vencido se rechaza. La duración se define en el diseño (ver [10](10_preguntas_abiertas.md)).
- **RN-04**: Las contraseñas se almacenan únicamente como hash con un algoritmo adaptativo con sal. Nunca se registran en logs ni se devuelven por la API.
- **RN-05**: La recuperación de contraseña se hace con un enlace de un solo uso enviado al correo verificado. La respuesta a la solicitud es idéntica exista o no el correo, para no revelar qué cuentas existen. Al restablecer, se revocan las sesiones activas del usuario.
- **RN-06**: El JWT incluye como mínimo el identificador del usuario, `consultorio_id` y `rol` (incluido `paciente`). El token de acceso nunca lleva la ficha ni el identificador del paciente: el vínculo entre la cuenta y su ficha se lee de la base en cada solicitud (RN-63). Los claims los emite solo el servidor al autenticar; el cliente no puede fijarlos.
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
- **RN-26 (Suposición)**: 24 horas antes del turno, el sistema envía un recordatorio por correo (y deja preparado el de WhatsApp). Se envía a los turnos `pendiente` y `confirmado`; para los `pendiente` el texto advierte que serán liberados si no se confirman solo cuando ese turno puede liberarse de forma automática según RN-60 al armar el recordatorio (consultorio en modo automático, solicitud de confirmación de su ciclo actual `enviada`, turno sin la marca "sin confirmar" y sin comenzar). En cualquier otro caso (modo manual, solicitud no enviada, turno ya marcado) el texto solo le pide que confirme, sin advertir una liberación que no ocurriría.
- **RN-27**: En modo automático (por defecto), un turno que sigue `pendiente` 12 horas antes del inicio y cumple las condiciones de RN-60 pasa a `liberado` y el hueco queda disponible. **(Suposición)** El sistema avisa al paciente por correo que su turno fue liberado.
- **RN-28**: En modo manual, configurable por consultorio, el turno que sigue sin confirmar 12 horas antes **no** se libera: queda `pendiente` con la marca "sin confirmar", visible para Recepción en una lista dedicada. Recepción decide si llama al paciente o libera el turno. El barrido no selecciona ni marca un turno cuyo inicio ya pasó: ese turno sigue la regla de atendido o ausente (RN-44).
- **RN-29 (Suposición)**: Si un turno se crea o reprograma cuando uno o más hitos ya vencieron, esos hitos se omiten (no se envían retroactivamente). Como consecuencia, no existe una solicitud de confirmación enviada para ese ciclo y el turno no se libera de forma automática (RN-60): queda con la marca "sin confirmar" para que Recepción decida. Ver pregunta abierta en [10](10_preguntas_abiertas.md).
- **RN-30**: El paciente confirma desde su cuenta. **(Suposición)** También puede confirmar con un enlace de un solo uso incluido en el correo, sin ingresar la contraseña, para reducir la fricción antes de la liberación. Recepción y Administrador pueden confirmar por el paciente cuando este lo hace por teléfono o WhatsApp. No se puede confirmar un turno ya `liberado`; el paciente debe reservar de nuevo.
- **RN-31**: Si un envío de correo falla, se reintenta de forma acotada y, si persiste el fallo, la notificación queda `fallida` y visible para Recepción, que puede avisar por WhatsApp. Un envío fallido no cambia por sí mismo el estado del turno, pero si es la solicitud de confirmación impide la liberación automática de ese turno (RN-60). El despacho es al menos una vez (RN-61).
- **RN-32 (Suposición)**: Reprogramar un turno vuelve su estado a `pendiente` y reinicia el ciclo de hitos con los nuevos horarios (se incrementa `ciclo_confirmacion`, las notificaciones `programada` o `preparada` anteriores, de cualquier canal, de solicitud de confirmación y de recordatorio pasan a `omitida` (no así los avisos al paciente por el cambio, ver "Vigencia por tipo" en [04](04_modelo_de_datos.md)) y se limpia la marca "sin confirmar" `marcado_sin_confirmar_en`: la marca pertenece al ciclo, y el turno reprogramado se evalúa de nuevo en su ciclo nuevo).
- **RN-60**: La liberación automática (RN-27) solo se aplica a un turno `pendiente` si se cumplen las dos condiciones siguientes: (a) la notificación `solicitud_confirmacion` por correo de su ciclo de confirmación actual está en estado `enviada`; (b) el turno todavía no comenzó. Si ese envío falló (`fallida`), fue omitido (`omitida`), sigue `programada` o está `enviando`, o no existe porque el hito ya había vencido al crear o reprogramar el turno (RN-29), el turno queda `pendiente` con la marca "sin confirmar" para que Recepción decida, igual que en RN-28, y deja de ser candidato a la liberación automática. Un turno cuyo inicio ya pasó nunca se libera de forma automática ni recibe la marca: queda fuera de la selección del barrido, que no lo reevalúa, y el personal lo marca `atendido` o `ausente` (RN-44). Por eso la selección de candidatos y las dos actualizaciones condicionales de abajo incluyen "el turno todavía no comenzó" (`inicio` posterior a `ahora`, con el reloj inyectado). Dentro de un mismo ciclo, un turno que recibió la marca no se vuelve a evaluar para la liberación automática aunque su solicitud de confirmación se envíe después: decide Recepción (la marca se limpia solo al reprogramar, RN-32). No se exige una separación mínima entre el envío de la solicitud y la liberación. Liberar y marcar son cada una una sola actualización condicional sobre el turno (sigue `pendiente`, sin marca, en el ciclo evaluado y sin comenzar), y la fila de historial se escribe en la misma transacción solo si esa actualización afectó una fila: dos barridos simultáneos producen una sola.

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
- **RN-49**: Si un paciente se registra con un DNI que ya tiene ficha en el consultorio, el sistema crea la cuenta pero no crea una segunda ficha ni vincula la cuenta de forma automática (para impedir que alguien reclame la ficha de otra persona). Guarda una solicitud de vinculación con el DNI declarado (RN-62). Recepción verifica la identidad y vincula o rechaza. Decidido por el dueño del proyecto el 2026-10-11 (DD-19).
- **RN-50**: El Profesional ve únicamente a los pacientes con turnos en su propia agenda. Recepción y Administrador ven todos los pacientes del consultorio. El paciente ve solo su propia ficha.
- **RN-51**: La obra social es solo un dato de texto. No hay validación, convenio ni cobertura en la v1.
- **RN-62**: La solicitud de vinculación guarda el usuario que la origina, el DNI declarado en el registro y su estado (`pendiente`, `vinculada` o `rechazada`). La respuesta del registro y el correo de verificación son idénticos exista o no el DNI. Eso no impide por completo deducir que un DNI ya era paciente: quien se registra con el DNI de otra persona y verifica su propio correo ve rechazada su reserva (403) y puede inferir que ese DNI ya figuraba en el consultorio. El riesgo residual lo aceptó el dueño del proyecto y se acota con tres medidas: (a) el registro tiene un límite de solicitudes por origen: el origen es la dirección del cliente tomada del encabezado de reenvío, confiando solo en la cantidad de saltos de proxy que indica la configuración (`TRUSTED_PROXY_HOPS`) y nunca en un valor que envíe el cliente más allá de ellos; si no se puede determinar un origen rige un límite global; el origen se guarda solo como hash con clave en `intento_registro` (DD-21, [04](04_modelo_de_datos.md) y [08](08_arquitectura_propuesta.md)); (b) el estado de la vinculación solo lo ve una cuenta con el correo verificado (el registro, el reenvío y el ingreso no lo muestran, y la reserva exige sesión y correo verificado, RN-02); (c) toda solicitud queda registrada y Recepción puede consultarlas todas, sin filtrar por estado, para detectar intentos sospechosos, como varias cuentas sobre el mismo DNI. Un paciente nuevo con un DNI nuevo reserva por su cuenta sin pasar por Recepción. Dos registros simultáneos con el mismo DNI nuevo se resuelven sin abortar la transacción: la ficha se inserta con `ON CONFLICT DO NOTHING` sobre la unicidad del DNI y, si no se insertó, el registro sigue por la solicitud (ver [04](04_modelo_de_datos.md)); ambos reciben la misma respuesta.

  Una cuenta sin ficha (solicitud `pendiente` o `rechazada`, también la de una cuenta desvinculada, RN-63) no puede reservar en línea (costo aceptado): la reserva responde 403 con el mensaje de que debe comunicarse con el consultorio para verificar su cuenta, que no menciona el DNI ni el estado de la solicitud. Recepción y Administrador ven la lista de solicitudes, verifican la identidad y resuelven: vinculan la cuenta con la ficha que eligen (la cuenta pasa a ser la titular de esa ficha) o rechazan. Vincular se rechaza con 409, sin cambiar nada, si la ficha está inactiva, si ya tiene otra cuenta o si el correo de la cuenta aún no está verificado; Recepción tiene salida para cada una (RN-63). Vincular bloquea primero la fila de la ficha elegida y hace después dos escrituras condicionales en la misma transacción, primero la solicitud (por el estado que Recepción vio) y después la ficha (activa y sin cuenta): si cualquiera no afecta ninguna fila (por ejemplo, una solicitud ya vinculada, o dos vínculos simultáneos sobre la misma ficha), o si choca con la unicidad de `paciente.usuario_id`, o si el motor informa un interbloqueo o un fallo de serialización (`40P01`, `40001`), la operación responde 409 y no cambia nada, tampoco el estado de la solicitud. Si la ficha elegida no existe en el consultorio, responde 404 y tampoco cambia nada. Si el DNI de la ficha cambió después de la solicitud no hay conflicto: la ficha la elige Recepción y no se compara con el DNI declarado.

  Al rechazar, el paciente recibe un correo que le pide comunicarse con el consultorio, sin el motivo ni el DNI, solo si el correo de su cuenta está verificado: una cuenta con el correo sin verificar no recibe correo del consultorio (el consultorio no escribe a una dirección que nadie probó controlar, SU-42) y, cuando lo verifica, se entera por el rechazo de la reserva (403 con el mismo mensaje). Un rechazo no deja a la cuenta sin salida del lado de Recepción: puede después vincular esa cuenta con la ficha correcta o crear una ficha nueva y vincularla (una solicitud `rechazada` puede pasar a `vinculada`; ver RN-63 para los casos con la ficha ocupada, inactiva o en manos de otra cuenta). El paciente no reintenta por su cuenta y no hay un formulario nuevo para él, de modo que la salida depende de que contacte al consultorio. Cada resolución registra quién la hizo y cuándo; el registro conserva solo la última.

- **RN-63**: Recepción y Administrador pueden **desvincular** una cuenta de paciente de su ficha y **reactivar** una ficha inactiva (decisión del dueño del proyecto, DD-20). Desvincular exige un motivo (obligatorio): la ficha conserva sus datos y sus turnos; la cuenta queda sin ficha y no puede reservar (403 como toda cuenta sin ficha, RN-02, RN-62); sus sesiones renovables se revocan en la misma transacción; y puede vincularse de nuevo. Queda registrado quién desvinculó, cuándo, el motivo y de qué ficha, en la propia solicitud de vinculación de la cuenta, que pasa a `rechazada` (se crea si la cuenta se registró con un DNI nuevo y no tenía solicitud): conserva solo la última resolución, y la auditoría general sigue diferida (RN-58). No se envía ningún correo: no es el rechazo de una solicitud. Reactivar pone la ficha en `activo = true`; no exige motivo. La v1 no tiene ninguna acción que desactive una ficha: `activo` existe para fichas cargadas o corregidas fuera de la aplicación, y reactivar existe para recuperar una ficha así (SU-47). Para actuar sobre el vínculo, Recepción y Administrador lo ven: el detalle de la ficha devuelve la cuenta vinculada (identificador, nombre de usuario, correo y si está verificado) o nada si no tiene cuenta, y la lista de solicitudes devuelve la ficha vinculada cuando la solicitud está `vinculada`; el Profesional no recibe datos de la cuenta, y no se devuelve ningún otro dato (minimización, RN-58; detalle en [04](04_modelo_de_datos.md)). Con estas dos acciones, más vincular y rechazar (RN-62) y crear una ficha (RN-47), Recepción resuelve los casos así (la secuencia de pasos está en el flujo 1 de [07](07_flujos_principales.md)):
  - Vínculo equivocado hecho por error: desvincular la cuenta de la ficha equivocada y vincularla con la correcta.
  - La ficha correcta ya tiene otra cuenta: Recepción verifica quién corresponde; si es la otra cuenta, rechaza la solicitud; si no, desvincula a la otra cuenta y vincula la solicitud.
  - La ficha correcta está inactiva: reactivarla y vincular.
  - Un tercero se registró primero con un DNI nuevo y tiene la ficha: desvincular su cuenta, cancelar los turnos que no correspondan (la ficha conserva los turnos de quien la tuvo; se cancelan antes de corregir la ficha para que el aviso llegue al correo que la ficha tenía), corregir los datos de la ficha con la edición de pacientes y vincular la cuenta de la persona correcta.

  Estas son acciones del personal: ninguna cuenta se recupera sola, y llegar a la salida depende de que el paciente contacte al consultorio. Límite conocido: el token de acceso ya emitido sigue siendo válido hasta vencer (hallazgo JD-12 de la auditoría, sin corregir) y desvincular solo revoca los tokens de renovación. Como el token de acceso nunca lleva la ficha (RN-06) y la capa de aplicación carga en cada solicitud la ficha vigente de la cuenta (`paciente.usuario_id`) y se la pasa a la política A1 de [11](11_politicas_de_acceso_abac.md), la cuenta desvinculada deja de acceder a la ficha y a sus turnos de inmediato aunque su token siga vigente.

## Dominio: Comunicación

- **RN-52**: Para WhatsApp, el sistema arma el texto del mensaje y un enlace `wa.me` con el teléfono y el texto prellenado. Recepción lo abre y lo envía con un clic. Recepción marca la notificación como enviada (`enviada_manual`); el sistema no puede verificar la entrega. No se usa la API oficial de WhatsApp Business en la v1.
- **RN-53 (Suposición)**: Los teléfonos se normalizan a formato internacional, con código de país de Argentina por defecto, para construir el enlace de WhatsApp.
- **RN-54 (Suposición)**: Los mensajes de correo y WhatsApp contienen solo lo necesario: nombre del paciente, fecha, hora, profesional, consultorio y la acción requerida. No incluyen datos de salud ni la prestación detallada.
- **RN-61**: El despacho de notificaciones es al menos una vez, no exactamente una vez. El barrido reclama cada fila por separado con `SELECT ... FOR UPDATE SKIP LOCKED`, la pasa a `enviando` con la hora de la reclamación y confirma esa transacción corta; envía el correo fuera de toda transacción y registra el resultado en una segunda transacción corta (`enviada`, o el reintento acotado y `fallida` de RN-31). El resultado se escribe solo si la fila sigue `enviando` con la misma hora de reclamación que fijó este envío; si no, el envío perdió la reclamación y descarta su resultado sin escribir. Una reclamación más vieja que el plazo configurado se revisa en un barrido posterior, que aplica la misma validación de vigencia que la primera reclamación y respeta el máximo de intentos. La vigencia depende del tipo de notificación (tabla "Vigencia por tipo" en [04](04_modelo_de_datos.md)): un recordatorio de un turno que ya no corresponde pasa a `omitida`, y un aviso de algo que ya ocurrió (liberación, cancelación o reprogramación por el personal, resumen de la reserva, confirmación de la cancelación del paciente, rechazo de una solicitud, correos de cuenta) no depende del turno. Con el tipo vigente, al alcanzar el máximo de intentos pasa a `fallida` sin reenviar. Una caída entre el envío y el registro del resultado, o un envío más lento que el plazo, puede repetir un correo. Dos barridos simultáneos pueden ejecutarse a la vez y nunca reclaman la misma fila. El tope diario de correos se verifica antes de toda reclamación que enviaría un correo: con el tope alcanzado el barrido no reclama más correos, que siguen `programada` sin consumir intentos, ni reclama de nuevo una reclamación vencida. El conteo suma los correos enviados del día y las reclamaciones `enviando` que no vencieron. Pasar una reclamación vencida a `omitida` o a `fallida` no envía nada y no se frena por el tope (ver [04](04_modelo_de_datos.md)).

## Dominio: Multiconsultorio y protección de datos

- **RN-55**: Toda tabla que pertenece a un consultorio lleva `consultorio_id`, y toda consulta se filtra por el `consultorio_id` del token (o el que resuelve el servidor en los flujos sin token, RN-59).
- **RN-56**: Ningún usuario accede a datos de otro consultorio (atributo "consultorio" de las políticas, ver [11](11_politicas_de_acceso_abac.md)).
- **RN-57**: En la v1 hay un único consultorio activo. El alta de consultorios y su administración están fuera de alcance.
- **RN-58**: Desde la v1 se almacenan datos personales de pacientes, por lo que la Ley 25.326 aplica aunque la auditoría y el consentimiento estén diferidos. Mientras tanto se aplica el mínimo: datos limitados a los de RN-47, acceso restringido por rol y atributos, contraseñas hasheadas, comunicación por HTTPS y sin borrado físico de fichas. El límite de registros por origen guarda la dirección del cliente solo como hash con clave (HMAC con un secreto del servidor) en `intento_registro`, con retención de 24 horas: un hash de una dirección sigue siendo un dato personal y se trata como tal (RN-62, DD-21). El riesgo queda registrado en [09](09_decisiones_y_supuestos.md).
- **RN-59**: El cliente nunca envía el `consultorio_id`. Con token, se lee del `Principal`. Sin token, la regla es por tipo de flujo y no por prefijo de ruta. Una ruta que recibe un token de un solo uso enviado por correo, o un token de renovación, toma el consultorio de la fila a la que apunta ese token: verificación de correo (`POST /auth/verificar-email`), restablecimiento de contraseña (`POST /auth/restablecer-password`), confirmación por enlace (`POST /turnos/confirmar-por-enlace`) y renovación de sesión (`POST /auth/refresh`). Las demás rutas sin token (`/auth/login`, `/auth/registro`, `/auth/reenviar-verificacion`, `/auth/recuperar-password` y las lecturas públicas `/publico/*`, que no reciben ningún token) las resuelve el servidor: en la v1, el único consultorio activo, indicado por su configuración (`CONSULTORIO_ACTIVO_ID`, variable obligatoria), a través de una única dependencia. El barrido toma el de cada fila que procesa. Pasar a varios consultorios exige cambiar esa dependencia y las rutas públicas (DD-16).

## Dominio: Excepciones globales

- Un turno `atendido` es inmutable (RN-19) sin excepción, ni siquiera para el Administrador.
- La prevención de solapamientos (RN-17) y el aislamiento por consultorio (RN-55) se garantizan en la base de datos y en las políticas, no solo en la interfaz.
- Ninguna regla de esta lista usa borrado físico; la trazabilidad prevalece (RN-21, RN-36).
