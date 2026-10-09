# Tasks

> TDD estricto: en cada tarea marcada **[TDD]** se escribe primero el test, se observa RED, luego GREEN, TRIANGULATE y REFACTOR. Las tareas marcadas **[Estructural]** son scaffolding sin comportamiento propio: no tienen un RED significativo y se verifican con el chequeo indicado. Cada tarea cita el requisito que cubre (`capability › Requirement`). Estimación total: 4 a 6 horas.

## 1. Andamiaje del backend

- [ ] 1.1 [Estructural] Crear `backend/pyproject.toml` (Python 3.13, FastAPI, Uvicorn, pydantic-settings, SQLAlchemy 2.x, asyncpg, Alembic; grupo de desarrollo con pytest, pytest-asyncio en modo `auto`, httpx y PyYAML; marcador `integration`) y los paquetes vacíos `app/{core,domain,application,infrastructure,api,api/internal,api/v1,api/v1/routers}` y `tests/{unit,integration,api,infra}` con `__init__.py`. Verificar: `pytest --collect-only` termina sin errores y `python -c "import app"` funciona. (base de todas las capabilities)
- [ ] 1.2 [Estructural] Agregar a `.gitignore` `.env`, `secrets/`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `node_modules/` y `dist/`, y crear `.env.example` con las variables de la KB 08 que usa C-01 (`APP_ENV`, `APP_TIMEZONE`, `DATABASE_URL`, `POSTGRES_USER`, `POSTGRES_DB`, `REDIS_URL` comentada, `VITE_API_BASE_URL`) sin valores reales. Verificar: `git check-ignore secrets/jwt_secret_key.txt .env` lista ambas rutas. (local-environment › Secretos como archivos montados y no versionados)

## 2. Configuración en tiempo de ejecución

- [ ] 2.1 [TDD] `tests/unit/test_config.py`: RED con arranque sin `DATABASE_URL` y sin `JWT_SECRET_KEY` (error que nombra la variable y no muestra valores); GREEN con `Settings` en `app/core/config.py` (D4); TRIANGULATE con configuración completa. Verificar: `pytest tests/unit/test_config.py` en verde. (runtime-configuration › Arranque rechazado sin configuración obligatoria)
- [ ] 2.2 [TDD] Tests de secretos desde archivo con `SECRETS_DIR` apuntando a `tmp_path`: valor solo en archivo (con `\n` final), entorno con prioridad sobre archivo, directorio inexistente. Verificar: los tres escenarios pasan. (runtime-configuration › Valores leídos desde archivos de secreto)
- [ ] 2.3 [TDD] Tests de `REDIS_URL` ausente (arranca, Redis no configurado), valores por defecto de `APP_ENV`/`APP_TIMEZONE` y rechazo de `APP_ENV=staging`. Verificar: `pytest tests/unit/test_config.py` en verde. (runtime-configuration › Redis es opcional; › Valores por defecto de operación)

## 3. Logging estructurado

- [ ] 3.1 [TDD] `tests/unit/test_logging.py`: RED con un registro `INFO` que debe salir como una línea JSON con `timestamp` UTC, `level`, `logger` y `message`; GREEN con el formateador de `app/core/logging.py` (D5). Verificar: test en verde. (structured-logging › Registros estructurados)
- [ ] 3.2 [TDD] Tests de redacción: mensaje con `JWT_SECRET_KEY`, `DATABASE_URL` con contraseña, campo extra con `SMTP_PASSWORD` y error de arranque por configuración inválida; ninguna línea contiene el valor y aparece `***`. Verificar: los cuatro escenarios pasan. (structured-logging › Sin valores sensibles en los registros)

## 4. Aplicación y endpoint de salud

- [ ] 4.1 [TDD] `tests/api/test_health.py` con `httpx.AsyncClient` + `ASGITransport`: RED con `GET /api/v1/health` → `200` y cuerpo exacto `{"status": "ok"}`; GREEN con `create_app()` en `app/main.py` y el router `app/api/v1/routers/health.py` (D6); TRIANGULATE con `POST` → `405` y cuerpo con única clave `status`. Verificar: tests en verde. (api-health › Endpoint de salud de la API; › La salud no expone información interna)
- [ ] 4.2 [TDD] Test con `DATABASE_URL` apuntando a un puerto sin servidor (`postgresql+asyncpg://u:p@127.0.0.1:1/x`): la salud sigue respondiendo `200`. Verificar: test en verde. (api-health › La salud no depende de la base de datos)
- [ ] 4.3 [TDD] Tests del middleware de `X-Request-ID`: generado si falta, devuelto si es válido (`abc-123`), reemplazado si mide 300 caracteres o tiene espacios, distinto entre dos solicitudes, y presente como `request_id` en los registros capturados de la solicitud. Verificar: tests en verde. (structured-logging › Identificador de solicitud)

## 5. Migraciones de esquema

