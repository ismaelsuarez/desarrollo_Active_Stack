# Spec Delta: runtime-configuration

## MODIFIED Requirements

### Requirement: Arranque rechazado sin configuración obligatoria
La API MUST negarse a arrancar cuando falta `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY` o `CONSULTORIO_ACTIVO_ID`, con un error que nombra cada variable faltante o inválida y no muestra valores de variables sensibles. Ninguna de las cuatro variables tiene valor por defecto, y `CONSULTORIO_ACTIVO_ID` MUST ser un número entero mayor que 0.

#### Scenario: Falta DATABASE_URL
- **WHEN** la API arranca sin `DATABASE_URL` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `DATABASE_URL`

#### Scenario: Falta JWT_SECRET_KEY
- **WHEN** la API arranca con `DATABASE_URL` pero sin `JWT_SECRET_KEY` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `JWT_SECRET_KEY` y no contiene el valor de `DATABASE_URL`

#### Scenario: Falta APP_ENV
- **WHEN** la API arranca con `DATABASE_URL` y `JWT_SECRET_KEY` pero sin `APP_ENV`
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `APP_ENV`

#### Scenario: Falta CONSULTORIO_ACTIVO_ID
- **WHEN** la API arranca con `DATABASE_URL`, `JWT_SECRET_KEY` y `APP_ENV` pero sin `CONSULTORIO_ACTIVO_ID`
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `CONSULTORIO_ACTIVO_ID`

#### Scenario: CONSULTORIO_ACTIVO_ID inválido
- **WHEN** la API arranca con `CONSULTORIO_ACTIVO_ID` no numérico o menor o igual a cero
- **THEN** el arranque falla con error de validación sobre `CONSULTORIO_ACTIVO_ID`

#### Scenario: Configuración completa
- **WHEN** la API arranca con `APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY` y `CONSULTORIO_ACTIVO_ID` válidos
- **THEN** el arranque termina sin error
