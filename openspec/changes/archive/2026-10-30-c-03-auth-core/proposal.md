# Proposal: c-03-auth-core

## Why

El sistema cuenta con la estructura relacional base y el consultorio inicial aprovisionado (C-02), pero carece de mecanismos de autenticación y autorización. Es indispensable proveer acceso seguro para los distintos actores del consultorio (administrador, recepción, profesional, administrativo y paciente), emitiendo tokens de acceso JWT (PyJWT HS256), protegiendo sesiones renovables con rotación estricta de refresh tokens en cookies seguras, e implementando control de acceso basado en roles (RBAC) y defensas contra ataques de fuerza bruta y análisis de tiempos.

## What Changes

- **Autenticación y ciclo de sesión (`/api/v1/auth`)**:
  - `POST /api/v1/auth/login`: Validación de credenciales con Argon2 (`pwdlib`) y verificación ficticia para mitigar ataques de temporización si el usuario no existe. Emisión de JWT HS256 con claims `sub`, `consultorio_id`, `rol`, `jti`, `iat`, `exp` (nunca el identificador de paciente) y emisión de `refresh_token` en cookie `HttpOnly`, `SameSite=Strict` y `Secure`.
  - `POST /api/v1/auth/refresh`: Rotación atómica de refresh token (`reemplazado_por_id`). Si se detecta reutilización de un token revocado, se invalida toda la cadena de sesiones de la cuenta.
  - `POST /api/v1/auth/logout`: Revocación del refresh token activo y limpieza de la cookie de sesión.
  - `GET /api/v1/auth/me`: Retorna los datos del usuario autenticado a partir del `Principal`.
  - Rechazo de ingreso a cuentas de rol `paciente` cuyo correo no haya sido verificado (`email_verificado = false`, RN-02).
- **Control de acceso basado en roles (RBAC)**:
  - Modelo de dominio `Principal` conteniendo `usuario_id`, `consultorio_id` y `rol`.
  - Dependencias FastAPI `usuario_actual` y fábricas `requiere_rol(*roles)` con denegación por defecto (401 ante token ausente/inválido/expirado, 403 ante rol insuficiente).
- **Protección contra abuso y fuerza bruta**:
  - Migración Alembic `0003_auth_core.py` para la tabla `intento_ingreso` (`consultorio_id`, `identificador_hash`, `origen_hash`, `creado_en`).
  - Bloqueo temporal por par (cuenta, origen) tras 5 intentos fallidos (`LOGIN_MAX_ATTEMPTS=5`) en una ventana de 15 minutos (`LOGIN_LOCKOUT_MINUTES=15`), respondiendo 401 genérico idéntico sin evaluar contraseña.
  - Límite global por origen tras 20 intentos fallidos (`LOGIN_MAX_ATTEMPTS_PER_ORIGIN=20`).
  - Resolución segura de dirección de origen respetando `TRUSTED_PROXY_HOPS`.
  - Purga oportunista al escribir de intentos con más de 24 horas de antigüedad.
- **Configuración y secretos**:
  - Incorporación en `Settings` de `ORIGIN_HASH_SECRET` (obligatoria, sensible, mín 32 bytes) y `TRUSTED_PROXY_HOPS` (entero >= 0).
  - Actualización de `scripts/dev_secrets.sh`, `.env.example`, `docker-compose.yml` y `.github/workflows/ci.yml`.

## Capabilities

### New Capabilities
- `user-authentication`: Manejo de endpoints de login, logout, refresh con rotación atómica y consulta de identidad actual (`/auth/me`), validando contraseñas con Argon2 y mitigando ataques de temporización.
- `role-based-access-control`: Construcción del `Principal` desde tokens JWT validados y fábricas de dependencias de autorización con denegación por defecto.
- `login-rate-limiting`: Registro y conteo de intentos fallidos con hashes HMAC-SHA256, bloqueo temporal de cuenta y límite por origen respetando saltos de proxy confiables.

### Modified Capabilities
- `runtime-configuration`: Incorporación de `ORIGIN_HASH_SECRET` como variable obligatoria sensible y `TRUSTED_PROXY_HOPS` en la configuración de la API.

## Impact

- **Seguridad**: Autenticación estricta con Argon2 y JWT HS256 sin filtrar datos personales en claims ni respuestas de error.
- **Infraestructura y Base de Datos**: Nueva tabla `intento_ingreso` con índices especializados en migración `0003_auth_core.py`.
- **API REST**: Nuevos routers en `backend/app/api/v1/routers/auth.py` y dependencias de seguridad en `backend/app/api/deps.py`.
- **Configuración**: Secreto `secrets/origin_hash_secret.txt` montado en Compose y validado en CI.
