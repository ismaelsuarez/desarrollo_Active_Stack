# Proposal: C-01 foundation-setup

## Why

El repositorio no tiene código: no existe backend, frontend, base de datos local ni forma de ejecutar pruebas. Todo el camino crítico (`C-01 → C-02 → C-03 → …`) depende de una base ejecutable y verificable, y con la entrega del MVP fijada para el 2026-10-19 no hay margen para que cada change resuelva su propia infraestructura. C-01 entrega esa base una sola vez, con las reglas duras del proyecto ya aplicadas.

## What Changes

- Estructura del monorepo: `backend/` en capas (`app/domain`, `app/application`, `app/infrastructure`, `app/api` con `internal/`, `app/core`) y `frontend/` (Vite + React + TypeScript), según `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios.
- `docker-compose.yml` **sin clave `version`** con los servicios `db` (PostgreSQL con volumen y healthcheck), `migrate` (`alembic upgrade head` y termina), `api` (healthcheck y `restart: unless-stopped`), `frontend`, `redis` (opcional, perfil `redis`) y `mailpit` (perfil `dev`); `depends_on` con `service_healthy` y `service_completed_successfully`; secretos montados en `/run/secrets/<nombre>`. Sin servicio `worker`.
- `.env.example` versionado sin valores reales; `.env` y `secrets/` excluidos de Git.
- Endpoint de salud `GET /api/v1/health`, usado por el healthcheck del servicio `api`.
- Configuración de la aplicación que lee las variables de entorno y los archivos de `/run/secrets`, falla al arrancar sin `DATABASE_URL` o `JWT_SECRET_KEY`, y trata `REDIS_URL` como opcional.
- Logging estructurado con identificador de solicitud y sin valores sensibles.
- Alembic con `env.py` asíncrono, `compare_type=True` y una migración base que ejecuta `CREATE EXTENSION IF NOT EXISTS btree_gist`.
- Verificación de un único head de Alembic, ejecutable localmente y en CI.
- pytest con PostgreSQL real en contenedor para integración; Vitest + Testing Library en el frontend.
- CI gratuito (GitHub Actions): tests de backend y frontend, build de imágenes, `alembic upgrade head` sobre base vacía, chequeo de un único head y validación de Compose.

Fuera de alcance (otros changes): modelos, sesión asíncrona y semilla (C-02); autenticación, JWT y RBAC (C-03); políticas ABAC (C-04); barrido y `POST /internal/barrido` (C-15); restricción de exclusión de turnos (C-07); endurecimiento y despliegue en Neon/Cloudflare (C-20).

## Capabilities

### New Capabilities

- `api-health`: disponibilidad del proceso de la API, expuesta a orquestadores y monitores.
- `runtime-configuration`: carga, validación y origen (entorno o archivo de secreto) de la configuración al arrancar.
- `structured-logging`: registro estructurado con correlación por solicitud y protección de valores sensibles.
- `schema-migrations`: versionado del esquema de PostgreSQL con historia lineal de un único head y extensiones base.
- `local-environment`: entorno local reproducible con Docker Compose y su contrato de servicios.
- `continuous-integration`: verificaciones automáticas que todo cambio debe superar.

### Modified Capabilities

Ninguna (no existen specs previas en `openspec/specs/`).

## Impact

- **Código nuevo**: `backend/` (FastAPI, configuración, logging, Alembic, tests), `frontend/` (Vite, React, TypeScript, Vitest), `docker-compose.yml`, `.env.example`, Dockerfiles y `.dockerignore`, `.github/workflows/ci.yml`, `README.md` con el arranque local.
- **Archivos existentes**: `.gitignore` suma `.env`, `secrets/`, artefactos de Python y `node_modules/`.
- **Dependencias** (todas gratuitas): FastAPI, Uvicorn, pydantic-settings, SQLAlchemy 2.x asíncrono, asyncpg, Alembic, pytest, pytest-asyncio, httpx, PyYAML; React, Vite, TypeScript, Vitest, Testing Library, jsdom. Imágenes oficiales de PostgreSQL, Redis y Mailpit.
- **API**: aparece `GET /api/v1/health`. No hay otros endpoints.
- **Riesgos abiertos**: Q-26 (`btree_gist` en el proveedor elegido; la migración base falla si no está permitida) y Q-29 (despliegue del stack completo en una VM; no cambia este change).
