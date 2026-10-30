# Spec Delta: login-rate-limiting

## Purpose

Define el registro atómico previo de intentos de ingreso con hashes HMAC, el bloqueo temporal por par cuenta-origen, la limitación de tasa por IP de origen, la limpieza ante login exitoso y la purga automática de intentos caducados.

## ADDED Requirements

### Requirement: Registro previo y conteo de intentos de ingreso
La tabla `intento_ingreso` MUST persistir cada intento de login registrando `consultorio_id`, `identificador_hash`, `origen_hash` (o `NULL`) y `creado_en`. Cada inserción SHALL confirmarse en su propia transacción corta antes de evaluar el conteo de bloqueos y antes de validar la contraseña (RN-09, DD-25).

#### Scenario: Inserción previa de intento confirmada
- **WHEN** se recibe una solicitud de login en `POST /api/v1/auth/login`
- **THEN** se persiste un registro en `intento_ingreso` con los hashes correspondientes sin almacenar en claro el usuario ni la IP antes de comprobar credenciales
- **AND** el registro queda confirmado en la base de datos

### Requirement: Bloqueo temporal por par cuenta y origen
Si el conteo de intentos para un mismo par `(identificador_hash, origen_hash)` supera `LOGIN_MAX_ATTEMPTS` (5 por defecto) dentro de la ventana de `LOGIN_LOCKOUT_MINUTES` (15 minutos por defecto) utilizando semántica segura de nulidad (`IS NOT DISTINCT FROM`), el sistema MUST responder 401 Unauthorized sin verificar la contraseña.

#### Scenario: Bloqueo en el sexto intento
- **GIVEN** 5 intentos previos registrados para el mismo usuario y dirección de origen en los últimos 15 minutos
- **WHEN** se realiza un sexto intento de ingreso
- **THEN** la respuesta es 401 Unauthorized de forma inmediata sin procesar la contraseña
- **AND** el sexto intento queda registrado prolongando la ventana de bloqueo

#### Scenario: Acceso desde otro origen no es bloqueado
- **GIVEN** una cuenta con intentos bloqueados desde un origen determinado
- **WHEN** el usuario legítimo intenta ingresar con credenciales correctas desde una dirección de origen distinta
- **THEN** el ingreso es exitoso y se emite la sesión

#### Scenario: Éxito limpia los intentos del par
- **GIVEN** intentos previos acumulados para un par `(identificador_hash, origen_hash)`
- **WHEN** se produce un ingreso exitoso para ese mismo par
- **THEN** se eliminan los registros de intentos acumulados para ese par

### Requirement: Límite global por origen y saltos de proxy confiables
El sistema MUST limitar los intentos provenientes de un mismo origen a un máximo de `LOGIN_MAX_ATTEMPTS_PER_ORIGIN` (20 por defecto) en la ventana configurada. La dirección de origen MUST ser extraída del encabezado `X-Forwarded-For` confiando exclusivamente en el número de saltos definido en `TRUSTED_PROXY_HOPS` (0 por defecto, DD-21). Si `TRUSTED_PROXY_HOPS = 0`, se utiliza el host directo de la conexión.

#### Scenario: Bloqueo por exceso de intentos desde un mismo origen
- **GIVEN** 20 intentos registrados desde una misma dirección IP hacia distintas cuentas en los últimos 15 minutos
- **WHEN** se recibe un intento número 21 desde esa misma IP
- **THEN** la solicitud es rechazada con 401 Unauthorized sin verificar la contraseña

#### Scenario: Saltos de proxy no confiables son ignorados
- **GIVEN** `TRUSTED_PROXY_HOPS = 0`
- **WHEN** un cliente envía un encabezado `X-Forwarded-For: 203.0.113.195` falsificado
- **THEN** el sistema utiliza la dirección directa de la conexión descartando la cabecera falsificada

### Requirement: Purga oportunista de registros expirados
En cada inserción de un nuevo intento en `intento_ingreso`, el sistema SHALL ejecutar una purga eliminando todos los registros cuyo `creado_en` tenga una antigüedad superior a 24 horas respecto a la marca temporal provista por el puerto `Reloj`.

#### Scenario: Eliminación de intentos con más de 24 horas
- **GIVEN** registros antiguos en `intento_ingreso` con más de 24 horas de antigüedad
- **WHEN** se registra un nuevo intento de ingreso
- **THEN** los registros antiguos son eliminados de la tabla
