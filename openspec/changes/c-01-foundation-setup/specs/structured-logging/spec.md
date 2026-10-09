# Spec Delta

## Purpose

Garantiza registros de la API legibles por máquina, correlacionables por solicitud y libres de secretos o credenciales, en línea con la minimización de datos de la Ley 25.326.

## ADDED Requirements

### Requirement: Registros estructurados
Cada registro emitido por la API SHALL ser un objeto JSON en una sola línea con, al menos, las claves `timestamp` (ISO 8601 en UTC), `level`, `logger` y `message`.

#### Scenario: Registro de un evento
- **WHEN** la aplicación registra el mensaje `inicio` con nivel `INFO`
- **THEN** la salida es una línea JSON válida con `level` igual a `INFO`, `message` igual a `inicio` y un `timestamp` en UTC

### Requirement: Identificador de solicitud
La API SHALL asignar a cada solicitud HTTP un identificador, tomado del encabezado `X-Request-ID` cuando llega con un valor válido (hasta 128 caracteres de `[A-Za-z0-9._-]`) o generado en otro caso; lo devuelve en el encabezado `X-Request-ID` de la respuesta y lo incluye como `request_id` en todo registro emitido durante esa solicitud.

#### Scenario: Solicitud sin identificador
- **WHEN** un cliente envía `GET /api/v1/health` sin `X-Request-ID`
- **THEN** la respuesta incluye un encabezado `X-Request-ID` no vacío
- **AND** los registros de esa solicitud llevan ese mismo valor en `request_id`

#### Scenario: Solicitud con identificador válido
- **WHEN** un cliente envía `GET /api/v1/health` con `X-Request-ID: abc-123`
- **THEN** la respuesta devuelve `X-Request-ID: abc-123`

#### Scenario: Identificador inválido
- **WHEN** un cliente envía `X-Request-ID` con un valor de 300 caracteres o con espacios
- **THEN** la respuesta devuelve un identificador generado distinto del recibido

#### Scenario: Solicitudes distintas
- **WHEN** se envían dos solicitudes sin `X-Request-ID`
- **THEN** cada respuesta tiene un `X-Request-ID` distinto

### Requirement: Sin valores sensibles en los registros
Los registros MUST NOT contener el valor de ninguna variable sensible (`JWT_SECRET_KEY`, `SMTP_PASSWORD`, `SWEEP_SHARED_SECRET`, `BOOTSTRAP_ADMIN_PASSWORD`, `POSTGRES_PASSWORD`) ni la contraseña incluida en `DATABASE_URL`; cuando un mensaje los contiene, se reemplazan por `***`.

#### Scenario: Mensaje con un secreto
- **WHEN** la configuración tiene `JWT_SECRET_KEY=super-secreto` y la aplicación registra un mensaje que contiene `super-secreto`
- **THEN** la línea emitida no contiene `super-secreto`
- **AND** contiene `***` en su lugar

#### Scenario: URL de base con contraseña
- **WHEN** la aplicación registra la `DATABASE_URL` `postgresql+asyncpg://turnos:clave123@db:5432/turnos`
- **THEN** la línea emitida no contiene `clave123`

#### Scenario: Campos extra con secretos
- **WHEN** la aplicación registra un evento con un campo adicional cuyo valor es el de `SMTP_PASSWORD`
- **THEN** la línea emitida no contiene ese valor

#### Scenario: Error de arranque
- **WHEN** el arranque falla por configuración inválida
- **THEN** ninguna línea emitida contiene valores de variables sensibles
