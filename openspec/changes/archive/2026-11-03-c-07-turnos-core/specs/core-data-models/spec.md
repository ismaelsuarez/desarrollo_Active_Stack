# Spec Delta

## MODIFIED Requirements

### Requirement: Tokens de un solo uso desacoplados y sesiones rotativas
La tabla token_usuario MUST conservar hash único y turno_id nullable, ahora con clave foránea a turno. Los tokens de cuenta sin turno SHALL seguir siendo válidos; un identificador de turno inexistente MUST rechazarse. Refresh_token MUST conservar rotación, hash único, reemplazo y revocación.

#### Scenario: Creación de token de usuario con turno_id nulo
- **WHEN** se persiste un token_usuario de cuenta con turno_id nulo
- **THEN** se guarda sin exigir un turno

#### Scenario: Registro de refresh token para usuario
- **WHEN** se persiste un refresh_token con hash único y expiración
- **THEN** la sesión queda asociada al usuario correspondiente

#### Scenario: Referencia de turno inexistente
- **WHEN** se persiste un token_usuario con turno_id no nulo inexistente
- **THEN** PostgreSQL rechaza la escritura

### Requirement: Persistencia de notificaciones y reclamaciones
La persistencia SHALL admitir los diez tipos de KB 04, canales email/whatsapp y estados declarados, exigir marca si y solo si está enviando y conservar intentos y tiempos. turno_id SHALL seguir nullable y tendrá FK a turno. ciclo SHALL seguir diferido a C-15.

#### Scenario: Estado consistente
- **WHEN** una notificación pasa de programada a enviando con marca y luego a enviada sin marca
- **THEN** ambas escrituras conservan integridad e historial de intentos

#### Scenario: Estado inconsistente
- **WHEN** enviando no tiene marca o cualquier otro estado conserva marca
- **THEN** PostgreSQL rechaza la escritura

#### Scenario: Contratos futuros
- **WHEN** se registra un tipo válido con turno_id nulo o una fila WhatsApp preparada
- **THEN** el esquema los admite sin añadir el barrido ni ciclo de C-15

#### Scenario: Referencia válida o inexistente
- **WHEN** se guarda una notificación con turno_id no nulo
- **THEN** la FK exige que el turno exista; un identificador inexistente se rechaza

## ADDED Requirements

### Requirement: Turno conserva identidad y datos operativos
El turno SHALL conservar identificador e intervalo con zona, estado y pertenencia; SHALL guardar ciclo inicial 1, marca sin confirmar, datos de confirmación, cancelación, liberación, último inicio previo, origen y trazabilidad de nuevas operaciones según KB 04. Fechas operativas MUST venir del reloj inyectado y fin MUST ser posterior a inicio.

#### Scenario: Alta operativa
- **WHEN** se crea un turno por Recepción
- **THEN** conserva ficha, profesional, prestación, box y consultorio, ciclo 1, origen recepción y fechas de aplicación

#### Scenario: Intervalo o pertenencia inválidos
- **WHEN** se intenta persistir un turno con fin no posterior a inicio o referencias obligatorias inexistentes
- **THEN** PostgreSQL rechaza la escritura

### Requirement: Evolución conserva la exclusión y las filas existentes
La migración SHALL evolucionar el esquema existente sin recrear turno ni perder registros. MUST conservar la exclusión por consultorio/profesional sobre [inicio, fin), limitada a regulares en pendiente, confirmado, atendido y ausente. Los campos nuevos MUST NOT atribuir actores o hechos históricos desconocidos (DD-08, DD-14).

#### Scenario: Actualizar desde C-06
- **GIVEN** el esquema de C-06 y turnos sintéticos preexistentes
- **WHEN** se aplica la nueva revisión
- **THEN** conserva sus identificadores e intervalos, asigna ciclo inicial y mantiene una sola exclusión operativa

#### Scenario: Exclusión después de migrar
- **WHEN** se insertan directamente dos regulares activos solapados del mismo consultorio y profesional
- **THEN** la segunda escritura es rechazada y no se persiste

### Requirement: Historial pertenece al turno y solo agrega hechos
turno_historial SHALL conservar identificador, consultorio, turno, actor o sistema, acción, estados anterior/nuevo, detalle mínimo y fecha. SHALL impedir referencias a turnos inexistentes y no ofrecer modificación ni borrado de hechos registrados (RN-21; KB 04 §turno_historial).

#### Scenario: Historial de transición válida
- **WHEN** se registra una transición de un turno existente
- **THEN** se conserva el hecho con el consultorio, actor, estados y fecha correspondientes

#### Scenario: Historial sin turno
- **WHEN** se intenta persistir historial con turno_id inexistente
- **THEN** PostgreSQL rechaza la escritura

#### Scenario: Historial anterior permanece
- **WHEN** se registra una nueva transición
- **THEN** agrega un hecho sin modificar ni eliminar hechos anteriores
