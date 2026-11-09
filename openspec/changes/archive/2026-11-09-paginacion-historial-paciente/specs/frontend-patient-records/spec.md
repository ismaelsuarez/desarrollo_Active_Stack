# Spec Delta

## ADDED Requirements

### Requirement: Historial de turnos paginado
La pantalla SHALL obtener el historial autorizado en páginas acotadas, con controles accesibles para retroceder y avanzar, sin mostrar información de otra ficha o identidad.

#### Scenario: Primera y última página
- **WHEN** el personal abre una ficha con más de veinte turnos y navega hasta la última página
- **THEN** ve hasta veinte turnos por página, puede volver y no puede avanzar después de la última.

#### Scenario: Error y cambio de ficha
- **WHEN** falla la lectura de una página o se abre otra ficha antes de la respuesta
- **THEN** puede reintentar sin perder la ficha y una respuesta anterior no reemplaza los datos de la ficha actual.

