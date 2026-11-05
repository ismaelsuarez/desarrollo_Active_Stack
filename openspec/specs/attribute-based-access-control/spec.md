# attribute-based-access-control Specification

## Purpose
Define las políticas de autorización basadas en atributos (ABAC) del dominio odontológico, asegurando aislamiento multi-inquilino estricto, propiedad de agendas y turnos, validez de transiciones de estado y respeto de ventanas temporales.

## Requirements

### Requirement: Aislamiento estricto por consultorio (A2)
La evaluación de políticas MUST comprobar en primer lugar que el `consultorio_id` del usuario autenticado coincida con el `consultorio_id` del recurso objetivo. Si los identificadores no coinciden, la solicitud SHALL ser denegada inmediatamente indicando código HTTP 404 para no revelar la existencia de datos ajenos.

#### Scenario: Usuario accede a recurso de su propio consultorio
- **WHEN** un usuario autenticado intenta operar sobre un recurso con su mismo `consultorio_id`
- **THEN** la verificación de consultorio es exitosa y permite continuar con las demás políticas

#### Scenario: Usuario intenta acceder a recurso de otro consultorio
- **WHEN** un usuario autenticado intenta operar sobre un recurso cuyo `consultorio_id` difiere del suyo
- **THEN** la solicitud es denegada inmediatamente con motivo de aislamiento y código HTTP 404

### Requirement: Propiedad de agenda y titularidad de turnos (A1)
Un profesional MUST acceder solo a turnos de su agenda. Un paciente MUST operar solo sobre turnos de su ficha vigente. Turno ajeno consultado u operado por identificador, ficha no vinculada y recurso de otro consultorio SHALL responder 404; pedir la agenda de un colega del mismo consultorio SHALL responder 403 (KB 11 §Matriz de decisión; RN-35, RN-50, RN-55).

#### Scenario: Profesional accede a turno de su propia agenda
- **WHEN** un profesional solicita ver o gestionar un turno asignado a su identificador profesional
- **THEN** la política de dueño de agenda permite continuar con las restantes comprobaciones de la acción

#### Scenario: Profesional intenta acceder a turno de otro profesional
- **WHEN** un profesional solicita ver o gestionar por identificador un turno asignado a otro profesional
- **THEN** la política deniega el acceso con código HTTP 404

#### Scenario: Paciente con ficha vigente opera sobre su turno
- **WHEN** un paciente con ficha_vigente_id válida opera sobre un turno asociado a ese mismo paciente_id
- **THEN** la política de titularidad permite continuar con las restantes comprobaciones de la acción

#### Scenario: Paciente intenta operar sobre turno ajeno o sin ficha vigente
- **WHEN** un paciente intenta operar sobre un turno de otro paciente o la cuenta no tiene ficha vinculada
- **THEN** la política deniega el acceso con código HTTP 404

#### Scenario: Profesional solicita agenda de un colega
- **WHEN** un profesional consulta la agenda de otro profesional del mismo consultorio
- **THEN** la política deniega con 403, sin alterar el 404 aplicable a turnos por identificador

### Requirement: Modificabilidad y transiciones de estado del turno (A3)
Las operaciones de modificación, cancelación o reprogramación MUST permitirse únicamente sobre turnos en estado modificable (`pendiente` o `confirmado`). Los turnos en estado `atendido`, `cancelado` o `liberado` son finales e inmutables. Un turno en estado `ausente` SHALL rechazar cancelaciones o reprogramaciones y solo admitirá la acción de corrección hacia `atendido`. Toda transición MUST cumplir la tabla de estados de RN-18.

#### Scenario: Modificación permitida en estado pendiente o confirmado
- **WHEN** se solicita reprogramar o cancelar un turno en estado `pendiente` o `confirmado`
- **THEN** la política de modificabilidad aprueba la operación

#### Scenario: Rechazo de modificación en turno atendido o cancelado
- **WHEN** se solicita modificar, cancelar o reprogramar un turno en estado `atendido`, `cancelado` o `liberado`
- **THEN** la política deniega la operación con código HTTP 403

