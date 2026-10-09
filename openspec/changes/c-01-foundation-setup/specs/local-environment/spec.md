# Spec Delta

## Purpose

Define el contrato del entorno local con Docker Compose: qué servicios existen, cómo se ordenan al arrancar, cómo reciben configuración y secretos, y qué queda fuera del control de versiones.

## ADDED Requirements

### Requirement: Archivo de Compose válido y sin clave version
El archivo `docker-compose.yml` SHALL validar con `docker compose config --quiet` y MUST NOT declarar la clave de nivel superior `version`.

#### Scenario: Validación
- **WHEN** se ejecuta `docker compose config --quiet` con los archivos de secreto de ejemplo presentes
- **THEN** termina con código 0

#### Scenario: Sin clave version
- **WHEN** se inspecciona el nivel superior de `docker-compose.yml`
- **THEN** no existe la clave `version`

### Requirement: Servicios del entorno local
El entorno local SHALL definir exactamente los servicios `db`, `migrate`, `api`, `frontend`, `redis` y `mailpit`, y MUST NOT definir un servicio `worker` ni ningún otro proceso persistente aparte de la API.

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

### Requirement: Secretos como archivos montados y no versionados
Los valores sensibles SHALL llegar a los contenedores como secretos de Compose montados en `/run/secrets/<nombre>` desde la carpeta `secrets/`; `secrets/` y `.env` MUST quedar excluidos de Git, y `.env.example` MUST listar las variables sin valores reales.

#### Scenario: Secretos de la API
- **WHEN** se inspecciona el servicio `api`
- **THEN** recibe `jwt_secret_key` como secreto de Compose
- **AND** ninguna variable sensible aparece con valor literal en `docker-compose.yml`

#### Scenario: Archivos ignorados
- **WHEN** se ejecuta `git check-ignore secrets/jwt_secret_key.txt .env`
- **THEN** ambas rutas figuran como ignoradas

#### Scenario: Ejemplo de entorno
- **WHEN** se inspecciona `.env.example`
- **THEN** incluye `DATABASE_URL`, `APP_ENV` y `APP_TIMEZONE`
- **AND** no contiene contraseñas ni claves reales
