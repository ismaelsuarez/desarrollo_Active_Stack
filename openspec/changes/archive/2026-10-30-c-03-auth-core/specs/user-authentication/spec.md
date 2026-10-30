# Spec Delta: user-authentication

## Purpose

Define los contratos de autenticación mediante credenciales, emisión y renovación de tokens JWT gobernados por el puerto `Reloj`, mitigación de ataques de temporización con alta entropía, prevención de enumeración de pacientes y consulta de identidad del usuario actual.

## ADDED Requirements

### Requirement: Autenticación con credenciales y emisión de tokens
El endpoint `POST /api/v1/auth/login` MUST validar credenciales contra la tabla `usuario` utilizando Argon2. Si son válidas, SHALL emitir un token JWT (HS256) con claims mínimos gobernados por el puerto `Reloj`, y fijar un `refresh_token` en una cookie con directivas `HttpOnly`, `SameSite=Strict`, `Path=/api/v1/auth` y `Secure`.

#### Scenario: Inicio de sesión exitoso con nombre de usuario
- **GIVEN** un usuario registrado y activo con nombre de usuario `"admin"` y contraseña válida
- **WHEN** envía `POST /api/v1/auth/login` con `identificador="admin"` y la contraseña correcta
- **THEN** la respuesta es 200 con el token de acceso JWT en el cuerpo
- **AND** la respuesta incluye la cookie `refresh_token` con directivas seguras

#### Scenario: Inicio de sesión exitoso con email normalizado
- **GIVEN** un usuario registrado con email `"admin@consultorio.com"`
- **WHEN** envía `POST /api/v1/auth/login` con `identificador=" ADMIN@CONSULTORIO.COM "` y contraseña correcta
- **THEN** la respuesta es 200 con el token de acceso JWT

#### Scenario: Rechazo por contraseña incorrecta
- **GIVEN** un usuario existente
- **WHEN** envía `POST /api/v1/auth/login` con una contraseña errónea
- **THEN** la respuesta es 401 con el mensaje genérico `"Credenciales inválidas"`

### Requirement: Mitigación de ataques de temporización en login
Cuando un intento de ingreso utiliza un identificador que no corresponde a ningún usuario existente en el consultorio o a un usuario inactivo, el sistema MUST computar la verificación contra un hash Argon2 ficticio (`DUMMY_HASH`) generado al inicio con entropía criptográfica (`secrets.token_hex(32)`) para igualar el tiempo de cómputo del intento fallido, respondiendo exactamente el mismo mensaje y código de error 401 genérico de forma incondicional.

#### Scenario: Usuario inexistente responde igual que contraseña incorrecta
- **WHEN** se envía `POST /api/v1/auth/login` con un usuario que no existe
- **THEN** el tiempo de respuesta es indistinguible de una verificación real de contraseña
- **AND** la respuesta es 401 con el mensaje `"Credenciales inválidas"`

### Requirement: Prevención de enumeración y verificación de cuenta de pacientes
Para las cuentas con rol `paciente`, el sistema MUST verificar la validez de la contraseña ANTES de verificar el estado de confirmación de correo. Si la contraseña es errónea, SHALL responder 401 genérico. Si la contraseña es correcta pero `email_verificado = false`, SHALL rechazar el acceso con 403 Forbidden indicando que el correo electrónico requiere verificación (RN-02).

#### Scenario: Rechazo de paciente con correo sin verificar tras contraseña correcta
- **GIVEN** un usuario con rol `paciente` y `email_verificado = false`
- **WHEN** envía `POST /api/v1/auth/login` con su contraseña correcta
- **THEN** la respuesta es 403 Forbidden indicando que el correo requiere verificación

#### Scenario: Paciente sin verificar con contraseña errónea no revela existencia
- **GIVEN** un usuario con rol `paciente` y `email_verificado = false`
- **WHEN** envía `POST /api/v1/auth/login` con una contraseña incorrecta
- **THEN** la respuesta es 401 Unauthorized genérica ("Credenciales inválidas")

### Requirement: Renovación de sesión con rotación de refresh tokens
El endpoint `POST /api/v1/auth/refresh` MUST extraer el `refresh_token` de la cookie, resolver el `consultorio_id` desde la fila en BD (RN-59) y rotar atómicamente el token validando expiración con el puerto `Reloj`. Si el token ya fue revocado o reemplazado, SHALL revocar todas las sesiones del usuario por reuso.

#### Scenario: Renovación exitosa con rotación
- **GIVEN** un `refresh_token` válido y activo enviado en la cookie
- **WHEN** se envía `POST /api/v1/auth/refresh`
- **THEN** la respuesta es 200 con un nuevo token de acceso JWT
- **AND** se emite una nueva cookie con un nuevo `refresh_token`
- **AND** el `refresh_token` anterior queda marcado como reemplazado

#### Scenario: Detección de reuso de token revocado o reemplazado
- **GIVEN** un `refresh_token` que ya había sido utilizado y reemplazado
- **WHEN** se intenta reutilizar en `POST /api/v1/auth/refresh`
- **THEN** la respuesta es 401 Unauthorized
- **AND** todos los `refresh_token` vigentes del usuario quedan revocados

### Requirement: Revocación de sesión en cierre de sesión
El endpoint `POST /api/v1/auth/logout` MUST revocar el `refresh_token` provisto en la cookie marcando su fecha de revocación contra el puerto `Reloj`, tolerando que el token de acceso de cabecera haya expirado, y limpiar la cookie de sesión del cliente con directiva de expiración inmediata.

#### Scenario: Cierre de sesión exitoso
- **GIVEN** una sesión activa con cookie `refresh_token`
- **WHEN** se envía `POST /api/v1/auth/logout`
- **THEN** la respuesta es 200 con mensaje de confirmación
- **AND** el `refresh_token` en la base queda marcado como revocado
- **AND** la cookie `refresh_token` es eliminada en la respuesta

### Requirement: Consulta de perfil actual
El endpoint `GET /api/v1/auth/me` MUST retornar los datos no sensibles del usuario autenticado (`id`, `nombre_usuario`, `email`, `rol`, `consultorio_id`, `email_verificado`) a partir del `Principal` extraído del token de acceso, verificando en la base de datos que el usuario continúe activo (`activo = true`), sin exponer datos personales no indispensables ni claves foráneas de pacientes.

#### Scenario: Lectura de perfil autenticado
- **GIVEN** una solicitud con encabezado `Authorization: Bearer <token_valido>`
- **WHEN** se consulta `GET /api/v1/auth/me`
- **THEN** la respuesta es 200 con la información del usuario autenticado
