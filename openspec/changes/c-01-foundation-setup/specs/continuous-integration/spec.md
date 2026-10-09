# Spec Delta

## Purpose

Asegura que todo cambio enviado al repositorio pase, sin costo, las mismas verificaciones mínimas de backend, frontend, imágenes, Compose y migraciones antes de integrarse.

## ADDED Requirements

### Requirement: Verificación en cada cambio
El repositorio SHALL ejecutar automáticamente, en cada push y en cada pull request hacia `main`, un flujo de integración continua gratuito que falla si falla cualquiera de sus pasos.

#### Scenario: Pull request
- **WHEN** se abre o actualiza un pull request hacia `main`
- **THEN** se ejecuta el flujo de integración continua y su resultado queda asociado al pull request

### Requirement: Pruebas de backend contra PostgreSQL real
El flujo MUST ejecutar todas las pruebas del backend, incluidas las de integración, contra un servidor PostgreSQL real; ninguna prueba de integración se omite en CI por falta de base.

#### Scenario: Prueba de integración en CI
- **WHEN** el flujo ejecuta las pruebas del backend
- **THEN** las pruebas de integración se ejecutan contra el PostgreSQL del flujo y ninguna figura como omitida

### Requirement: Migraciones verificadas en CI
El flujo MUST aplicar `alembic upgrade head` sobre una base vacía y ejecutar el chequeo de un único head; un segundo head hace fallar el flujo.

#### Scenario: Dos heads
- **WHEN** un cambio agrega una revisión cuyo padre ya tiene otra revisión hija
- **THEN** el flujo falla en el paso del chequeo de heads

### Requirement: Frontend, imágenes y Compose verificados en CI
El flujo MUST ejecutar las pruebas del frontend, el chequeo de tipos de TypeScript, la compilación de producción del frontend, la construcción de las imágenes de backend y frontend, y la validación de `docker-compose.yml`.

#### Scenario: Error de tipos
- **WHEN** un cambio introduce un error de tipos en el frontend
- **THEN** el flujo falla

#### Scenario: Dockerfile roto
- **WHEN** un cambio impide construir la imagen del backend
- **THEN** el flujo falla
