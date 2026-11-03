# Spec Delta

## ADDED Requirements

### Requirement: Modelos de agenda aíslan las entidades por consultorio
Las tablas `box`, `profesional`, `horario_semanal`, `bloqueo_agenda` y `prestacion` MUST usar claves primarias `bigint` identity, clave foránea a consultorio e índice de `consultorio_id`.

#### Scenario: Entidad de agenda sin consultorio
- **WHEN** se intenta insertar una entidad de agenda con consultorio nulo o inexistente
- **THEN** PostgreSQL rechaza la escritura por integridad referencial

### Requirement: Box y profesional conservan asociaciones exclusivas
La persistencia MUST exigir nombres de box únicos por consultorio, `UNIQUE (profesional.usuario_id)` y `UNIQUE (profesional.box_id)`; la asociación de box y cuenta MUST pertenecer al mismo consultorio.

#### Scenario: Dos profesionales comparten box
- **WHEN** se intenta persistir un segundo profesional en un box ya asignado
- **THEN** PostgreSQL rechaza la operación por unicidad

#### Scenario: Asociación entre consultorios
- **WHEN** un profesional se asocia a un box de otro consultorio
- **THEN** la escritura es rechazada por la integridad del esquema

### Requirement: Bloques semanales y prestaciones tienen límites estructurales
La base MUST exigir día semanal entre 1 y 7, `hora_inicio < hora_fin`, duraciones de prestación positivas y unicidad de nombre por consultorio.

#### Scenario: Bloque u oferta inválidos
- **WHEN** se intenta guardar día inválido, horas invertidas, duración no positiva o nombre repetido
- **THEN** PostgreSQL rechaza la escritura

### Requirement: Bloqueo de agenda tiene intervalo y tipo válidos
La base MUST exigir `inicio < fin`, tipo en `feriado`, `vacaciones`, `ausencia` o `bloqueo`, profesional opcional y actor creador asociado a una cuenta.

#### Scenario: Bloqueo global válido
- **WHEN** se persiste un feriado con profesional nulo y un intervalo creciente
- **THEN** PostgreSQL conserva el bloqueo global del consultorio

#### Scenario: Bloqueo inválido
- **WHEN** se persiste un bloqueo de tipo no permitido o un intervalo vacío
- **THEN** PostgreSQL rechaza la operación por `CHECK`

### Requirement: Parámetros de agenda se validan en PostgreSQL
La tabla `consultorio` MUST hacer cumplir granularidad de 5 a 120 minutos, anticipación y máximo de turnos mayores o iguales a 1, el modo permitido y el orden de plazos operativo.

#### Scenario: Parámetros válidos
- **WHEN** se persisten plazos válidos, granularidad 15, anticipación 60 y máximo 2
- **THEN** PostgreSQL acepta la configuración

#### Scenario: Parámetros fuera de contrato
- **WHEN** se persiste granularidad 4, anticipación 0, máximo 0 o modo inválido
- **THEN** PostgreSQL rechaza la configuración