- [ ] 5.1 [Estructural] Ejecutar `alembic init -t async alembic` en `backend/`, ajustar `env.py` para leer `get_settings().database_url`, `compare_type=True`, `target_metadata = None`, y quitar la URL de `alembic.ini` (D7). Verificar: `alembic heads` corre sin error y `rg -n "postgresql" alembic.ini` no devuelve credenciales. (schema-migrations › Conexión de migraciones desde la configuración)
- [ ] 5.2 [TDD] `tests/integration/conftest.py` con la fixture de base vacía por test sobre `TEST_DATABASE_URL` (falla explícita si falta, D9) y `tests/integration/test_migrations.py`: RED con `alembic upgrade head` sobre base vacía → código 0 y `btree_gist` en `pg_extension`; GREEN con la revisión `0001_base_extensions`; TRIANGULATE con aplicación repetida y con la extensión ya instalada antes de migrar. Verificar: `pytest -m integration` en verde contra PostgreSQL real. (schema-migrations › Migración base con btree_gist; › Conexión de migraciones desde la configuración)
- [ ] 5.3 [TDD] `tests/unit/test_single_head.py` con fixtures `tests/fixtures/alembic_single_head/` y `alembic_two_heads/` (dos revisiones con el mismo padre): RED esperando código distinto de 0 y ambos identificadores en la salida; GREEN con `scripts/check_single_head.py` (D8); TRIANGULATE con la historia lineal (código 0) y con el directorio real del proyecto. Verificar: tests en verde y `python scripts/check_single_head.py` sale con 0. (schema-migrations › Historia con un único head)

## 6. Frontend

- [ ] 6.1 [Estructural] Crear `frontend/` con Vite + React + TypeScript (`strict: true`), Vitest con entorno `jsdom`, Testing Library y scripts `test`, `typecheck` y `build` en `package.json`; fijar versiones con `package-lock.json`. Verificar: `npm ci` y `npm run typecheck` terminan con código 0. (continuous-integration › Frontend, imágenes y Compose verificados en CI)
- [ ] 6.2 [TDD] `src/App.test.tsx`: RED esperando un encabezado accesible (`getByRole('heading')`) con el nombre del sistema en español; GREEN con `src/App.tsx` y `src/main.tsx`. Verificar: `npm test -- --run` y `npm run build` terminan con código 0. (continuous-integration › Frontend, imágenes y Compose verificados en CI)

## 7. Imágenes y Docker Compose

- [ ] 7.1 [Estructural] `backend/Dockerfile` multi-etapa no root y `backend/.dockerignore`; `frontend/Dockerfile` con etapas `dev` y `runtime` y `frontend/.dockerignore` (D11). Verificar: `docker build backend` y `docker build --target runtime frontend` terminan con código 0 y `docker inspect` muestra un usuario distinto de root en la imagen del backend. (continuous-integration › Frontend, imágenes y Compose verificados en CI)
- [ ] 7.2 [TDD] `backend/tests/infra/test_compose_contract.py` (D10): RED con las aserciones de servicios exactos, sin `version`, sin `worker`, `db` con volumen con nombre y `pg_isready`, `migrate` con `alembic upgrade head` y `service_healthy`, `api` con `service_completed_successfully`, `restart: unless-stopped` y healthcheck a `/api/v1/health`, `frontend` con `service_healthy`, perfiles `redis` y `dev`, secreto `jwt_secret_key` y ninguna variable sensible literal; GREEN escribiendo `docker-compose.yml`. Verificar: test en verde. (local-environment › todos los requisitos de configuración; schema-migrations › Migraciones solo con upgrade head)
- [ ] 7.3 [Estructural] Con archivos de secreto de prueba en `secrets/`: `docker compose config --quiet` → 0; `docker compose config --services` sin perfiles no incluye `redis` ni `mailpit`; `docker compose up -d --wait` sobre volumen vacío deja `migrate` terminado con 0 y `api` saludable; con `--profile dev`, `mailpit` responde en el puerto 8025. Verificar: salidas observadas registradas en el log de apply. (local-environment › Archivo de Compose válido; › Migración previa a la API; › Servicios auxiliares bajo perfiles)

## 8. Integración continua y documentación

- [ ] 8.1 [Estructural] `.github/workflows/ci.yml` con jobs `backend` (servicio PostgreSQL, `TEST_DATABASE_URL`, `pytest` completo sin omitidos, `alembic upgrade head` sobre base vacía, `alembic heads` y `scripts/check_single_head.py`), `frontend` (`npm ci`, `typecheck`, `test`, `build`) e `images` (secretos de prueba, `docker compose config --quiet`, build de ambas imágenes) en `push` y `pull_request` a `main` (D13). Verificar: el workflow valida (por ejemplo con `actionlint` si está disponible) y, al subir la rama, el run queda en verde. (continuous-integration › Verificación en cada cambio; › Pruebas de backend contra PostgreSQL real; › Migraciones verificadas en CI; › Frontend, imágenes y Compose verificados en CI)
- [ ] 8.2 [Estructural] `README.md` con prerrequisitos, creación de `secrets/` y `.env` a partir de `.env.example`, `docker compose up` (y `--profile dev`), cómo correr `pytest` (unitarias e integración con el contenedor descartable de D9), `npm test` y el chequeo de un único head. Verificar: cada comando del README se ejecuta tal como está escrito en una copia limpia. (local-environment; schema-migrations › Historia con un único head)

## 9. Verificación integral

- [ ] 9.1 Ejecutar la suite completa (`pytest` con `TEST_DATABASE_URL`, `npm test -- --run`, `npm run typecheck`, `docker compose config --quiet`, `python scripts/check_single_head.py`) y `rg -n "upgrade heads" docker-compose.yml backend .github README.md` sin coincidencias. Verificar: todo en verde y ningún test integración omitido. (todas las capabilities del change)
