# Spec Delta

## Purpose

Ofrece un catálogo por consultorio de prestaciones dentales con duraciones sugeridas que el Administrador puede adaptar para turnos futuros.

## ADDED Requirements

### Requirement: Catálogo inicial editable de nueve prestaciones
La semilla MUST crear una sola vez nueve prestaciones iniciales con duraciones marcadas como sugeridas; repetirla no debe duplicar ni sobrescribir cambios hechos por el consultorio.

#### Scenario: Semilla en consultorio nuevo
- **WHEN** se inicializa un consultorio sin prestaciones
- **THEN** queda disponible el catálogo de nueve prestaciones sugeridas

#### Scenario: Repetición preserva cambios
- **GIVEN** una prestación inicial cuya duración fue editada
- **WHEN** se vuelve a ejecutar la semilla
- **THEN** no se crea un duplicado ni se restaura la duración anterior

### Requirement: Administrador mantiene prestaciones
El Administrador MUST poder listar, crear, editar y desactivar prestaciones de su consultorio; cada duración es un entero positivo y el nombre es único dentro del consultorio.

#### Scenario: Crear prestación válida
- **WHEN** el administrador crea una prestación con nombre único y duración positiva
- **THEN** queda disponible para turnos nuevos

#### Scenario: Rechazar duración inválida o nombre duplicado
- **WHEN** se intenta guardar duración no positiva o repetir nombre en el consultorio
- **THEN** la solicitud se rechaza y el catálogo no cambia

### Requirement: Cambios al catálogo no reescriben turnos existentes
Modificar o desactivar una prestación MUST afectar solo turnos nuevos; turnos históricos MUST conservar la prestación y duración que tenían.

#### Scenario: Editar duración
- **GIVEN** un turno ya creado con la prestación
- **WHEN** el administrador modifica la duración sugerida
- **THEN** la duración guardada en el turno no cambia
