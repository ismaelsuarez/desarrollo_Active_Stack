# Spec Delta

## Purpose

Define de dónde obtiene la API su configuración (variables de entorno o archivos de secreto montados), qué valores son obligatorios y cómo falla cuando faltan, para que ningún entorno arranque mal configurado.

## ADDED Requirements

### Requirement: Arranque rechazado sin configuración obligatoria
La API MUST negarse a arrancar cuando falta `DATABASE_URL` o `JWT_SECRET_KEY`, con un error que nombra cada variable faltante y no muestra valores de ninguna variable.

#### Scenario: Falta DATABASE_URL
- **WHEN** la API arranca sin `DATABASE_URL` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `DATABASE_URL`

#### Scenario: Falta JWT_SECRET_KEY
- **WHEN** la API arranca con `DATABASE_URL` pero sin `JWT_SECRET_KEY` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `JWT_SECRET_KEY` y no contiene el valor de `DATABASE_URL`

#### Scenario: Configuración completa
- **WHEN** la API arranca con `DATABASE_URL` y `JWT_SECRET_KEY` definidos
- **THEN** el arranque termina sin error

### Requirement: Valores leídos desde archivos de secreto
La configuración SHALL aceptar cada valor sensible desde un archivo de secreto en el directorio de secretos (por defecto `/run/secrets`), cuyo nombre es el de la variable en minúsculas (por ejemplo `jwt_secret_key`). Una variable de entorno definida tiene prioridad sobre el archivo. Se descartan los espacios y saltos de línea finales del archivo.

#### Scenario: Secreto solo en archivo
- **WHEN** `JWT_SECRET_KEY` no está en el entorno y el archivo `jwt_secret_key` del directorio de secretos contiene `valor-de-prueba\n`
- **THEN** la configuración expone `JWT_SECRET_KEY` con el valor `valor-de-prueba`

#### Scenario: Entorno y archivo a la vez
- **WHEN** `JWT_SECRET_KEY` está en el entorno con `desde-entorno` y el archivo `jwt_secret_key` contiene `desde-archivo`
- **THEN** la configuración expone `desde-entorno`

#### Scenario: Directorio de secretos inexistente
- **WHEN** el directorio de secretos no existe y las variables obligatorias están en el entorno
- **THEN** el arranque termina sin error

### Requirement: Redis es opcional
La configuración MUST tratar `REDIS_URL` como opcional: su ausencia no impide el arranque ni habilita ningún comportamiento que dependa de Redis.

#### Scenario: Sin REDIS_URL
- **WHEN** la API arranca con la configuración obligatoria y sin `REDIS_URL`
- **THEN** el arranque termina sin error
- **AND** la configuración informa que Redis no está configurado

### Requirement: Valores por defecto de operación
La configuración SHALL usar `APP_ENV=development` y `APP_TIMEZONE=America/Argentina/Buenos_Aires` cuando no se definen, y MUST rechazar un `APP_ENV` distinto de `development`, `test` o `production`.

#### Scenario: Valores por defecto
- **WHEN** la API arranca sin `APP_ENV` ni `APP_TIMEZONE`
- **THEN** la configuración expone `development` y `America/Argentina/Buenos_Aires`

#### Scenario: Entorno inválido
- **WHEN** la API arranca con `APP_ENV=staging`
- **THEN** el arranque falla con un error que menciona `APP_ENV`
