# Design: C-01 foundation-setup

## Context

Repositorio greenfield: solo existen `knowledge-base/`, `CHANGES.md`, `AGENTS.md`/`CLAUDE.md` y `openspec/`. No hay código, dependencias ni CI. La motivación está en `proposal.md` (Why) y los requisitos en `specs/`. Restricciones que dan forma al diseño:

- Stack fijo y presupuesto cero (`AGENTS.md`, reglas duras 5, 9, 10, 14).
- Sin worker persistente ni Redis obligatorio (DD-13, regla dura 9).
- Compose según DD-15 y `knowledge-base/12_devops_y_despliegue.md` §Servicios de Docker Compose.
- Alembic asíncrono con un único head (DD-14, SU-29, regla dura 8).
- TDD estricto en apply; integración contra PostgreSQL real, nunca SQLite (regla dura 3).
- La estructura de carpetas sigue `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios.

## Goals / Non-Goals

**Goals:**
- Dejar ejecutables `pytest`, `vitest`, `alembic upgrade head`, `docker compose up` y el CI en una sola sesión de 4 a 6 horas.
- Fijar convenciones que C-02 en adelante reutilizan sin rediscutir: carga de configuración, logging, layout de tests, fixture de PostgreSQL, chequeo de heads.

**Non-Goals:**
- `DeclarativeBase`, modelos, `async_sessionmaker`, `UnitOfWork`, puerto `Reloj` y semilla (C-02). `target_metadata` queda en `None` hasta C-02.
- JWT, hash de contraseñas, CORS, `OPENAPI_DOCS_ENABLED` y restricción de `/docs` (C-03, C-11, C-20).
- `POST /internal/barrido` y el bucle del barrido (C-15): `app/api/internal/` se crea vacío.
- Restricción de exclusión de turnos (C-07). Despliegue en Neon, host de la API o Cloudflare Pages (C-20).
- UI real del frontend: solo una página mínima que prueba la cadena de herramientas.

## Decisions

### D1. Nombre del archivo: `docker-compose.yml`
La skill `docker-compose-patterns` prefiere `compose.yaml`, pero `CHANGES.md`, la KB 12 y las reglas del proyecto nombran `docker-compose.yml`. Prevalece el proyecto. Alternativa descartada: renombrar y actualizar la KB (fuera del alcance de C-01).

### D2. Ruta del endpoint de salud: `GET /api/v1/health`
`CHANGES.md` propone `/api/v1/health` y la KB 12 cita `/health` "a confirmar al implementar". Se adopta `/api/v1/health` para que todo endpoint público viva bajo el prefijo versionado y el `VITE_API_BASE_URL` (`…/api/v1`) lo alcance. El healthcheck de Compose usa esa ruta. **Supuesto:** el hosting elegido en Q-24 admite una ruta de salud configurable.

### D3. Salud de vida (liveness), sin consultar la base
El endpoint no abre conexiones. Razones: Neon suspende el cómputo tras 5 minutos sin actividad y cobra CU-h (Q-27); un healthcheck cada 30 s que consulte la base mantendría el cómputo despierto y reiniciaría la API cuando la base esté suspendida. La disponibilidad de la base se garantiza por el orden de Compose (`migrate` termina antes de `api`). Alternativa descartada: `/health` con `SELECT 1` (readiness); se puede agregar luego como ruta separada si hace falta.

### D4. Configuración con `pydantic-settings`
`app/core/config.py` define `Settings(BaseSettings)` con `secrets_dir` configurable (por defecto `/run/secrets`, sobreescribible con `SECRETS_DIR` para tests), `case_sensitive=False`, campos obligatorios `database_url: SecretStr` y `jwt_secret_key: SecretStr`, `redis_url: str | None = None`, `app_env: Literal["development","test","production"]`, `app_timezone` con el valor por defecto de la KB. La precedencia de `pydantic-settings` (entorno > archivo de secreto) coincide con el spec. Los secretos se tipan como `SecretStr` para que `repr` y errores no muestren valores. Una función `get_settings()` con `lru_cache` se usa como dependencia; los tests llaman a `Settings(...)` directamente o limpian la caché. Las demás variables de la KB 08 (SMTP, barrido, TTL) se agregan en el change que las consume; **supuesto**: en C-01 solo `DATABASE_URL` y `JWT_SECRET_KEY` son obligatorias, como dice el scope de C-01. Alternativa descartada: lectura manual de `os.environ` (más código propio sin ventaja).

### D5. Logging JSON con biblioteca estándar
`app/core/logging.py`: un `logging.Formatter` propio que emite JSON por línea, un `contextvars.ContextVar` con el `request_id` y un filtro de redacción que reemplaza por `***` los valores sensibles conocidos (los `SecretStr` de `Settings`, más la contraseña extraída de `DATABASE_URL`) en el mensaje y en los campos extra. Un middleware ASGI puro (no `BaseHTTPMiddleware`, para no romper `contextvars`) valida o genera el `X-Request-ID` (`uuid4().hex`) y lo devuelve. Alternativa descartada: `structlog` o `python-json-logger` (dependencia extra para lo que resuelven 60 líneas probadas).

### D6. App factory y lifespan
`app/main.py` expone `create_app(settings: Settings | None = None) -> FastAPI` y `app = create_app()` para Uvicorn. El router de salud vive en `app/api/v1/routers/health.py` y se incluye con prefijo `/api/v1`. Se usa `lifespan` (no `on_event`) y `Annotated` según la skill `fastapi`. La validación de configuración ocurre al construir la app, así un arranque sin variables obligatorias falla antes de aceptar tráfico.

### D7. Alembic asíncrono sin modelos
Se ejecuta `alembic init -t async alembic` dentro de `backend/`. `env.py` toma la URL de `get_settings().database_url` (nunca de `alembic.ini`), activa `compare_type=True` y deja `target_metadata = None` hasta C-02. La skill `alembic` prefiere el runner síncrono; prevalece DD-14 (`-t async`). Se ignoran SQLite y `render_as_batch` (registro de skills). Migración base `0001_base_extensions` con `op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")`; `downgrade` ejecuta `DROP EXTENSION IF EXISTS btree_gist`. Identificadores de revisión legibles con `--rev-id` para que el orden de archivado sea explícito.