#### Scenario: Turno ausente solo admite corrección a atendido
- **WHEN** se solicita la acción `turno.corregir_ausente` sobre un turno en estado `ausente`
- **THEN** la política autoriza la transición hacia `atendido`

#### Scenario: Rechazo de cancelación sobre turno ausente
- **WHEN** se solicita cancelar un turno en estado `ausente`
- **THEN** la política deniega la operación con código HTTP 403

### Requirement: Ventanas temporales y hora de inicio (A4)
Las solicitudes de cancelación o reprogramación solicitadas por el paciente MUST realizarse dentro de la ventana de anticipación configurada (`ahora <= inicio - horas_limite`). Las acciones para marcar un turno como `atendido` o `ausente` MUST permitirse únicamente si la hora actual ha alcanzado o superado el inicio del turno (`ahora >= inicio`). Cualquier violación temporal SHALL denegarse con código HTTP 403.

#### Scenario: Paciente cancela o reprograma con más de 24 horas de anticipación
- **WHEN** un paciente solicita cancelar un turno y el instante `ahora` es anterior al inicio por al menos 24 horas
- **THEN** la política de ventana temporal aprueba la acción

#### Scenario: Paciente intenta cancelar o reprogramar con menos de 24 horas de anticipación
- **WHEN** un paciente solicita cancelar un turno faltando menos del plazo límite configurado
- **THEN** la política deniega la acción con código HTTP 403 indicando expiración de ventana

#### Scenario: Marcar atendido o ausente habiendo alcanzado la hora de inicio
- **WHEN** el personal registra `turno.atendido` o `turno.ausente` cuando `ahora >= turno.inicio`
- **THEN** la política de horario autoriza el cambio

#### Scenario: Marcar atendido o ausente antes de la hora de inicio
- **WHEN** se intenta marcar `turno.atendido` o `turno.ausente` antes de que empiece el turno
- **THEN** la política deniega el cambio con código HTTP 403

### Requirement: Autorización de sobreturnos y respuesta del profesional
La autorización de un sobreturno (`sobreturno.autorizar`) MUST estar reservada exclusivamente a los roles `recepcion` y `administrador`. La respuesta de aprobación o rechazo a un aviso de sobreturno (`sobreturno.responder`) MUST permitirse únicamente al profesional cuya agenda se ve afectada, o al administrador si este posee agenda propia y se trata de su turno.

#### Scenario: Recepción autoriza sobreturno
- **WHEN** un usuario con rol `recepcion` ejecuta `sobreturno.autorizar`
- **THEN** la política autoriza la acción

#### Scenario: Profesional responde sobreturno de su propia agenda
- **WHEN** un profesional ejecuta `sobreturno.responder` sobre un sobreturno de su propia agenda
- **THEN** la política autoriza la respuesta

#### Scenario: Profesional o administrador intenta responder sobreturno de agenda ajena
- **WHEN** un usuario intenta responder un sobreturno asignado a otro profesional
- **THEN** la política deniega la acción con código HTTP 403

### Requirement: Liberación manual y condicional de turnos pendientes
La acción `turno.liberar` ejecutada por `recepcion` o `administrador` MUST autorizarse únicamente si el turno se encuentra en estado `pendiente` y se cumple alguna de las siguientes condiciones: el consultorio está configurado en modo manual, o el turno posee la marca de "sin confirmar". En modo automático sin marca "sin confirmar", la solicitud SHALL ser denegada con código HTTP 403. Los roles `profesional` y `paciente` MUST ser siempre denegados.

#### Scenario: Recepción libera turno en modo manual
- **WHEN** un usuario con rol `recepcion` solicita liberar un turno `pendiente` en un consultorio con modo manual
- **THEN** la política autoriza la liberación

#### Scenario: Recepción libera turno con marca sin confirmar en modo automático
- **WHEN** se solicita liberar un turno `pendiente` con marca "sin confirmar" en un consultorio con modo automático
- **THEN** la política autoriza la liberación

