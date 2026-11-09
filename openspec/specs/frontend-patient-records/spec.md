# frontend-patient-records Specification
## Purpose

Permitir a los roles habilitados consultar fichas de pacientes y gestionar solicitudes de vinculación sin exponer datos ajenos.

## Requirements
### Requirement: Búsqueda, ficha e historial autorizados
La interfaz SHALL permitir buscar fichas, consultar detalle e historial según el alcance del servidor. Recepción y Administrador SHALL poder crear y editar fichas; Profesional SHALL ver solo pacientes de su agenda y no controles de edición.

#### Scenario: Cuenta vinculada según rol
- **WHEN** Recepción o Administrador abre una ficha
- **THEN** ve la cuenta vinculada o su ausencia; Profesional no ve ese bloque.

#### Scenario: Búsqueda vacía
- **WHEN** no hay resultados autorizados
- **THEN** se muestra un estado vacío sin afirmar que existan fichas fuera del alcance.

### Requirement: Resolución de solicitudes de vínculo
Recepción y Administrador SHALL poder consultar solicitudes pendientes y resueltas, incluyendo ficha vinculada cuando corresponda, vincular a una ficha elegida o rechazar una pendiente. SHALL mostrar conflictos sin perder la pantalla y actualizar el estado al resolver.

#### Scenario: Rechazada se vincula
- **WHEN** personal elige una ficha para una solicitud rechazada y la API acepta
- **THEN** la solicitud aparece vinculada con la ficha elegida.

#### Scenario: Conflicto de vínculo
- **WHEN** la API devuelve 409 por una solicitud o ficha cambiada
- **THEN** se explica el conflicto y se ofrece actualizar antes de volver a intentar.

### Requirement: Desvinculación y reactivación
Recepción y Administrador SHALL poder desvincular con motivo obligatorio y reactivar una ficha inactiva. Profesional MUST NOT ver esas acciones. Las respuestas de conflicto SHALL ser visibles sin perder el contexto.

#### Scenario: Falta motivo
- **WHEN** se intenta desvincular sin motivo
- **THEN** se muestra el error y no se envía la solicitud.

#### Scenario: Estado cambió
- **WHEN** desvincular o reactivar recibe 409
- **THEN** se muestra el conflicto y se permite actualizar la ficha.

### Requirement: Historial de turnos paginado
La pantalla SHALL obtener el historial autorizado en páginas acotadas, con controles accesibles para retroceder y avanzar, sin mostrar información de otra ficha o identidad.

#### Scenario: Primera y última página
- **WHEN** el personal abre una ficha con más de veinte turnos y navega hasta la última página
- **THEN** ve hasta veinte turnos por página, puede volver y no puede avanzar después de la última.

#### Scenario: Error y cambio de ficha
- **WHEN** falla la lectura de una página o se abre otra ficha antes de la respuesta
- **THEN** puede reintentar sin perder la ficha y una respuesta anterior no reemplaza los datos de la ficha actual.
