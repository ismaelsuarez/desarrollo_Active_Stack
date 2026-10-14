# Proposal: C-00 crear-turno-sin-solapamientos

## Why

Que un profesional no tenga dos turnos superpuestos es la regla central del sistema (RN-17) y el vacío del mercado argentino que identificó el Discovery (`docs/discovery/informe-discovery.md`, sección D.3). Hoy el repositorio no tiene código, así que esa regla no existe en ningún lado: este change la entrega completa, especificada y probada contra PostgreSQL real, como único change de la primera parte de la entrega (DD-33).

## What Changes

- Caso de uso para crear un turno de un paciente con un profesional y una prestación, en un consultorio dado. El turno nace en estado `pendiente`.
- La duración del turno es la de la prestación elegida: `fin = inicio + duración` (RN-13).
- Un turno que se superpone con otro turno activo del mismo profesional se rechaza con el error de dominio "horario ocupado" y no se guarda (RN-17).
- El rango del turno es semiabierto, `[inicio, fin)`: un turno que empieza justo cuando termina otro se acepta.
- Los turnos `cancelado` y `liberado` no ocupan el hueco (RN-17, RN-22).
- Dos creaciones simultáneas del mismo horario dejan un solo turno; la otra recibe "horario ocupado" (RN-24). La garantía la da la base de datos con una restricción de exclusión (DD-08), no una validación previa de la aplicación.
- Tablas mínimas `profesional`, `prestacion` y `turno` con clave primaria `bigint` con identidad (DD-23), y la restricción `turno_sin_solapamiento` con el predicado completo de `knowledge-base/04_modelo_de_datos.md` §turno.
- Andamiaje mínimo para ejecutar las pruebas: proyecto Python en `backend/` con las capas de `knowledge-base/08_arquitectura_propuesta.md`, Alembic asíncrono con una migración y pytest contra PostgreSQL real.

Fuera de alcance (otros changes):

- **RN-14**: el turno dentro del horario semanal del profesional y fuera de sus excepciones, y la grilla de inicio de RN-64 (C-06 y C-07). Consecuencia aceptada: hasta entonces se puede crear un turno fuera del horario de atención.
- Sobreturnos (RN-39 a RN-43): la columna `es_sobreturno` existe y vale `false`; ningún caso de uso de este change la pone en `true` (C-12).
- Cancelar, reprogramar, confirmar y liberar turnos, y el resto de las transiciones de RN-18 (C-07, C-08, C-16).
- Autenticación, autorización, API HTTP y pantallas (C-03, C-04, C-07, C-11).
- Tablas `consultorio`, `paciente`, `box` y `usuario` (C-02); hitos de confirmación, `origen` e historial del turno (C-07, C-15).
- Docker Compose, configuración de la aplicación, logging y CI (C-01).

Supuestos de este change, a revisar:

- `consultorio_id` entra como dato del caso de uso. Sin autenticación no existe un `Principal` de donde leerlo; la regla dura 1 se cumple cuando C-03 conecte el token.
- Dos profesionales distintos pueden tener turnos en el mismo horario: la regla es por profesional (y por su box fijo, RN-10).
- El turno nace siempre `pendiente`. El caso del turno creado con poca anticipación, que nace `confirmado` (DD-32), llega con los hitos de confirmación.

## Capabilities

### New Capabilities

- `appointment-booking`: creación de turnos de un profesional con la garantía de que dos turnos activos del mismo profesional nunca se superponen.

### Modified Capabilities

Ninguna: el proyecto todavía no tiene especificaciones archivadas.

## Impact

- **Código nuevo**: `backend/app/domain`, `backend/app/application`, `backend/app/infrastructure/db`, `backend/alembic/` y `backend/tests/`. No hay código previo que se modifique.
- **Base de datos**: extensión `btree_gist`, tipo enumerado del estado del turno, tablas `profesional`, `prestacion` y `turno`, y la restricción de exclusión `turno_sin_solapamiento`. Es la primera revisión de Alembic del proyecto.
- **Dependencias** (todas gratuitas, regla dura 14): SQLAlchemy 2.x asíncrono, asyncpg y Alembic; para desarrollo, pytest y pytest-asyncio.
- **Entorno**: las pruebas de integración exigen un PostgreSQL real accesible por `TEST_DATABASE_URL`.
- **Relación con la segunda parte**: es una rebanada de C-07 con la base mínima de C-01 y C-02. Esos changes reutilizan la estructura, agregan las claves foráneas que faltan y absorben la migración; el diseño de `c-01-foundation-setup` debe rebasar su migración base sobre la de este change para conservar un único head (regla dura 8).
- **Documentación**: sección del `README.md` con los comandos para levantar PostgreSQL y correr las pruebas.