### D8. Chequeo de un único head como script probado
`backend/scripts/check_single_head.py` usa `alembic.script.ScriptDirectory` para obtener `get_heads()`; recibe la ruta del directorio de scripts como argumento (por defecto el del proyecto), imprime los heads y sale con código 1 si hay más de uno. Así se prueba con fixtures (`tests/fixtures/alembic_two_heads/`, `alembic_single_head/`) sin base de datos. CI lo ejecuta además de `alembic heads`. Alternativa descartada: parsear la salida de `alembic heads` en shell (frágil y no testeable con pytest).

### D9. PostgreSQL de pruebas por `TEST_DATABASE_URL`
Las pruebas de integración (`pytest -m integration`) usan la URL de `TEST_DATABASE_URL`; si no está definida, la fixture falla con un mensaje explícito (no se omiten en silencio). En CI la provee un `services: postgres` de GitHub Actions; en local, un contenedor descartable documentado en el README (`docker run --rm -p 55432:5432 postgres:<versión>`). Cada test de migración crea y elimina su propia base (`CREATE DATABASE c01_<uuid>`) para empezar vacía. Alternativa descartada: `testcontainers` (más dependencias y Docker dentro del runner; se puede adoptar luego sin cambiar los tests). `pytest-asyncio` en modo `auto`.

### D10. Contrato de Compose como test
`backend/tests/infra/test_compose_contract.py` carga `../docker-compose.yml` con PyYAML y verifica los requisitos de `specs/local-environment` (sin `version`, servicios exactos, healthchecks, `depends_on`, perfiles, secretos, `restart`). `docker compose config --quiet` se ejecuta en CI y en la verificación manual. Para que `config` resuelva los secretos, CI genera archivos de secreto de prueba en `secrets/` antes de validar.

### D11. Imágenes
Backend: Dockerfile multi-etapa sobre `python:3.13-slim` (**supuesto** de versión, se fija al crear), dependencias instaladas antes del código para cachear, usuario no root con UID 1001, `EXPOSE 8000`, `CMD` en forma exec. `migrate` y `api` comparten la imagen con distinto `command`. Frontend: Dockerfile con etapa `dev` (servidor de Vite, la que usa Compose) y etapa `runtime` estática sobre `nginxinc/nginx-unprivileged` para la alternativa en VM (Q-29); CI construye ambas. `.dockerignore` en cada carpeta excluye `.env`, `secrets/`, `node_modules/`, `.venv/` y `.git/`. Imágenes con versión fija (`postgres:17-alpine`, `redis:7-alpine`, `axllent/mailpit:<tag>`; **supuesto**: versiones exactas se fijan al implementar).

### D12. Frontend mínimo
Vite + React + TypeScript (`strict: true`, sin `any`), Vitest con `jsdom` y Testing Library. Una página `App` que muestra el título del sistema en español; su test es la prueba de humo del toolchain. Carpetas de la KB 08 (`app/`, `components/atoms…templates`, `features/`, `pages/`, `services/`, `shared/`) creadas solo cuando tienen contenido, para no versionar directorios vacíos con `.gitkeep` innecesarios; **excepción**: el backend sí crea los paquetes de capas con `__init__.py` porque el scope de C-01 los nombra.

### D13. CI en GitHub Actions
`.github/workflows/ci.yml` con jobs `backend` (servicio PostgreSQL, `pytest` completo, `alembic upgrade head` sobre base vacía, chequeo de heads), `frontend` (`npm ci`, `tsc --noEmit`, `vitest run`, `vite build`) y `images` (`docker compose config --quiet` y `docker build` de backend y frontend). El repositorio está en GitHub: Actions es gratuito para repositorios públicos y tiene cuota gratuita en privados.

## Risks / Trade-offs

- [Q-26: el proveedor no permite `CREATE EXTENSION btree_gist` con el usuario de la app] → En local y CI no aplica (superusuario del contenedor). Para Neon se valida en el spike de infraestructura; si falla, se habilita desde la consola y la migración sigue siendo idempotente (`IF NOT EXISTS`).
- [Q-29: se exige el stack completo en una VM] → El mismo Compose sirve; la etapa `runtime` del frontend ya existe. No cambia este change.
- [Salud sin base puede reportar "ok" con la base caída] → Aceptado (D3). La API devuelve errores en los endpoints que usan la base; C-20 puede sumar una ruta de readiness.
- [Divergencia con la skill de Compose (`compose.yaml`) y de Alembic (runner síncrono)] → Documentado en D1 y D7; prevalece el proyecto.
- [Versiones de imágenes y paquetes no fijadas por la KB] → Se fijan al implementar con la última versión estable y se registran en `pyproject.toml`, `package-lock.json` y los `FROM`.
- [Tiempo de sesión] → Alcance limitado a lo que nombra `CHANGES.md`; el frontend es solo humo.

## Migration Plan

No hay datos ni sistema previo. Aplicación: `docker compose up` (o `alembic upgrade head` contra la base de destino). Reversión: `alembic downgrade base` y borrar los archivos nuevos; no afecta otros changes porque es el primero.

## Open Questions

- Versión exacta de PostgreSQL local para coincidir con Neon (17 es el supuesto); se resuelve al implementar sin cambiar specs ni tareas.
