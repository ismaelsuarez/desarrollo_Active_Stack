# Design: C-01 foundation-setup

## Context

C-00 está archivado y entregó `backend/` en capas, dependencias bloqueadas, repositorios y unidad de trabajo, Alembic asíncrono con la revisión `0001_turnos_sin_solapamiento` y pruebas contra PostgreSQL real. C-01 extiende esa base con HTTP, frontend, Compose y CI; no recrea ni elimina lo existente. La motivación está en `proposal.md` (Why) y los requisitos en `specs/`. Restricciones que dan forma al diseño:

- Stack fijo y presupuesto cero (`AGENTS.md`, reglas duras 5, 9, 10, 14).
- Sin worker persistente ni Redis obligatorio (DD-13, regla dura 9).
- Compose según DD-15 y `knowledge-base/12_devops_y_despliegue.md` §Servicios de Docker Compose.
- Alembic asíncrono con un único head (DD-14, SU-29, regla dura 8).
- TDD estricto en apply; integración contra PostgreSQL real, nunca SQLite (regla dura 3).
- La estructura de carpetas sigue `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios.

## Goals / Non-Goals

**Goals:**
- Integrar `pytest` y Alembic ya existentes con `vitest`, `docker compose up` y CI, manteniendo en verde las pruebas de C-00.
- Fijar convenciones que C-02 en adelante reutilizan sin rediscutir: carga de configuración, logging, layout de tests, fixture de PostgreSQL, chequeo de heads.

**Non-Goals:**
- Ampliar `DeclarativeBase`, modelos, `async_sessionmaker` y unidad de trabajo más allá de C-00; se reutilizan sin sustituirlos. El puerto `Reloj` y la semilla corresponden a C-02. Se conserva el `target_metadata = None` actual, usado con revisiones escritas a mano.
- JWT, hash de contraseñas, CORS, `OPENAPI_DOCS_ENABLED` y restricción de `/docs` (C-03, C-11, C-20).
- `POST /internal/barrido` y el bucle del barrido (C-15): `app/api/internal/` se crea vacío.
- Agregar reglas de turnos (C-07); la restricción de exclusión y el comportamiento de `appointment-booking` entregados por C-00 se conservan. Despliegue en Neon y en el host de la API, que sirve también el frontend compilado (C-20, DD-26); el proxy de Vite hacia la API lo configura C-11.
- UI real del frontend: solo una página mínima que prueba la cadena de herramientas.

## Decisions

### D1. Nombre del archivo: `docker-compose.yml`
La skill `docker-compose-patterns` prefiere `compose.yaml`, pero `CHANGES.md`, la KB 12 y las reglas del proyecto nombran `docker-compose.yml`. Prevalece el proyecto. Alternativa descartada: renombrar y actualizar la KB (fuera del alcance de C-01).

### D2. Ruta del endpoint de salud: `GET /api/v1/health`
La ruta es `GET /api/v1/health`: todo endpoint público vive bajo el prefijo versionado y el `VITE_API_BASE_URL` (`…/api/v1`) lo alcanza. Las tablas de rutas de la KB 02 y 03 son relativas al prefijo `/api/v1`, así que su `GET /health` es esta misma ruta; `CHANGES.md` y la KB 12 la nombran completa. El healthcheck de Compose usa esa ruta. **Supuesto:** el hosting elegido en Q-24 admite una ruta de salud configurable.

### D3. Salud de vida (liveness), sin consultar la base
El endpoint no abre conexiones. Razones: Neon suspende el cómputo tras 5 minutos sin actividad y cobra CU-h (Q-27); un healthcheck cada 30 s que consulte la base mantendría el cómputo despierto y reiniciaría la API cuando la base esté suspendida. La disponibilidad de la base se garantiza por el orden de Compose (`migrate` termina antes de `api`). Alternativa descartada: `/health` con `SELECT 1` (readiness); se puede agregar luego como ruta separada si hace falta.

### D4. Configuración con `pydantic-settings`
`app/core/config.py` define dos clases. `DatabaseSettings(BaseSettings)` tiene `database_url: SecretStr` obligatoria y `migrations_database_url: SecretStr | None = None`, y expone la URL de migraciones (la propia si está definida; si no, `database_url`). `Settings(DatabaseSettings)` agrega `jwt_secret_key: SecretStr` obligatoria con un validador de longitud mínima de 32 bytes (el mínimo de HS256), `app_env: Literal["development","test","production"]` obligatoria y sin valor por defecto, `redis_url: str | None = None` y `app_timezone` con el valor por defecto de la KB. Las dos usan `secrets_dir` configurable (por defecto `/run/secrets`, sobreescribible con `SECRETS_DIR` para tests), `case_sensitive=False` y `hide_input_in_errors=True`: cuando la configuración no se puede construir no hay instancia que consultar, y con esa opción los errores de pydantic listan solo el nombre de los campos y nunca los valores de entrada. Alembic carga solo `DatabaseSettings`, así el servicio `migrate` no necesita `JWT_SECRET_KEY` ni `APP_ENV`. `APP_ENV` no tiene valor por defecto para que un despliegue que olvida definirla falle al arrancar en lugar de quedar en modo de desarrollo. La precedencia de `pydantic-settings` (entorno > archivo de secreto) coincide con el spec. Los secretos se tipan como `SecretStr` para que `repr` y errores no muestren valores. Una función `get_settings()` con `lru_cache` se usa como dependencia; los tests llaman a `Settings(...)` directamente o limpian la caché. Las demás variables de la KB 08 se agregan en el change que las consume: `CONSULTORIO_ACTIVO_ID` en C-02, `ORIGIN_HASH_SECRET` y `TRUSTED_PROXY_HOPS` en C-03 (C-05 las reutiliza, DD-25), y SMTP, barrido y TTL en los suyos. El servicio `seed` que agrega C-02 no carga `Settings`: carga su propia `SeedSettings`, que extiende `DatabaseSettings` con lo que la semilla necesita, de modo que los secretos obligatorios que agreguen los changes posteriores se montan solo en `api`. En C-01 las obligatorias son `APP_ENV`, `DATABASE_URL` y `JWT_SECRET_KEY`. Alternativa descartada: lectura manual de `os.environ` (más código propio sin ventaja).

### D5. Logging JSON con biblioteca estándar
`app/core/logging.py`: un `logging.Formatter` propio que emite JSON por línea, un `contextvars.ContextVar` con el `request_id` y un filtro de redacción que reemplaza por `***` los valores sensibles en el mensaje y en los campos extra. El filtro recibe la instancia de configuración y recorre sus campos: oculta el valor de todo campo de tipo `SecretStr` y, además, la contraseña extraída de los campos que son una URL de base. No hay una lista de nombres: un change posterior que agrega un campo `SecretStr` queda cubierto sin tocar `logging.py`, y lo prueba con un test propio (KB 08 §Variables de entorno). La redacción reemplaza por contenido, así que un valor secreto vacío reemplazaría la cadena vacía en todas partes y uno muy corto rompería palabras corrientes: los valores vacíos y los de menos de 4 caracteres no se redactan (los secretos reales son más largos: `JWT_SECRET_KEY` exige 32 bytes y las URL de base se tratan por su contraseña). Si la configuración no se puede construir (arranque inválido) no hay instancia de configuración que recorrer: ese error se informa con `hide_input_in_errors=True` de pydantic (D4), cuyo mensaje lista solo nombres de campo, de modo que no hay valores que redactar. Un middleware ASGI puro (no `BaseHTTPMiddleware`, para no romper `contextvars`) valida o genera el `X-Request-ID` (`uuid4().hex`) y lo devuelve. Alternativa descartada: `structlog` o `python-json-logger` (dependencia extra para lo que resuelven 60 líneas probadas).

### D6. App factory y lifespan
`app/main.py` expone `create_app(settings: Settings | None = None) -> FastAPI` y no crea ninguna aplicación al importarse: Uvicorn la construye con `uvicorn app.main:create_app --factory`. Así, importar el módulo en una prueba o en una herramienta no exige tener definida la configuración obligatoria; cada prueba construye su `Settings`. El router de salud vive en `app/api/v1/routers/health.py` y se incluye con prefijo `/api/v1`. Se usa `lifespan` (no `on_event`) y `Annotated` según la skill `fastapi`. La validación de configuración ocurre al construir la app, así un arranque sin variables obligatorias falla antes de aceptar tráfico.

### D7. Ampliación del Alembic asíncrono existente
Se modifica `backend/alembic/env.py`, sin ejecutar `alembic init` otra vez. La URL pasa de la lectura directa del entorno a `DatabaseSettings` (nunca a `Settings` ni a credenciales de `alembic.ini`). Se conservan el runner asíncrono, `compare_type=True`, `target_metadata = None` y `NullPool`; no se agrega autogenerate para la restricción de exclusión.

La revisión `0001_turnos_sin_solapamiento` ya crea `btree_gist` de forma idempotente y las tablas y la restricción de C-00. Se conserva sin reescribirla, renombrarla ni crear otra raíz. La adaptación de configuración no requiere DDL: se mantiene el head existente y no se crea una revisión vacía solo para C-01. Solo si surge un cambio real de esquema dentro del alcance autorizado se agrega una revisión con identificador legible y `down_revision` apuntando al único head vigente, sin `alembic merge`. La restricción de C-00 y la extensión no se eliminan al revertir C-01.

En producción, las migraciones usan `MIGRATIONS_DATABASE_URL` cuando existe para evitar el pooler; en otro caso usan `DATABASE_URL`. El servicio `migrate` sigue sin necesitar `APP_ENV` ni `JWT_SECRET_KEY`. Se ignoran SQLite, `render_as_batch` y la preferencia síncrona de la skill: prevalecen DD-14 y las reglas del proyecto.

### D8. Chequeo de un único head como script probado
`backend/scripts/check_single_head.py` usa `alembic.script.ScriptDirectory` para obtener `get_heads()`; recibe la ruta del directorio de scripts como argumento (por defecto el del proyecto), imprime los heads y sale con código 1 si hay más de uno. Así se prueba con fixtures (`tests/fixtures/alembic_two_heads/`, `alembic_single_head/`) sin base de datos. CI lo ejecuta además de `alembic heads`. Se conserva la prueba existente de historia única; si una modificación real de esquema agrega un descendiente, su expectativa deja de fijar el head antiguo y comprueba también que C-00 sigue en la cadena. Alternativa descartada: parsear la salida de `alembic heads` en shell (frágil y no testeable con pytest).

### D9. Reutilización de las pruebas PostgreSQL de C-00
Se conservan `tests/integration/conftest.py`, sus helpers de base temporal y Alembic, la fixture de sesión y sus fábricas. Las pruebas de integración usan PostgreSQL real por `TEST_DATABASE_URL`; si falta, fallan explícitamente y no se omiten. En local se mantiene el contenedor descartable `postgres:17` del README en el puerto 55432; en CI lo provee `services: postgres`.

Las pruebas de migración que necesitan empezar vacías reutilizan el helper de base temporal para crear y eliminar su propia base. Las demás mantienen una base de sesión migrada y limpieza con `TRUNCATE ... RESTART IDENTITY CASCADE`. No se reemplazan los commits reales por un rollback global: las pruebas de reservas simultáneas requieren datos visibles entre sesiones y una unidad de trabajo por ejecución. Se conserva `pytest-asyncio` en modo `auto` y la configuración de bucle de eventos existente. Los subprocesos de migración reciben la URL de su base aislada sin que una `MIGRATIONS_DATABASE_URL` del entorno los desvíe a otra base. Alternativa descartada: reemplazar la infraestructura por `testcontainers`, que agrega dependencias sin necesidad.

### D10. Contrato de Compose como test
`backend/tests/infra/test_compose_contract.py` carga `../docker-compose.yml` con PyYAML y verifica los requisitos de `specs/local-environment` (sin `version`, servicios exactos, healthchecks, `depends_on`, perfiles, secretos, `restart`). `docker compose config --quiet` se ejecuta en CI. Los dos scripts de entorno viven en `scripts/`, en la raíz del repositorio, junto a `docker-compose.yml`. Los secretos locales los genera `scripts/dev_secrets.sh`, idempotente: crea `secrets/postgres_password.txt` y `secrets/jwt_secret_key.txt` con valores aleatorios y arma `secrets/database_url.txt` con esa misma contraseña, así la contraseña de la base se escribe una sola vez y los dos archivos no pueden divergir; no pisa archivos existentes. `.env.example` trae `APP_ENV=development` (variable obligatoria y sin valor por defecto, que `api` recibe por `env_file`); `scripts/smoke_compose.sh` crea `.env` a partir de `.env.example` cuando no existe, y lo mismo hacen los jobs de CI que usan Compose, de modo que ni el arranque local ni CI dependan de una variable que nadie provee. Ningún valor sensible va en `.env`: `db` lee `POSTGRES_PASSWORD_FILE`, `migrate` recibe solo `database_url`, y `api` recibe `database_url` y `jwt_secret_key`. El arranque real se verifica con `scripts/smoke_compose.sh` en un proyecto Compose descartable con nombre único y volúmenes propios nuevos, sin volúmenes externos ni nombres globales fijos. Usa ese mismo nombre en todas las operaciones (`up`, inspecciones, `exec` y `down`). Genera los secretos, ejecuta `docker compose up -d --wait`, comprueba que `migrate` terminó con código 0, que `api` está saludable, que `GET /api/v1/health` responde `200` y que el proceso de `api` no es root (`docker compose exec api id -u`). Al terminar ejecuta `docker compose down -v` solo para ese proyecto descartable: nunca elimina ni reutiliza los volúmenes del entorno habitual. CI lo corre en un job propio y en local es un único comando.

### D11. Imágenes
Backend: Dockerfile multi-etapa sobre `python:3.13-slim` (**supuesto** de versión, se fija al crear), dependencias instaladas desde el archivo de bloqueo `uv.lock` (`uv sync --frozen`) antes del código para cachear, usuario no root con UID 1001, `EXPOSE 8000`, `CMD` en forma exec. `migrate` y `api` comparten la imagen con distinto `command`. Frontend: Dockerfile con etapa `dev` (servidor de Vite, la que usa Compose) y etapa `build` que produce `dist`; no hay etapa de servidor web ni nginx, porque la API sirve el frontend compilado (DD-26). CI construye la imagen del backend y `--target build` del frontend. La imagen de producción que incluye `dist` dentro del backend es trabajo de C-20; la alternativa en una VM (Q-29) usa ese mismo servicio único. `.dockerignore` en cada carpeta excluye `.env`, `secrets/`, `node_modules/`, `.venv/` y `.git/`. Imágenes con versión fija (`postgres:17`, `redis:7-alpine`, `axllent/mailpit:<tag>`; **supuesto**: versiones exactas se fijan al implementar). La imagen de PostgreSQL es la de Debian y no la de Alpine: Alpine usa musl y Neon usa glibc, y el orden de las cadenas con la intercalación por defecto puede diferir entre las dos.

### D12. Frontend mínimo
Vite + React + TypeScript (`strict: true`, sin `any`), Vitest con `jsdom` y Testing Library. Una página `App` que muestra el título del sistema en español; su test es la prueba de humo del toolchain. Carpetas de la KB 08 (`app/`, `components/atoms…templates`, `features/`, `pages/`, `services/`, `shared/`) creadas solo cuando tienen contenido, para no versionar directorios vacíos con `.gitkeep` innecesarios; **excepción**: el backend sí crea los paquetes de capas con `__init__.py` porque el scope de C-01 los nombra.

### D13. CI en GitHub Actions
`.github/workflows/ci.yml` con jobs `backend` (servicio PostgreSQL, `TEST_DATABASE_URL`, `pytest` completo, que no necesita otras variables porque la aplicación no se construye al importar (D6), `alembic upgrade head` sobre base vacía, chequeo de heads), `frontend` (`npm ci`, `tsc --noEmit`, `vitest run`, `vite build`), `images` (crea `.env` desde `.env.example` si no existe y los secretos con `scripts/dev_secrets.sh`; `docker compose config --quiet`, `docker build` del backend y `docker build --target build` del frontend) y `compose-smoke` (`scripts/smoke_compose.sh`, D10, que crea su propio `.env`). El repositorio está en GitHub: Actions es gratuito para repositorios públicos y tiene cuota gratuita en privados.

## Risks / Trade-offs

- [Q-26: el proveedor publicado no permite `CREATE EXTENSION btree_gist` con el usuario de la app] → Afecta solo al despliegue publicado y se resuelve antes de C-20; no bloquea este change. En local y CI no aplica (superusuario del contenedor). Para Neon se valida en el spike de infraestructura; si falla, se habilita desde la consola y la migración sigue siendo idempotente (`IF NOT EXISTS`).
- [Q-29: se exige el stack completo en una VM] → Afecta solo al despliegue publicado y se resuelve antes de C-20. El mismo Compose sirve, con el servicio único de DD-26 (la API sirve el frontend compilado). No cambia este change.
- [Salud sin base puede reportar "ok" con la base caída] → Aceptado (D3). La API devuelve errores en los endpoints que usan la base; C-20 puede sumar una ruta de readiness.
- [Divergencia con la skill de Compose (`compose.yaml`) y de Alembic (runner síncrono)] → Documentado en D1 y D7; prevalece el proyecto.
- [Versiones nuevas no fijadas por la KB] → Se fijan al implementar y se registran en `pyproject.toml` con `uv.lock`, en `package-lock.json` y en los `FROM`; se conservan las dependencias ya bloqueadas de C-00 salvo un ajuste necesario para incorporar C-01. `uv` es gratuito y solo se usa para resolver e instalar dependencias.
- [La contraseña local de la base figura en dos archivos de secreto] → `postgres_password.txt` la necesita el contenedor de PostgreSQL y `database_url.txt` la API. Los genera un único script a partir de un mismo valor (D10). Solo ocurre en local; en producción existe solo la cadena de Neon.
- [Tiempo de sesión] → Alcance limitado a lo que nombra `CHANGES.md`; el frontend es solo humo.

## Migration Plan

1. Tomar como base C-00 y verificar sus pruebas antes de modificar código en apply. Ampliar dependencias y estructura sin reemplazarlas; adaptar la lectura de conexión de Alembic a D7.
2. Aplicar `alembic upgrade head` en el entorno local. Sin DDL nuevo, el head sigue siendo `0001_turnos_sin_solapamiento`; una base vacía recibe el esquema completo de C-00 y una base ya migrada lo conserva sin cambios.
3. Revertir C-01 restaurando su configuración y componentes añadidos, sin eliminar archivos de C-00 ni ejecutar `alembic downgrade base` sobre una base existente. Si hubiera una revisión descendiente por DDL real, su reversión se detiene en la revisión de C-00 y conserva sus tablas, datos y restricción.
4. Reservar `alembic downgrade base` para las pruebas de historia completa en bases temporales propias: esas pruebas verifican que la extensión permanece y luego reaplican la historia. La limpieza `down -v` del smoke test afecta solo al proyecto descartable de D10, nunca al volumen de desarrollo habitual.

## Open Questions

- Versión exacta de PostgreSQL local para coincidir con Neon (17 es el supuesto); se resuelve al implementar sin cambiar specs ni tareas.
