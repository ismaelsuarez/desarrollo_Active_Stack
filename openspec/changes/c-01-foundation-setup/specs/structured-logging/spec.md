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
Los registros MUST reemplazar por `***` los valores secretos y las contraseñas de las URL de base que aparezcan en mensajes o campos adicionales. Los valores SHALL derivarse del tipo secreto del campo, no de una lista de nombres; agregar un campo secreto no requiere cambiar el registro. Se exceptúan los valores vacíos o menores de 4 caracteres para evitar reemplazos espurios.

#### Scenario: Mensaje con un secreto
- **GIVEN** la configuración obligatoria es válida y declara `JWT_SECRET_KEY`, `DATABASE_URL` y `MIGRATIONS_DATABASE_URL` como campos secretos
- **WHEN** la configuración tiene `JWT_SECRET_KEY=jwt-secreto-de-prueba-0123456789-abcd` y la aplicación registra un mensaje que contiene `jwt-secreto-de-prueba-0123456789-abcd`
- **THEN** la línea emitida no contiene `jwt-secreto-de-prueba-0123456789-abcd`
- **AND** contiene `***` en su lugar

#### Scenario: URL de base con contraseña
- **WHEN** la aplicación registra la `DATABASE_URL` `postgresql+asyncpg://turnos:clave123@db:5432/turnos`
- **THEN** la línea emitida no contiene `clave123`

#### Scenario: Campos extra con secretos
- **WHEN** la aplicación registra un evento con un campo adicional cuyo valor es el de `JWT_SECRET_KEY`
- **THEN** la línea emitida no contiene ese valor

#### Scenario: Campo secreto agregado después
- **WHEN** una configuración de prueba que extiende la de la API con un campo secreto nuevo (por ejemplo `SMTP_PASSWORD`, `SWEEP_SHARED_SECRET`, `ORIGIN_HASH_SECRET` o `BOOTSTRAP_ADMIN_PASSWORD`) tiene ese campo en `valor-nuevo` y la aplicación registra un mensaje que contiene `valor-nuevo`
- **THEN** la línea emitida no contiene `valor-nuevo`
- **AND** el código del registro no se modificó para conocer ese campo

#### Scenario: Valor secreto vacío o muy corto
- **WHEN** una configuración válida con una clave JWT de al menos 32 bytes tiene campos secretos adicionales de prueba, uno vacío y otro con el valor `abc`, y la aplicación registra el mensaje `inicio abc`
- **THEN** la línea emitida conserva el mensaje `inicio abc` sin `***` insertado en ninguna posición

#### Scenario: Error de arranque
- **WHEN** el arranque falla por configuración inválida
- **THEN** no existe una instancia de configuración que consultar, así que el error se informa con la opción `hide_input_in_errors=True` de pydantic y su mensaje lista solo nombres de campo
- **AND** ninguna línea emitida contiene valores de variables sensibles
