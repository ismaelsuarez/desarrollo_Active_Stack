# Spec Delta

## Purpose

Define el contrato del entorno local con Docker Compose: qué servicios existen, cómo se ordenan al arrancar, cómo reciben configuración y secretos, y qué queda fuera del control de versiones.

## ADDED Requirements

### Requirement: Archivo de Compose válido y sin clave version
El archivo `docker-compose.yml` SHALL validar con `docker compose config --quiet` y MUST NOT declarar la clave de nivel superior `version`.

#### Scenario: Validación
- **WHEN** se ejecuta `docker compose config --quiet` con los archivos de secreto de ejemplo presentes y `.env` creado a partir de `.env.example`
- **THEN** termina con código 0

#### Scenario: Sin clave version
- **WHEN** se inspecciona el nivel superior de `docker-compose.yml`
- **THEN** no existe la clave `version`

### Requirement: Servicios del entorno local
El entorno local SHALL definir exactamente los servicios `db`, `migrate`, `api`, `frontend`, `redis` y `mailpit`, y MUST NOT definir un servicio `worker` ni otro trabajador de aplicación separado de la API; esto no prohíbe los servicios de base de datos, frontend y auxiliares declarados.

#### Scenario: Conjunto de servicios
- **WHEN** se listan los servicios de `docker-compose.yml`
- **THEN** son `db`, `migrate`, `api`, `frontend`, `redis` y `mailpit`

### Requirement: Base de datos persistente y con healthcheck
El servicio `db` SHALL usar la imagen oficial de PostgreSQL con versión fija, guardar sus datos en un volumen con nombre, no publicar el puerto 5432 en el host por defecto y declarar un healthcheck con `pg_isready`.

#### Scenario: Volumen y healthcheck
- **WHEN** se inspecciona el servicio `db`
- **THEN** monta un volumen con nombre en el directorio de datos de PostgreSQL
- **AND** su healthcheck invoca `pg_isready`

### Requirement: Migración previa a la API
El servicio `migrate` SHALL ejecutar `alembic upgrade head` y terminar, y arrancar solo cuando `db` está saludable; el servicio `api` SHALL arrancar solo cuando `migrate` terminó con éxito.

#### Scenario: Orden de arranque
- **WHEN** se inspeccionan las dependencias
- **THEN** `migrate` depende de `db` con `condition: service_healthy`
- **AND** `api` depende de `migrate` con `condition: service_completed_successfully`

#### Scenario: Migración ejecutada
- **WHEN** se ejecuta `docker compose up` sobre un volumen vacío
- **THEN** `migrate` termina con código 0 y `api` queda en estado saludable
- **AND** el proceso de `api` no corre como root

### Requirement: API resiliente con healthcheck
El servicio `api` SHALL declarar `restart: unless-stopped` y un healthcheck que consulta `/api/v1/health`; el servicio `frontend` SHALL depender de `api` con `condition: service_healthy`.

#### Scenario: Healthcheck de la API
- **WHEN** se inspecciona el servicio `api`
- **THEN** su política de reinicio es `unless-stopped` y su healthcheck consulta `/api/v1/health`

### Requirement: Servicios auxiliares bajo perfiles
`redis` MUST pertenecer únicamente al perfil `redis` y `mailpit` únicamente al perfil `dev`, de modo que `docker compose up` sin perfiles no los inicie y ningún servicio sin perfil dependa de ellos.

#### Scenario: Arranque sin perfiles
- **WHEN** se ejecuta `docker compose config --services` sin perfiles activos
- **THEN** la lista no incluye `redis` ni `mailpit`

#### Scenario: Perfil dev
- **WHEN** se activa el perfil `dev`
- **THEN** `mailpit` queda incluido y expone su interfaz web en el puerto 8025

### Requirement: Verificación de arranque aislada
La verificación local y de CI SHALL usar un proyecto Compose descartable con identidad y volúmenes propios nuevos. Su limpieza MUST eliminar únicamente esos recursos; MUST NOT reutilizar ni eliminar los volúmenes del entorno de desarrollo habitual.

#### Scenario: Entorno de prueba vacío
- **WHEN** se ejecuta `scripts/smoke_compose.sh`
- **THEN** el arranque usa un proyecto descartable con volúmenes propios nuevos
- **AND** las comprobaciones y la limpieza usan la misma identidad de proyecto

#### Scenario: Volúmenes de desarrollo existentes
- **GIVEN** volúmenes persistentes del entorno de desarrollo habitual
- **WHEN** termina la verificación de arranque y limpia su proyecto descartable
- **THEN** elimina solo los contenedores y volúmenes de la prueba
- **AND** los volúmenes habituales y sus datos permanecen intactos

### Requirement: Secretos como archivos montados y no versionados
Los valores sensibles SHALL llegar a los contenedores como secretos de Compose montados en `/run/secrets/<nombre>` desde la carpeta `secrets/`, nunca por `env_file` ni por `environment`; `secrets/` y `.env` MUST quedar excluidos de Git, y `.env.example` MUST listar solo variables no sensibles. Cada servicio SHALL recibir únicamente los secretos que usa: `db` recibe `postgres_password`, `migrate` recibe `database_url` y `api` recibe `database_url` y `jwt_secret_key`.

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
