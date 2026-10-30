# Tasks: c-03-auth-core

## 1. Configuración, dependencias y secretos

- [x] 1.1 Incorporar `pyjwt>=2.9.0` a `backend/pyproject.toml` y sincronizar el entorno con `uv sync`, verificando la disponibilidad del paquete y la ausencia de dependencias no autorizadas.
- [x] 1.2 Extender `Settings` en `backend/app/core/config.py` incorporando `ORIGIN_HASH_SECRET` (obligatorio, sensible, mín 32 bytes), `TRUSTED_PROXY_HOPS` (entero >= 0), parámetros de rate limiting (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`, `LOGIN_MAX_ATTEMPTS_PER_ORIGIN`) y `cookie_secure` (por defecto `app_env != 'development'`), agregando pruebas unitarias en `backend/tests/unit/test_config.py` y verificando con `uv run pytest backend/tests/unit/test_config.py`.
- [x] 1.3 Actualizar `scripts/dev_secrets.sh`, `.env.example`, `docker-compose.yml` y `.github/workflows/ci.yml` para aprovisionar `ORIGIN_HASH_SECRET` y variables de red, verificando la generación del secreto y la consistencia de variables de entorno.

## 2. Modelo de datos y migración de intentos de ingreso

- [x] 2.1 Definir el modelo SQLAlchemy `IntentoIngresoModel` en `backend/app/infrastructure/db/models.py` con columnas `id`, `consultorio_id`, `identificador_hash`, `origen_hash` (nullable), `creado_en` e índices especializados (`ix_intento_ingreso_par`, `ix_intento_ingreso_origen`, `ix_intento_ingreso_creado_en`).
- [x] 2.2 Crear la migración Alembic `0003_auth_core.py` en `backend/migrations/versions/` aplicando `uv run alembic upgrade head`, y verificar en pruebas de integración con PostgreSQL real la creación y reversión limpia (`alembic downgrade -1 && alembic upgrade head`) sin dejar múltiples heads.

## 3. Dominio, puertos y utilidades criptográficas

- [x] 3.1 Implementar la entidad de dominio inmutable `Principal` y tipos de roles en `backend/app/domain/entities/auth.py`, agregando pruebas unitarias de inmutabilidad y validación de tipos.
- [x] 3.2 Implementar utilidades criptográficas y de red en `backend/app/domain/services/auth_crypto.py`: cálculo de hashes HMAC-SHA256 (`identificador_hash`, `origen_hash`), resolución segura de IP de origen respetando `TRUSTED_PROXY_HOPS` con soporte de host de prueba (`testclient`), hash SHA-256 para refresh tokens, y verificación constante con Argon2 (`pwdlib`) y `DUMMY_HASH` generado con alta entropía (`secrets.token_hex(32)`), verificando con pruebas unitarias en `backend/tests/unit/test_auth_crypto.py`.

## 4. Servicios de aplicación y persistencia de autenticación

- [x] 4.1 Implementar `AuthTokenService` en `backend/app/application/services/token_service.py` inyectando el puerto `Reloj` (Regla Dura 4) para la emisión y decodificación de tokens JWT HS256 con claims mínimos (`sub`, `consultorio_id`, `rol`, `jti`, `iat`, `exp`), verificando firma, expiración gobernada por el reloj inyectado y rechazo de tokens inválidos con pruebas unitarias en `backend/tests/unit/test_token_service.py`.
- [x] 4.2 Implementar `LoginRateLimiter` en `backend/app/application/services/rate_limiter.py` gestionando la inserción y confirmación atómica previa en cada intento (RN-09), el conteo de bloqueos por par con semántica segura de nulidad `IS NOT DISTINCT FROM` (5 intentos / 15 min), el conteo por origen (20 intentos / 15 min), la limpieza ante login exitoso y la purga oportunista de registros con más de 24 horas, verificando con pruebas de integración contra PostgreSQL real en `backend/tests/integration/test_rate_limiter.py`.
- [x] 4.3 Implementar `AuthService` en `backend/app/application/services/auth_service.py` orquestando autenticación con Argon2 y mitigación dummy, verificación de `email_verificado` para rol `paciente` estrictamente después de validar la contraseña (RN-02), rotación atómica de refresh tokens resolviendo el consultorio a partir de la fila del token (RN-59, Regla Dura 1), detección de reuso de tokens revocados con invalidación en cascada, y revocación en logout, verificando con pruebas en `backend/tests/integration/test_auth_service.py`.

## 5. Dependencias FastAPI y endpoints REST de autenticación

- [x] 5.1 Implementar dependencias de seguridad en `backend/app/api/deps.py`: `usuario_actual` (extracción y validación de JWT a `Principal` con el puerto `Reloj`), `requiere_rol(*roles)` (fábrica RBAC con denegación por defecto 403) y `consultorio_sin_token` (resolución segura de `CONSULTORIO_ACTIVO_ID` para `/login`), verificando con pruebas unitarias en `backend/tests/unit/test_auth_deps.py`.
- [x] 5.2 Implementar esquemas Pydantic estrictos (`extra='forbid'`, Regla Dura 11) para solicitudes y respuestas de autenticación en `backend/app/api/v1/schemas/auth.py`, asegurando que no se expongan datos personales de pacientes ni identificadores internos sensibles.
- [x] 5.3 Implementar el router de autenticación en `backend/app/api/v1/routers/auth.py` con los endpoints `POST /login`, `POST /refresh`, `POST /logout` y `GET /me`, gestionando cookies de sesión seguras (`HttpOnly`, `SameSite=Strict`, `Path=/api/v1/auth`, `Secure`), montándolo en `backend/app/main.py`, y verificando todos los flujos mediante pruebas de integración API en `backend/tests/integration/test_auth_endpoints.py`.

## 6. Verificación integral de comportamiento y smoke test

- [x] 6.1 Ejecutar la suite completa de pruebas unitarias e integración con `uv run pytest`, verificando que todos los escenarios de las cuatro especificaciones delta (`user-authentication`, `role-based-access-control`, `login-rate-limiting`, `runtime-configuration`) pasen exitosamente.
- [x] 6.2 Ejecutar `scripts/smoke_compose.sh` verificando el ciclo completo de Compose (db -> migrate -> seed -> api) con las nuevas variables y secretos de autenticación.

## Workflow follow-up

- Sincronizar las especificaciones delta con las especificaciones principales (`openspec sync`).
- Validar las especificaciones con `openspec validate --specs`.
- Archivar el cambio completado mediante `openspec archive c-03-auth-core`.
