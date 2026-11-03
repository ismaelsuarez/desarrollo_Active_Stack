## ADDED Requirements

### Requirement: Solicitudes de vinculación de cuenta
La persistencia SHALL guardar solicitudes con consultorio, cuenta única, DNI declarado normalizado, estado pendiente/vinculada/rechazada, ficha y resolución opcionales, fecha de creación y motivo. SHALL preservar la unicidad de ficha por DNI y consultorio (RN-49, RN-62).

#### Scenario: Solicitud pendiente
- **WHEN** se registra una cuenta con DNI existente
- **THEN** persiste una solicitud pendiente sin ficha vinculada y con la fecha del reloj inyectado

#### Scenario: Integridad de la solicitud
- **WHEN** se intenta duplicar solicitud por cuenta o guardar estado no permitido
- **THEN** la base rechaza la escritura

### Requirement: Persistencia de notificaciones y reclamaciones
La persistencia SHALL admitir los diez tipos de KB 04, canales email/whatsapp y sus estados declarados. SHALL exigir marca de reclamación si y solo si está enviando, y guardar intentos y tiempos. turno_id SHALL ser nullable sin nueva FK y ciclo SHALL diferirse a C-15.

#### Scenario: Estado consistente
- **WHEN** se pasa de programada a enviando con marca y luego a enviada sin marca
- **THEN** ambas escrituras cumplen la integridad y preservan el historial de intentos

#### Scenario: Estado inconsistente
- **WHEN** enviando no tiene marca o cualquier otro estado conserva marca
- **THEN** PostgreSQL rechaza la escritura

#### Scenario: Contratos futuros
- **WHEN** se programa un tipo de turno válido con turno_id nullable o una fila de WhatsApp preparada
- **THEN** el esquema admite esos tipos sin incorporar el barrido ni el ciclo de C-15

### Requirement: Intentos de registro sin direcciones
La persistencia SHALL almacenar consultorio, HMAC de origen nullable y fecha inyectada para intentos de registro, con índices por consultorio/origen/fecha y fecha para retención, sin dirección IP en claro (DD-21).

#### Scenario: Origen conocido
- **WHEN** se admite una solicitud de origen determinable
- **THEN** guarda únicamente su HMAC y confirma antes del registro

#### Scenario: Origen desconocido
- **WHEN** se admite una solicitud sin origen
- **THEN** guarda origen nulo y permite contarla para el límite global