#### Scenario: Rechazo de liberación en modo automático sin marca de confirmación
- **WHEN** se intenta liberar manualmente un turno `pendiente` sin marca "sin confirmar" en modo automático
- **THEN** la política deniega la acción con código HTTP 403

### Requirement: Punto de entrada unificado y denegación por defecto
El punto de entrada `autorizar(usuario, accion, recurso, contexto)` MUST coordinar la evaluación de atributos (A2, RBAC, A1, A3, A4) devolviendo un objeto `Decision` inmutable con indicador booleano `permitido`, descripción del motivo y código HTTP sugerido. Si ninguna regla otorga permiso explícito para la combinación recibida, la decisión MUST ser denegada por defecto. El rol `administrativo` SHALL ser denegado para todas las acciones operativas en esta versión.

#### Scenario: Autorización exitosa devuelve decisión permitida
- **WHEN** se evalúa una acción cuyos atributos cumplen todas las políticas aplicables
- **THEN** el resultado es `Decision(permitido=True, motivo=None, codigo_http=None)`

#### Scenario: Denegación por defecto ante regla inexistente o rol no autorizado
- **WHEN** se evalúa una acción no contemplada en la matriz o un usuario con rol `administrativo`
- **THEN** el resultado es `Decision(permitido=False)` con código HTTP 403

#### Scenario: Registro seguro de rechazos sin fuga de datos personales
- **WHEN** una acción es denegada por cualquier política
- **THEN** el motivo registrado contiene identificador de usuario, rol, acción y regla violada, excluyendo DNI, nombres o datos sensibles del paciente

### Requirement: Acceso a fichas por vínculo vigente y agenda
paciente.ver y paciente.editar SHALL usar consultorio y vínculo leídos para la solicitud actual. Recepción/Administrador SHALL acceder a su consultorio; Profesional sólo SHALL leer pacientes de su agenda; Paciente sólo SHALL leer su ficha y editar contacto propio. Una ficha ajena por id SHALL responder 404 (RN-06, RN-50, RN-55, RN-63; KB 11).

#### Scenario: Personal y agenda autorizados
- **WHEN** el personal de Recepción/Administración consulta una ficha de su consultorio o un Profesional consulta un paciente de su agenda
- **THEN** autorizar permite la lectura y el Profesional no puede editar ni recibir datos de cuenta

#### Scenario: Ficha fuera de alcance
- **WHEN** el Profesional pide una ficha fuera de su agenda, el Paciente pide la de otra cuenta o el recurso es de otro consultorio
- **THEN** responde 404 sin revelar la ficha; los filtros se aplican también a búsquedas y sus totales

#### Scenario: Vínculo leído después de emitir el token
- **WHEN** una cuenta desvinculada usa un JWT emitido antes para leer o editar su antigua ficha
- **THEN** recibe 404 porque el vínculo ya no le corresponde, sin agregar paciente_id a los claims

### Requirement: Resoluciones de vínculo reservadas al personal
paciente.vincular, paciente.desvincular y paciente.reactivar SHALL permitirse sólo a Recepción y Administrador. Las solicitudes de vinculación SHALL tener ese mismo alcance de rol y consultorio. Estado incompatible al escribir SHALL ser 409 y no una ampliación de la política (RN-62, RN-63; KB 11).

#### Scenario: Actor sin permiso funcional
- **WHEN** Profesional, Paciente o Administrativo lista solicitudes o intenta vincular, rechazar, desvincular o reactivar
- **THEN** recibe 403 y no cambia ficha, solicitud, sesiones ni notificaciones

#### Scenario: Recurso ajeno y estado incompatible
- **WHEN** un actor permitido opera un recurso de otro consultorio o una transición incompatible con los datos actuales
- **THEN** el recurso ajeno responde 404 y el conflicto al escribir responde 409 con rollback; ninguna ruta autoriza ad hoc fuera del punto de entrada central
