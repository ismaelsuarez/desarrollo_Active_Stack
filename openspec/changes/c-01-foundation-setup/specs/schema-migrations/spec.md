# Spec Delta

## Purpose

Versiona el esquema de PostgreSQL con una historia lineal de un único head, aplicable de forma repetible sobre una base vacía, e instala las extensiones que el resto del sistema necesita.

## ADDED Requirements

### Requirement: Migración base con btree_gist
La primera migración del esquema SHALL dejar instalada la extensión `btree_gist` mediante una creación idempotente (`CREATE EXTENSION IF NOT EXISTS btree_gist`), requisito de la restricción de no solapamiento de turnos.

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
Las migraciones MUST obtener la conexión de `DATABASE_URL` de la configuración de la aplicación (entorno o archivo de secreto) y MUST NOT contener credenciales en archivos versionados.

#### Scenario: URL desde el entorno
- **WHEN** se ejecuta `alembic upgrade head` con `DATABASE_URL` apuntando a una base de prueba
- **THEN** la migración se aplica sobre esa base

#### Scenario: Archivo de configuración sin credenciales
- **WHEN** se inspecciona el archivo de configuración de Alembic versionado
- **THEN** no contiene una URL de conexión con usuario y contraseña
