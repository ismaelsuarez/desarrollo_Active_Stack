# Spec Delta

## ADDED Requirements

### Requirement: Lista operativa de turnos sin confirmar
GET /api/v1/turnos?sin_confirmar=true SHALL permitir solo a Recepción/Administrador consultar pendientes con marcado_sin_confirmar_en no nulo de su consultorio. SHALL conservar minimización, orden por inicio/identificador y el comportamiento anterior sin el filtro o con false. Confirmar, cancelar, liberar y reprogramar SHALL reutilizar las acciones existentes (US-025, RN-28, RN-32, RN-55).

#### Scenario: Filtrado por marca estado y consultorio
- **WHEN** Recepción lista sin_confirmar=true y existen pendientes marcados/no marcados, confirmados/cancelados/liberados con marca y filas de otro consultorio
- **THEN** recibe solo pendientes marcados de su consultorio, ordenados por inicio e identificador, sin DNI, contacto, obra social ni cuenta

#### Scenario: Resolución y reinicio
- **WHEN** Recepción confirma, cancela, libera o reprograma un turno de esa lista
- **THEN** la acción aplica las reglas existentes y el turno deja de aparecer; al reprogramar la marca queda nula en el ciclo nuevo

#### Scenario: Roles sin acceso al filtro
- **WHEN** Profesional, Paciente o Administrativo solicita sin_confirmar=true
- **THEN** recibe 403 y no obtiene una lista ampliada de turnos o datos del consultorio

#### Scenario: Compatibilidad de lectura existente
- **WHEN** un usuario previamente autorizado consulta sin el filtro o con sin_confirmar=false
- **THEN** conserva el alcance y contrato de sus turnos/agenda existentes, incluida la cuenta de paciente y la agenda propia del Profesional
