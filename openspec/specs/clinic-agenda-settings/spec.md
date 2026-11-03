# clinic-agenda-settings Specification

## Purpose

Permite al Administrador adaptar el modo de liberación y los límites de reserva de un consultorio para que API y datos persistidos usen la misma configuración.

## Requirements

### Requirement: Administrador consulta y actualiza parámetros de agenda
La API MUST permitir al Administrador leer y actualizar el modo de liberación, plazos operativos, teléfono, granularidad de inicio, anticipación máxima y máximo de turnos activos del consultorio autenticado.

#### Scenario: Actualización válida
- **WHEN** el administrador actualiza valores dentro de los límites del consultorio
- **THEN** la respuesta y la configuración persistida muestran esos valores

#### Scenario: Otro rol intenta escribir
- **WHEN** un usuario que no es administrador intenta actualizar la configuración
- **THEN** la API responde 403 y conserva los valores previos

### Requirement: Valores de agenda respetan límites comunes
La API MUST rechazar configuraciones inválidas con 422 y la base MUST impedir los mismos valores inválidos mediante sus restricciones `CHECK`.

#### Scenario: Granularidad fuera de rango
- **WHEN** se intenta guardar granularidad menor a 5 o mayor a 120, anticipación menor a 1 o máximo de turnos menor a 1
- **THEN** la API responde 422 y la configuración previa permanece

#### Scenario: Plazos o modo inválidos
- **WHEN** se intenta guardar plazos cuyo orden viola confirmación > recordatorio > liberación > 0, límite de paciente no positivo o modo distinto de `automatico`/`manual`
- **THEN** la API responde 422 sin persistir cambios
