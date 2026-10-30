# Spec Delta: local-environment

## MODIFIED Requirements

### Requirement: Servicios del entorno local
El entorno local SHALL definir exactamente los servicios `db`, `migrate`, `seed`, `api`, `frontend`, `redis` y `mailpit`, y MUST NOT definir un servicio `worker` ni otro trabajador de aplicación separado de la API; esto no prohíbe los servicios de base de datos, inicialización, frontend y auxiliares declarados.

#### Scenario: Conjunto de servicios
- **WHEN** se listan los servicios de `docker-compose.yml`
- **THEN** son `db`, `migrate`, `seed`, `api`, `frontend`, `redis` y `mailpit`

### Requirement: Migración previa a la API
El servicio `migrate` SHALL ejecutar `alembic upgrade head` y terminar, y arrancar solo cuando `db` está saludable; el servicio `seed` SHALL ejecutar `python -m app.seed` y terminar, arrancando solo cuando `migrate` terminó con éxito; el servicio `api` SHALL arrancar solo cuando `seed` terminó con éxito.

#### Scenario: Orden de arranque
- **WHEN** se inspeccionan las dependencias
- **THEN** `migrate` depende de `db` con `condition: service_healthy`
- **AND** `seed` depende de `migrate` con `condition: service_completed_successfully`
- **AND** `api` depende de `seed` con `condition: service_completed_successfully`

#### Scenario: Migración ejecutada
- **WHEN** se ejecuta `docker compose up` sobre un volumen vacío
- **THEN** `migrate` termina con código 0 y `seed` termina con código 0
- **AND** `api` queda en estado saludable y su proceso no corre como root

### Requirement: Secretos como archivos montados y no versionados
Los valores sensibles SHALL llegar a los contenedores como secretos de Compose montados en `/run/secrets/<nombre>` desde la carpeta `secrets/`, nunca por `env_file` ni por `environment`; `secrets/` y `.env` MUST quedar excluidos de Git, y `.env.example` MUST listar solo variables no sensibles. Cada servicio SHALL recibir únicamente los secretos que usa: `db` recibe `postgres_password`, `migrate` recibe `database_url`, `seed` recibe `database_url` y `bootstrap_admin_password`, y `api` recibe `database_url` y `jwt_secret_key`.

#### Scenario: Secretos de la API
- **WHEN** se inspecciona el servicio `api`
- **THEN** recibe `database_url` y `jwt_secret_key` como secretos de Compose
- **AND** ninguna variable sensible aparece con valor literal en `docker-compose.yml`

#### Scenario: Secretos de las migraciones
- **WHEN** se inspecciona el servicio `migrate`
- **THEN** recibe `database_url` como secreto de Compose y no recibe `jwt_secret_key`

#### Scenario: Contraseña de la base
- **WHEN** se inspecciona el servicio `db`
- **THEN** recibe `postgres_password` como secreto de Compose y lo lee con `POSTGRES_PASSWORD_FILE`
- **AND** no define `POSTGRES_PASSWORD`

#### Scenario: Archivos ignorados
- **WHEN** se ejecuta `git check-ignore secrets/jwt_secret_key.txt .env`
- **THEN** ambas rutas figuran como ignoradas

#### Scenario: Ejemplo de entorno
- **WHEN** se inspecciona `.env.example`
- **THEN** incluye `APP_ENV=development` y `APP_TIMEZONE`
- **AND** no incluye `DATABASE_URL`, `JWT_SECRET_KEY` ni `POSTGRES_PASSWORD`

#### Scenario: Arranque sin `.env`
- **WHEN** se ejecuta el arranque verificado (`scripts/smoke_compose.sh`) en una copia limpia sin `.env`
- **THEN** el script crea `.env` a partir de `.env.example`
- **AND** `api` recibe `APP_ENV` y arranca

#### Scenario: Secretos locales generados en un paso
- **WHEN** se ejecuta el script de secretos locales en una copia limpia
- **THEN** existen `secrets/postgres_password.txt`, `secrets/database_url.txt` y `secrets/jwt_secret_key.txt`
- **AND** la contraseña de `database_url.txt` es la de `postgres_password.txt`
- **AND** una segunda ejecución no cambia los archivos existentes
