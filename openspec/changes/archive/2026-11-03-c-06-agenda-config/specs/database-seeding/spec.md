# Spec Delta

## ADDED Requirements

### Requirement: La semilla inicializa el catálogo de prestaciones sin sobrescribirlo
El comando de semilla MUST asegurar nueve prestaciones iniciales por consultorio nuevo y repetirse sin duplicar ni reemplazar nombres, duraciones o activación de prestaciones ya existentes.

#### Scenario: Sembrar consultorio vacío
- **GIVEN** un consultorio activo sin prestaciones
- **WHEN** termina la inicialización de datos
- **THEN** quedan creadas nueve prestaciones iniciales con duraciones sugeridas

#### Scenario: Semilla repetida
- **GIVEN** el catálogo ya existe y el Administrador modificó una prestación
- **WHEN** se repite la semilla
- **THEN** los valores modificados se preservan y no se crean duplicados
