# Proposal: C-01 foundation-setup

## Why

C-00 (`crear-turno-sin-solapamientos`) ya entregó el backend mínimo, la migración inicial y pruebas contra PostgreSQL real. C-01 completa la base de desarrollo local y CI de la segunda parte (DD-33), reutilizando ese trabajo sin cambiar el comportamiento de `appointment-booking`; faltan la aplicación HTTP, el frontend y el entorno integrado reproducible.

## What Changes

- Ampliación de la estructura existente del monorepo, sin reemplazar código ni pruebas de C-00: `backend/` en capas (`app/domain`, `app/application`, `app/infrastructure`, `app/api` con `internal/`, `app/core`) y `frontend/` (Vite + React + TypeScript), según `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios.
- `docker-compose.yml` **sin clave `version`** con los servicios `db` (PostgreSQL con volumen y healthcheck), `migrate` (`alembic upgrade head` y termina), `api` (healthcheck y `restart: unless-stopped`), `frontend`, `redis` (opcional, perfil `redis`) y `mailpit` (perfil `dev`); `depends_on` con `service_healthy` y `service_completed_successfully`; secretos montados en `/run/secrets/<nombre>`. Sin servicio `worker`.
- `.env.example` versionado sin valores reales; `.env` y `secrets/` excluidos de Git.
- Endpoint de salud `GET /api/v1/health`, usado por el healthcheck del servicio `api`.
- Configuración de la aplicación que lee las variables de entorno y los archivos de `/run/secrets`, falla al arrancar sin `APP_ENV`, `DATABASE_URL` o `JWT_SECRET_KEY` (o con una clave de firma de menos de 32 bytes), y trata `REDIS_URL` como opcional.
- Logging estructurado con identificador de solicitud y sin valores sensibles.
- Adaptación del Alembic asíncrono existente a la configuración de base de datos, conservando `compare_type=True`, `target_metadata = None`, `NullPool` y la revisión `0001_turnos_sin_solapamiento`, que ya instala `btree_gist`. No se reinicializa Alembic ni se crea otra raíz; solo un cambio real de esquema justificaría una revisión descendiente.
- Verificación de un único head de Alembic, ejecutable localmente y en CI.
- pytest con PostgreSQL real en contenedor para integración; Vitest + Testing Library en el frontend.
- CI gratuito (GitHub Actions): tests de backend y frontend, build de imágenes, `alembic upgrade head` sobre base vacía, chequeo de un único head y validación de Compose.

Fuera de alcance (otros changes): ampliar los modelos y la sesión asíncrona más allá de lo ya entregado por C-00, y agregar la semilla (C-02); autenticación, JWT y RBAC (C-03); políticas ABAC (C-04); barrido y `POST /internal/barrido` (C-15); nuevas reglas de turnos (C-07; se conserva la restricción de exclusión de C-00); endurecimiento y despliegue en Neon y en el host de la API (C-20).

## Capabilities

### New Capabilities

- `api-health`: disponibilidad del proceso de la API, expuesta a orquestadores y monitores.
- `runtime-configuration`: carga, validación y origen (entorno o archivo de secreto) de la configuración al arrancar.
- `structured-logging`: registro estructurado con correlación por solicitud y protección de valores sensibles.
- `schema-migrations`: versionado del esquema de PostgreSQL con historia lineal de un único head y extensiones base.
- `local-environment`: entorno local reproducible con Docker Compose y su contrato de servicios.
- `continuous-integration`: verificaciones automáticas que todo cambio debe superar.

### Modified Capabilities

Ninguna. La especificación existente `appointment-booking` se conserva íntegra; C-01 no modifica sus requisitos.

## Impact

- **Código nuevo o ampliado**: `backend/` (FastAPI, configuración, logging y pruebas nuevas sobre la estructura existente), `frontend/` (Vite, React, TypeScript, Vitest), `docker-compose.yml`, `.env.example`, Dockerfiles y `.dockerignore`, `.github/workflows/ci.yml`, `scripts/dev_secrets.sh` y `scripts/smoke_compose.sh`, y una sección de desarrollo local en el `README.md` existente.
- **Archivos existentes**: se amplían `backend/pyproject.toml` y `uv.lock` sin eliminar las dependencias de C-00, se adapta `backend/alembic/env.py` y se reutilizan sus fixtures y pruebas. `.gitignore` suma solo las exclusiones faltantes; el README conserva las instrucciones de pruebas existentes.
- **Dependencias existentes y nuevas** (todas gratuitas; conservar las versiones bloqueadas salvo cambios necesarios para incorporar C-01): FastAPI, Uvicorn, pydantic-settings, SQLAlchemy 2.x asíncrono, asyncpg, Alembic, pytest, pytest-asyncio, httpx, PyYAML; React, Vite, TypeScript, Vitest, Testing Library, jsdom. Imágenes oficiales de PostgreSQL, Redis y Mailpit.
- **API**: aparece `GET /api/v1/health`. No hay otros endpoints.
- **Riesgos abiertos**: ninguno bloquea este change. Q-26 (`btree_gist` en el proveedor publicado; la migración base fallaría allí si no está permitida) y Q-29 (despliegue del stack completo en una VM) afectan solo al despliegue publicado y se resuelven antes de C-20 (DD-22); en local y en CI PostgreSQL corre como superusuario y la migración base funciona.
