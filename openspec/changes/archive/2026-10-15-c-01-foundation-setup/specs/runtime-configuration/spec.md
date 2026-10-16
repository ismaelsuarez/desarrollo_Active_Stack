# Spec Delta

## Purpose

Define de dónde obtiene la API su configuración (variables de entorno o archivos de secreto montados), qué valores son obligatorios y cómo falla cuando faltan, para que ningún entorno arranque mal configurado.

## ADDED Requirements

### Requirement: Arranque rechazado sin configuración obligatoria
La API MUST negarse a arrancar cuando falta `APP_ENV`, `DATABASE_URL` o `JWT_SECRET_KEY`, con un error que nombra cada variable faltante y no muestra valores de ninguna variable. Ninguna de las tres tiene valor por defecto, para que un entorno mal configurado no arranque en modo de desarrollo.

#### Scenario: Falta DATABASE_URL
- **WHEN** la API arranca sin `DATABASE_URL` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `DATABASE_URL`

#### Scenario: Falta JWT_SECRET_KEY
- **WHEN** la API arranca con `DATABASE_URL` pero sin `JWT_SECRET_KEY` en el entorno ni en archivo de secreto
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `JWT_SECRET_KEY` y no contiene el valor de `DATABASE_URL`

#### Scenario: Falta APP_ENV
- **WHEN** la API arranca con `DATABASE_URL` y `JWT_SECRET_KEY` pero sin `APP_ENV`
- **THEN** el arranque falla
- **AND** el mensaje de error menciona `APP_ENV`

#### Scenario: Configuración completa
- **WHEN** la API arranca con `APP_ENV`, `DATABASE_URL` y `JWT_SECRET_KEY` válidos
- **THEN** el arranque termina sin error

### Requirement: Longitud mínima de la clave de firma
La configuración MUST rechazar, en cualquier entorno, una `JWT_SECRET_KEY` de menos de 32 bytes (el mínimo de HS256), con un error que nombra la variable y no muestra su valor.

#### Scenario: Clave corta
- **WHEN** la API arranca con una `JWT_SECRET_KEY` de 31 bytes
- **THEN** el arranque falla con un error que menciona `JWT_SECRET_KEY`
- **AND** el mensaje no contiene el valor de la clave

#### Scenario: Clave de longitud mínima
- **WHEN** la API arranca con una `JWT_SECRET_KEY` de 32 bytes y el resto de la configuración obligatoria
- **THEN** el arranque termina sin error

### Requirement: Valores leídos desde archivos de secreto
La configuración SHALL aceptar cada valor sensible desde un archivo de secreto en el directorio de secretos (por defecto `/run/secrets`), cuyo nombre es el de la variable en minúsculas (por ejemplo `jwt_secret_key`). Una variable de entorno definida tiene prioridad sobre el archivo. Se descartan los espacios y saltos de línea finales del archivo.

#### Scenario: Secreto solo en archivo
- **GIVEN** el resto de la configuración obligatoria es válido
- **WHEN** `JWT_SECRET_KEY` no está en el entorno y el archivo `jwt_secret_key` del directorio de secretos contiene `archivo-secreto-de-prueba-0123456789\n`
- **THEN** la configuración expone `JWT_SECRET_KEY` con el valor `archivo-secreto-de-prueba-0123456789`

#### Scenario: Entorno y archivo a la vez
- **GIVEN** el resto de la configuración obligatoria es válido
- **WHEN** `JWT_SECRET_KEY` está en el entorno con `entorno-secreto-de-prueba-0123456789` y el archivo `jwt_secret_key` contiene `archivo-secreto-de-prueba-0123456789`
- **THEN** la configuración expone `entorno-secreto-de-prueba-0123456789`

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
La configuración SHALL usar `APP_TIMEZONE=America/Argentina/Buenos_Aires` cuando no se define, y MUST rechazar un `APP_ENV` distinto de `development`, `test` o `production`.

#### Scenario: Zona horaria por defecto
- **WHEN** la API arranca con la configuración obligatoria y sin `APP_TIMEZONE`
- **THEN** la configuración expone `America/Argentina/Buenos_Aires`

#### Scenario: Entorno inválido
- **WHEN** la API arranca con `APP_ENV=staging`
- **THEN** el arranque falla con un error que menciona `APP_ENV`

### Requirement: Configuración de base de datos separada para las migraciones
La configuración de conexión a la base SHALL poder cargarse sin el resto de la configuración de la API, de modo que el proceso de migraciones no necesite `JWT_SECRET_KEY` ni ningún otro secreto ajeno a la base. Las migraciones SHALL usar `MIGRATIONS_DATABASE_URL` cuando está definida y `DATABASE_URL` en otro caso; `MIGRATIONS_DATABASE_URL` es opcional y sensible, y existe para apuntar a la conexión directa cuando `DATABASE_URL` pasa por un pooler.

#### Scenario: Migraciones sin secretos de la API
- **WHEN** se carga la configuración de base de datos con `DATABASE_URL` definido y sin `APP_ENV` ni `JWT_SECRET_KEY`
- **THEN** la carga termina sin error

#### Scenario: URL propia de migraciones
- **WHEN** `DATABASE_URL` y `MIGRATIONS_DATABASE_URL` están definidas con valores distintos
- **THEN** la URL de migraciones es la de `MIGRATIONS_DATABASE_URL`

#### Scenario: Sin URL propia de migraciones
- **WHEN** solo `DATABASE_URL` está definida
- **THEN** la URL de migraciones es la de `DATABASE_URL`
