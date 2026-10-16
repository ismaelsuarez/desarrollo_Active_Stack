# Spec Delta

## Purpose

Versiona el esquema de PostgreSQL con una historia lineal de un único head, aplicable de forma repetible sobre una base vacía, e instala las extensiones que el resto del sistema necesita.

## ADDED Requirements

### Requirement: Migración base con btree_gist
La migración inicial existente de C-00 SHALL conservar la creación idempotente de `btree_gist` (`CREATE EXTENSION IF NOT EXISTS btree_gist`), requisito de la restricción de no solapamiento de turnos.

#### Scenario: Base vacía
- **WHEN** se aplica `alembic upgrade head` sobre una base PostgreSQL vacía
- **THEN** el comando termina con código 0
- **AND** `btree_gist` figura en `pg_extension`

#### Scenario: Aplicación repetida
- **WHEN** se aplica `alembic upgrade head` dos veces seguidas sobre la misma base
- **THEN** ambas ejecuciones terminan con código 0 y la versión registrada es la misma

#### Scenario: Extensión ya instalada
- **WHEN** la base ya tiene `btree_gist` instalada antes de la primera migración
- **THEN** `alembic upgrade head` termina con código 0

#### Scenario: Reversión de la migración base
- **GIVEN** una base temporal propia y descartable, sin datos ajenos a la prueba
- **WHEN** se ejecuta `alembic downgrade base` después de `alembic upgrade head`
- **THEN** el comando termina con código 0
- **AND** `btree_gist` sigue en `pg_extension`, porque la extensión pudo existir antes de la migración

### Requirement: Conservación del esquema existente
C-01 MUST conservar el esquema y los datos entregados por C-00, incluida la restricción de no solapamiento. Sin cambios de esquema se mantiene el head existente; cualquier revisión necesaria SHALL ser descendiente del único head vigente, nunca otra raíz. Revertir C-01 MUST NOT eliminar el esquema ni los datos de C-00.

#### Scenario: Base ya migrada por C-00
- **GIVEN** una base con la migración de C-00 aplicada y un turno guardado
- **WHEN** se aplica `alembic upgrade head` con la configuración de C-01
- **THEN** el turno y la restricción de no solapamiento permanecen
- **AND** la historia conserva un único head

#### Scenario: Sin cambios de esquema
- **WHEN** C-01 modifica configuración sin agregar DDL
- **THEN** se conserva el head `0001_turnos_sin_solapamiento` sin crear una revisión vacía

#### Scenario: Reversión de C-01
- **GIVEN** una base que conserva datos de C-00 después de aplicar C-01
- **WHEN** se revierte únicamente C-01
- **THEN** la base conserva las tablas, los datos y la restricción de C-00
- **AND** no se ejecuta `alembic downgrade base` sobre esa base

### Requirement: Migraciones solo con upgrade head
Las migraciones MUST aplicarse con `alembic upgrade head`; ningún script, servicio ni documentación del proyecto usa `upgrade heads`.

#### Scenario: Servicio de migración
- **WHEN** se inspecciona el comando del servicio que aplica migraciones
- **THEN** el comando es `alembic upgrade head`

### Requirement: Historia con un único head
El proyecto SHALL ofrecer un chequeo ejecutable que termina con código 0 cuando la historia de migraciones tiene exactamente un head, y con código distinto de 0, listando los heads encontrados, cuando tiene más de uno.

#### Scenario: Un único head
- **WHEN** se ejecuta el chequeo sobre una historia lineal
- **THEN** termina con código 0

#### Scenario: Dos revisiones con el mismo padre
- **WHEN** se ejecuta el chequeo sobre una historia con dos revisiones que tienen el mismo padre
- **THEN** termina con código distinto de 0
- **AND** la salida menciona los identificadores de ambas revisiones

### Requirement: Conexión de migraciones desde la configuración
Las migraciones MUST obtener la conexión de la configuración de base de datos (entorno o archivo de secreto): `MIGRATIONS_DATABASE_URL` cuando está definida y `DATABASE_URL` en otro caso. MUST NOT contener credenciales en archivos versionados ni requerir secretos ajenos a la base.

#### Scenario: URL desde el entorno
- **WHEN** se ejecuta `alembic upgrade head` con `DATABASE_URL` apuntando a una base de prueba
- **THEN** la migración se aplica sobre esa base

#### Scenario: Migración sin secretos de la API
- **WHEN** se ejecuta `alembic upgrade head` con `DATABASE_URL` definida y sin `JWT_SECRET_KEY` ni `APP_ENV`
- **THEN** el comando termina con código 0

#### Scenario: Archivo de configuración sin credenciales
- **WHEN** se inspecciona el archivo de configuración de Alembic versionado
- **THEN** no contiene una URL de conexión con usuario y contraseña
