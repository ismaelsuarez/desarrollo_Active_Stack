# Proposal: C-06 agenda-config

## Why

El consultorio todavía no puede configurar en el sistema quién atiende, en qué box y en qué horarios; tampoco puede registrar prestaciones ni adaptar los parámetros de reserva y liberación. Sin esa configuración, la agenda operativa y la disponibilidad que consumirán C-07 y C-09 no tienen una fuente confiable.

## What Changes

- Administrar cuentas del personal: crear, editar y desactivar usuarios con un único rol no paciente; impedir que desactivar borre su historial. Asociar profesionales de agenda a cuentas `profesional` o `administrador`.
- Administrar boxes y profesionales: un box fijo por profesional y sin compartir; conservar referencias históricas al desactivar.
- Configurar varios bloques semanales por día, con validación de intervalos y rechazo de superposiciones.
- Crear, listar y eliminar excepciones de agenda para un profesional o para todo el consultorio; los intervalos se interpretan en la zona horaria del consultorio y no se eliminan turnos en silencio.
- Mantener un catálogo inicial editable de nueve prestaciones; los cambios de duración solo rigen para turnos futuros.
- Permitir consultar y actualizar los parámetros de agenda/liberación del consultorio, incluidos granularidad, anticipación máxima, cantidad máxima de turnos activos y teléfono, validando los mismos límites en API y base.
- Agregar la migración lineal y la semilla repetible para estas entidades y el catálogo.

## Capabilities

### New Capabilities
- `staff-management`: administración de cuentas del personal y asociación de roles a profesionales de agenda.
- `professional-schedules`: boxes, profesionales, horarios semanales y excepciones que bloquean la agenda.
- `service-catalog`: catálogo de prestaciones, activación y duraciones sugeridas.
- `clinic-agenda-settings`: parámetros de agenda y liberación configurables por consultorio.

### Modified Capabilities
- `core-data-models`: agregar entidades e integridad de box, profesional, horarios, bloqueos y prestaciones; precisar los parámetros existentes del consultorio.
- `database-seeding`: extender la inicialización repetible con el catálogo de prestaciones, sin modificar datos existentes.

## Impact

- **Backend/API**: nuevas rutas de personal, boxes, profesionales, horarios, bloqueos, prestaciones y configuración del consultorio; restricciones de escritura con RBAC de Administrador y `consultorio_id` siempre desde `Principal`.
- **Datos**: una revisión Alembic descendiente del único head `0006_intento_registro`; validación en PostgreSQL real.
- **Semilla y documentación**: catálogo de nueve prestaciones con duraciones explícitamente sugeridas, README y `.env.example` solo si aparecen variables nuevas.
- **Gobernanza**: MEDIA. Q-09, Q-12 y Q-13 permanecen como decisiones medias no bloqueantes: las duraciones son sugeridas, solo Administrador gestiona configuración en C-06 y los feriados se cargan manualmente.
