# Delta

## Purpose

Permitir al personal consultar la agenda y gestionar turnos de forma clara y acorde a las autorizaciones del servidor.

## ADDED Requirements

### Requirement: Agenda diaria por rol
La interfaz SHALL mostrar fecha, profesional, turnos ordenados, estado y marca de sobreturno en la zona del consultorio. El Profesional SHALL acceder únicamente a su agenda; Recepción y Administrador SHALL poder elegir profesional y el Administrador con agenda propia SHALL poder seleccionar la suya.

#### Scenario: Agenda propia y ajena
- **WHEN** un Profesional abre la agenda o intenta acceder a otra
- **THEN** ve solo la propia y la API impide el acceso ajeno.

#### Scenario: Día vacío y error
- **WHEN** no hay turnos o falla la consulta
- **THEN** se muestra un estado vacío o error recuperable, sin confundir ambos.

### Requirement: Acciones de turno según servidor
La interfaz SHALL presentar crear, mover, cancelar, confirmar, marcar atendido y ausente solo a los roles habilitados y conforme a las acciones operativas devueltas. SHALL actualizar la lectura tras cada resultado confirmado y respetar rechazos del servidor.

#### Scenario: Profesional y estado final
- **WHEN** un Profesional consulta su agenda o cualquier actor consulta un turno sin acción permitida
- **THEN** no se ofrece crear al Profesional ni se presentan acciones no permitidas para el turno.

#### Scenario: Conflicto al reservar o mover
- **WHEN** la API informa horario ocupado
- **THEN** se conserva la selección y se muestra el conflicto, con disponibilidad orientativa si la consulta independiente devuelve opciones; no se presenta como garantía ni como dato devuelto en el 409.

#### Scenario: Alta de ficha durante reserva
- **WHEN** Recepción crea una ficha válida desde el flujo y después confirma el turno
- **THEN** usa la ficha creada y solo registra el turno tras la confirmación explícita; si falla el turno, informa que la ficha ya existe.

### Requirement: Sobreturno explícito y respuesta
La interfaz SHALL exigir motivo y autorización explícita para otorgar un sobreturno y mostrar su aviso y respuesta. Solo el profesional afectado o administrador con agenda propia SHALL poder responder; una respuesta negativa no cancela el turno.

#### Scenario: Falta autorización
- **WHEN** Recepción intenta enviar sin motivo o sin autorización
- **THEN** se explica el campo requerido y no se envía la operación.

#### Scenario: Respuesta negativa
- **WHEN** el profesional rechaza el aviso
- **THEN** se muestra la respuesta y se indica que el sobreturno sigue vigente.

### Requirement: Lecturas seguras y errores de escritura
La interfaz SHALL identificar carga, error, ausencia de permisos y resultado incierto; MUST NOT repetir automáticamente escrituras inciertas. SHALL ignorar respuestas obsoletas al cambiar fecha, profesional o sesión.

#### Scenario: Escritura sin respuesta
- **WHEN** una escritura pierde respuesta
- **THEN** informa que debe consultarse el estado antes de reintentar, sin duplicar el envío.
