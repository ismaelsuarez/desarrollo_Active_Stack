# Spec Delta

## MODIFIED Requirements

### Requirement: Tokens de un solo uso desacoplados y sesiones rotativas
token_usuario MUST conservar hash único y turno_id nullable con FK a turno. Los tokens de cuenta sin turno SHALL seguir válidos y exigir usuario. confirmar_turno SHALL exigir turno y ciclo positivo y permitir usuario nulo para fichas sin cuenta; otros tipos MUST NOT admitir usuario nulo. Una referencia a turno inexistente MUST rechazarse. Refresh_token MUST conservar rotación, hash único, reemplazo y revocación.

#### Scenario: Creación de token de usuario con turno_id nulo
- **WHEN** se persiste un token_usuario de cuenta con turno_id nulo
- **THEN** se guarda sin exigir un turno

#### Scenario: Registro de refresh token para usuario
- **WHEN** se persiste un refresh_token con hash único y expiración
- **THEN** la sesión queda asociada al usuario correspondiente

#### Scenario: Referencia de turno inexistente
- **WHEN** se persiste un token_usuario con turno_id no nulo inexistente
- **THEN** la base rechaza la referencia por clave foránea

#### Scenario: Confirmación de ficha sin cuenta
- **WHEN** se persiste confirmar_turno con turno existente, ciclo positivo, hash único y usuario nulo
- **THEN** se conserva el token sin crear ni asignar una cuenta artificial

#### Scenario: Restricciones según propósito
- **WHEN** se intenta guardar confirmar_turno sin turno o ciclo positivo, o verificar_email/recuperar_password con usuario nulo
- **THEN** PostgreSQL rechaza la fila por restricción sin debilitar los contratos de cuenta
