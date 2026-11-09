# Spec Delta

## ADDED Requirements

### Requirement: Fechas iniciales según el consultorio
La pantalla SHALL establecer el período inicial según la fecha de la zona horaria del consultorio y no la zona del navegador.

#### Scenario: Zonas con días diferentes
- **WHEN** la fecha local del navegador difiere de la del consultorio
- **THEN** las fechas iniciales corresponden al día del consultorio.

