# Spec Delta

## Purpose

Permite reservar un turno de un paciente con un profesional y garantiza que dos turnos activos del mismo profesional nunca ocupen el mismo tiempo, incluso cuando dos reservas compiten a la vez.

## ADDED Requirements

### Requirement: Crear un turno en un horario libre
El sistema SHALL crear un turno para un paciente, un profesional y una prestación del mismo consultorio cuando el profesional no tiene otro turno activo en ese horario. El turno creado MUST quedar en estado `pendiente`, no ser sobreturno y registrar el box fijo del profesional (RN-10).

#### Scenario: Turno en un horario libre
- **GIVEN** un profesional sin turnos y una prestación de 30 minutos, ambos del consultorio 1
- **WHEN** se crea un turno para ese profesional con esa prestación e inicio el 2026-11-02 a las 10:00 (hora de Buenos Aires)
- **THEN** el turno queda guardado con un identificador propio y estado `pendiente`
- **AND** el turno no es sobreturno y su box es el box fijo del profesional

#### Scenario: Otro profesional en el mismo horario
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional B, del mismo consultorio, con inicio el 2026-11-02 a las 10:00
- **THEN** el turno del profesional B queda guardado
- **AND** el turno del profesional A no cambia

### Requirement: La duración del turno es la de la prestación
El fin de un turno SHALL ser su inicio más la duración en minutos de la prestación elegida (RN-13). Quien crea el turno no indica el fin.

#### Scenario: Prestación de 30 minutos
- **WHEN** se crea un turno con una prestación de 30 minutos e inicio a las 10:00
- **THEN** el fin del turno es a las 10:30 del mismo día

#### Scenario: Prestación de 60 minutos
- **WHEN** se crea un turno con una prestación de 60 minutos e inicio a las 15:15
- **THEN** el fin del turno es a las 16:15 del mismo día

### Requirement: Rechazar un turno superpuesto del mismo profesional
El sistema MUST rechazar con el error "horario ocupado" la creación de un turno cuyo intervalo comparte algún instante con el de otro turno activo del mismo profesional (RN-17). Son activos los turnos `pendiente`, `confirmado`, `atendido` y `ausente`. Un turno rechazado no se guarda.

#### Scenario: Superposición parcial
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:15 del mismo día
- **THEN** la creación falla con el error "horario ocupado"
- **AND** el profesional A sigue teniendo un único turno ese día

#### Scenario: Mismo horario exacto
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** la creación falla con el error "horario ocupado"

#### Scenario: Turno nuevo que contiene a uno existente
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:15 a 10:45
- **WHEN** se crea un turno del profesional A con una prestación de 60 minutos e inicio a las 10:00 del mismo día
- **THEN** la creación falla con el error "horario ocupado"

### Requirement: Los turnos contiguos no se superponen
El intervalo de un turno SHALL incluir su inicio y excluir su fin. Un turno que empieza en el instante exacto en que termina otro del mismo profesional, o que termina en el instante exacto en que otro empieza, MUST aceptarse.

#### Scenario: Empieza cuando termina otro
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:30 del mismo día
- **THEN** el turno queda guardado de 10:30 a 11:00

#### Scenario: Termina cuando empieza otro
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:30 a 11:00
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno queda guardado de 10:00 a 10:30

### Requirement: Los turnos cancelados y liberados no ocupan el horario
Un turno en estado `cancelado` o `liberado` MUST NOT impedir la creación de otro turno del mismo profesional en su mismo horario (RN-17, RN-22).

#### Scenario: Horario de un turno cancelado
- **GIVEN** un turno `cancelado` del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno nuevo queda guardado en estado `pendiente`

#### Scenario: Horario de un turno liberado
- **GIVEN** un turno `liberado` del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno nuevo queda guardado en estado `pendiente`

### Requirement: Solo una de dos reservas simultáneas prospera
Cuando dos creaciones de turno del mismo profesional con intervalos superpuestos se ejecutan al mismo tiempo, el sistema MUST guardar exactamente una y rechazar la otra con el error "horario ocupado" (RN-24). La garantía MUST sostenerse aunque ninguna de las dos vea el turno de la otra antes de guardar.

#### Scenario: Dos creaciones simultáneas del mismo horario
- **GIVEN** un profesional A sin turnos el 2026-11-02
- **WHEN** dos creaciones independientes piden a la vez un turno del profesional A con inicio a las 10:00 de ese día
- **THEN** exactamente una creación termina con el turno guardado
- **AND** la otra falla con el error "horario ocupado"
- **AND** el profesional A tiene un único turno ese día

### Requirement: El profesional y la prestación pertenecen al consultorio
El sistema MUST rechazar la creación de un turno cuyo profesional o cuya prestación no existen en el consultorio indicado, con un error que distingue cuál de los dos falta. Un profesional o una prestación de otro consultorio se tratan como inexistentes (RN-55). Un turno rechazado no se guarda.

#### Scenario: Profesional inexistente
- **WHEN** se crea un turno en el consultorio 1 con un identificador de profesional que no existe
- **THEN** la creación falla con el error "profesional inexistente"
- **AND** no se guarda ningún turno

#### Scenario: Prestación de otro consultorio
- **GIVEN** una prestación que pertenece al consultorio 2
- **WHEN** se crea un turno en el consultorio 1 con esa prestación y un profesional del consultorio 1
- **THEN** la creación falla con el error "prestación inexistente"
- **AND** no se guarda ningún turno

### Requirement: El inicio del turno es un instante con zona horaria
El sistema MUST rechazar la creación de un turno cuyo inicio no indica zona horaria, para que el horario no dependa de la configuración del servidor. Un turno rechazado no se guarda.

#### Scenario: Inicio sin zona horaria
- **WHEN** se crea un turno con el inicio `2026-11-02 10:00` sin zona horaria
- **THEN** la creación falla con el error "el inicio debe indicar zona horaria"
- **AND** no se guarda ningún turno

#### Scenario: Mismo instante expresado en otra zona
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30, hora de Buenos Aires
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio el 2026-11-02 a las 13:00 UTC
- **THEN** la creación falla con el error "horario ocupado"
