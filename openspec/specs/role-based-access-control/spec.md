# role-based-access-control Specification

## Purpose
Define el modelo de identidad autenticada Principal, la resolución de consultorio en flujos anónimos y las fábricas de dependencias de autorización basadas en roles.

## Requirements

### Requirement: Construcción del Principal a partir del token JWT
La capa de aplicación MUST extraer y validar el token JWT desde el encabezado `Authorization: Bearer <token>`, verificando firma HS256, expiración y presencia de claims obligatorios (`sub`, `consultorio_id`, `rol`, `jti`), construyendo la entidad de dominio `Principal`. Si el token falta, está vencido o está alterado, la solicitud SHALL fallar con 401 Unauthorized.

#### Scenario: Token de acceso válido construye Principal
- **WHEN** se envía una solicitud protegida con un token JWT válido
- **THEN** la aplicación extrae el `Principal` con el identificador de usuario, consultorio y rol correctos

#### Scenario: Token expirado o alterado es rechazado
- **WHEN** se envía una solicitud con un token cuya fecha `exp` ha pasado o cuya firma es inválida
- **THEN** la respuesta es 401 Unauthorized

### Requirement: Autorización basada en roles con denegación por defecto
La API SHALL proveer la fábrica de dependencias `requiere_rol(*roles_permitidos)` que valide que el `Principal` autenticado posea uno de los roles autorizados para el endpoint. Toda ruta no explícitamente autorizada MUST denegar el acceso respondiendo 403 Forbidden.

#### Scenario: Usuario con rol permitido accede al recurso
- **GIVEN** un endpoint protegido con `requiere_rol("administrador", "recepcion")`
- **WHEN** un usuario con rol `"administrador"` invoca el endpoint
- **THEN** la solicitud es autorizada y continúa su ejecución

#### Scenario: Usuario con rol no autorizado es denegado
- **GIVEN** un endpoint protegido con `requiere_rol("administrador")`
- **WHEN** un usuario con rol `"profesional"` invoca el endpoint
- **THEN** la respuesta es 403 Forbidden

### Requirement: Resolución de consultorio sin token
Para las rutas que no reciben tokens de autenticación (`/auth/login`, etc.), el servidor MUST resolver el inquilino activo a partir de la variable obligatoria `CONSULTORIO_ACTIVO_ID` mediante la dependencia `consultorio_sin_token`. El cliente jamás debe proveer el `consultorio_id` en el cuerpo ni en parámetros de solicitud.

#### Scenario: Resolución de consultorio activo configurado
- **GIVEN** una solicitud a un endpoint sin autenticación como `POST /auth/login`
- **WHEN** el servidor procesa la solicitud
- **THEN** la dependencia `consultorio_sin_token` obtiene el consultorio configurado en `CONSULTORIO_ACTIVO_ID` y comprueba que esté activo

#### Scenario: Rechazo de consultorio inactivo o inexistente
- **GIVEN** un `CONSULTORIO_ACTIVO_ID` que no existe en la base o tiene `activo = false`
- **WHEN** se invoca una ruta pública que depende de `consultorio_sin_token`
- **THEN** la respuesta es 503 Service Unavailable o 404 Not Found impidiendo operar
