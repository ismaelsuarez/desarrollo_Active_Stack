# professional-schedules Specification

## Purpose

Configura boxes, profesionales y ventanas recurrentes o excepcionales que determinan cuándo cada agenda del consultorio puede atender.

## Requirements

### Requirement: Cada profesional usa un box exclusivo
El consultorio MUST permitir al administrador gestionar boxes y perfiles profesionales; cada profesional tiene un box fijo y ningún box se asigna a más de un profesional.

#### Scenario: Box ya asignado
- **GIVEN** un box ya asignado a un profesional activo
- **WHEN** se intenta asignarlo a otro profesional
- **THEN** la operación se rechaza y conserva la asignación existente

#### Scenario: Desactivar profesional
- **WHEN** el administrador desactiva un profesional
- **THEN** deja de estar disponible para nuevas operaciones y su historial queda conservado

### Requirement: Horario semanal contiene bloques no superpuestos
El administrador MUST poder reemplazar el horario semanal de un profesional con uno o más bloques por día; cada bloque pertenece a un día válido, termina después de empezar y no se superpone con otro bloque del mismo profesional y día.

#### Scenario: Jornada partida
- **WHEN** el administrador guarda bloques de mañana y tarde sin intersección
- **THEN** ambos bloques quedan asociados al profesional y consultorio correctos

#### Scenario: Bloques superpuestos
- **WHEN** dos bloques del mismo día se superponen parcialmente o por completo
- **THEN** la solicitud se rechaza y el horario previo permanece intacto

### Requirement: Excepciones bloquean una agenda local
El administrador MUST poder registrar, listar y eliminar excepciones `feriado`, `vacaciones`, `ausencia` o `bloqueo`; una excepción sin profesional aplica a todas las agendas del consultorio y sus instantes se interpretan en la zona del consultorio.

#### Scenario: Feriado del consultorio
- **WHEN** se crea un feriado sin profesional para un intervalo válido
- **THEN** queda asociado al consultorio y representa ese mismo intervalo local para todas sus agendas

#### Scenario: Intervalo inválido o profesional ajeno
- **WHEN** el fin no es posterior al inicio o el profesional pertenece a otro consultorio
- **THEN** la API rechaza el bloqueo y no crea registros

### Requirement: Bloquear períodos ocupados exige resolver turnos
Cuando una excepción se solapa con turnos existentes, el sistema MUST devolver los turnos afectados y exigir que se resuelvan antes de guardar el bloqueo; no cancela ni reprograma turnos en silencio.

#### Scenario: Período sin turnos
- **WHEN** el administrador crea un bloqueo que no coincide con turnos existentes
- **THEN** el bloqueo se guarda

#### Scenario: Período con turnos
- **WHEN** el administrador crea un bloqueo sobre uno o más turnos existentes
- **THEN** la solicitud informa los turnos afectados, no guarda el bloqueo y deja los turnos sin cambios
