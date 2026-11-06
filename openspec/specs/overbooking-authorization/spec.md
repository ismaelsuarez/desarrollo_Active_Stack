# overbooking-authorization Specification

## Purpose

Permitir al personal otorgar sobreturnos justificados y registrar la respuesta del profesional afectado de forma trazable y aislada por consultorio.

## Requirements

### Requirement: Otorgamiento explícito y atómico
POST /api/v1/sobreturnos SHALL permitir solo a Recepción y Administrador crear un sobreturno con autorización explícita y motivo no vacío. El servidor SHALL registrar turno, historial, autorización y aviso en una transacción, con consultorio y autorizante derivados del principal (RN-39–41, DD-30).

#### Scenario: Otorgamiento sobre turno activo
- **WHEN** Recepción autoriza con motivo un intervalo válido que se superpone a un turno activo del mismo profesional
- **THEN** responde 201 con el turno marcado como sobreturno y persiste su autorización, fecha, actor, aviso e historial.

#### Scenario: Autorización ausente o motivo vacío
- **WHEN** falta la autorización explícita o el motivo está vacío
- **THEN** responde 422 y no crea turno, autorización, historial ni avisos asociados.

#### Scenario: Reversión de escritura
- **WHEN** falla la inserción de autorización, historial o aviso transaccional
- **THEN** se revierte toda la operación y no queda sobreturno huérfano.

#### Scenario: Roles no autorizados
- **WHEN** Paciente, Profesional o Administrativo intenta otorgar un sobreturno
- **THEN** recibe 403 y no se registra ningún cambio.

### Requirement: Intervalo realmente solapado y válido
El sobreturno SHALL superponerse a al menos un turno activo del mismo profesional y consultorio, respetar horario, grilla y bloqueos y usar duración válida. Un intervalo libre o inválido SHALL responder 422; un intervalo contiguo no constituye solapamiento (RN-17, RN-43, RN-64).

#### Scenario: Horario libre o contiguo
- **WHEN** el intervalo no intersecta ningún turno activo del profesional o solo toca su extremo
- **THEN** responde 422 e indica crear un turno normal sin guardar cambios.

#### Scenario: Fuera de agenda o bloqueado
- **WHEN** el intervalo queda fuera del horario semanal o intersecta un bloqueo global o propio
- **THEN** responde 422 sin crear sobreturno ni autorización.

#### Scenario: Solo turnos finales no ocupantes
- **WHEN** el intervalo coincide solo con turnos cancelados o liberados
- **THEN** no se considera solapamiento suficiente y la solicitud responde 422.

### Requirement: Respuesta sin veto del profesional
POST /api/v1/sobreturnos/{id}/respuesta-profesional SHALL registrar aprobado o rechazado, fecha y comentario opcional para el turno identificado. Solo SHALL permitir responder al profesional afectado o administrador vinculado a esa agenda; la respuesta MUST NOT cambiar el estado ni cancelar el turno (RN-40, DD-24, DD-30).

#### Scenario: Rechazo del profesional afectado
- **WHEN** el profesional titular rechaza el aviso de su sobreturno
- **THEN** se registra rechazo y fecha y el turno conserva su estado y vigencia.

#### Scenario: Administrador con agenda propia
- **WHEN** un administrador responde un aviso de su agenda propia o de la de otro profesional
- **THEN** se acepta solo el primero; sin agenda propia también se deniega la respuesta.

#### Scenario: Profesional ajeno o recurso de otro consultorio
- **WHEN** un profesional intenta responder un aviso ajeno o cualquier usuario accede a uno de otro consultorio
- **THEN** se deniega conforme a las políticas de aislamiento sin modificar datos ni revelar un recurso de otro consultorio.

### Requirement: Aviso visible y respuesta operativa
Las lecturas autorizadas de agenda y turno SHALL identificar el sobreturno y presentar al personal autorizado el aviso y la respuesta registrada. MUST NOT ampliar la respuesta de paciente con motivo o comentario interno ni exponer datos de otros consultorios (RN-40–42, RN-54, RN-55).

#### Scenario: Profesional y recepción consultan
- **WHEN** se crea un sobreturno y luego el profesional lo rechaza
- **THEN** el aviso aparece en la agenda afectada y Recepción puede ver la respuesta junto al turno marcado.

#### Scenario: Lectura de paciente
- **WHEN** un paciente consulta su propio sobreturno
- **THEN** no recibe motivo, comentario profesional ni información interna de autorización.

### Requirement: Convivencia con exclusión y ciclo de turno
El sobreturno SHALL quedar fuera de la restricción de exclusión de turnos regulares, conservando la protección de solapamiento de turnos normales y las integraciones de historial y notificaciones vigentes. Las verificaciones de base de datos SHALL usar PostgreSQL real (RN-17, RN-29, DD-14).

#### Scenario: Excepción controlada
- **WHEN** se inserta un sobreturno autorizado sobre un turno regular activo
- **THEN** PostgreSQL permite la excepción y conserva la prohibición de dos turnos regulares superpuestos.

#### Scenario: Ciclo y fallos
- **WHEN** se crea el sobreturno o falla la planificación transaccional de sus hitos y avisos de turno
- **THEN** se aplican las reglas vigentes del ciclo o se revierte el conjunto, sin duplicar avisos.
