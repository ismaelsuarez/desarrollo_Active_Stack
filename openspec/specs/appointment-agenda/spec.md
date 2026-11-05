# appointment-agenda Specification

## Purpose

Entrega al personal las lecturas de turnos, agenda diaria e historial necesarias para organizar la atención, respetando consultorio, agenda propia y minimización de datos.

## Requirements

### Requirement: Consultar turnos e historial con alcance autorizado
El sistema SHALL ofrecer GET /api/v1/turnos, GET /api/v1/turnos/{id} y GET /api/v1/turnos/{id}/historial. SHALL filtrar por consultorio y permisos; Recepción/Administrador ven su consultorio y Profesional su agenda. Un turno ajeno por identificador MUST responder 404 (KB 11; RN-21, RN-50, RN-55).

#### Scenario: Detalle e historial propios
- **WHEN** Recepción consulta un turno y su historial en su consultorio
- **THEN** obtiene el turno y sus cambios con actor, fecha y estados

#### Scenario: Turno ajeno no se revela
- **WHEN** un Profesional consulta por identificador un turno de otro profesional o cualquier usuario un turno de otro consultorio
- **THEN** recibe 404 sin datos del turno ni de su historial

#### Scenario: Lista acotada
- **GIVEN** turnos de dos profesionales y de dos consultorios
- **WHEN** un Profesional lista sus turnos
- **THEN** recibe solamente los de su agenda y consultorio

### Requirement: Agenda diaria según zona del consultorio
GET /api/v1/agenda con profesional_id y fecha SHALL devolver los turnos de ese día en la zona del consultorio con horario, prestación, estado, paciente mínimo y marca de sobreturno. Profesional SHALL ver solo su agenda; agenda ajena del mismo consultorio MUST responder 403 y otro consultorio 404 (US-026; KB 11).

#### Scenario: Leer agenda propia
- **WHEN** un Profesional consulta su agenda de una fecha
- **THEN** recibe sus turnos ordenados por inicio dentro del día local, incluidos los sobreturnos identificados como tales

#### Scenario: Agenda de colega
- **WHEN** un Profesional pide la agenda de otro profesional del mismo consultorio
- **THEN** recibe 403

#### Scenario: Recurso de otro consultorio
- **WHEN** Recepción pide una agenda perteneciente a otro consultorio
- **THEN** recibe 404 sin revelar datos

### Requirement: Historial de turnos de una ficha
GET /api/v1/pacientes/{id}/turnos SHALL permitir a Recepción/Administrador leer turnos pasados y futuros de una ficha del consultorio, aun sin cuenta vinculada. El acceso profesional a fichas SHALL acotarse a pacientes de su agenda y a los turnos que está autorizado a ver (US-038, RN-50; KB 11).

#### Scenario: Ficha sin cuenta
- **GIVEN** una ficha sintética sin usuario y con turnos pasados y futuros
- **WHEN** Recepción consulta sus turnos
- **THEN** obtiene los turnos con sus estados sin exigir cuenta de paciente

#### Scenario: Ficha fuera del alcance
- **WHEN** se consulta una ficha de otro consultorio o un Profesional consulta una ficha sin turnos en su agenda
- **THEN** recibe 404

### Requirement: Respuestas minimizan información personal
Las lecturas SHALL devolver solo los datos necesarios para operar la agenda. MUST excluir DNI, obra social, contacto y datos de cuenta cuando no sean necesarios, y MUST evitar incluirlos en logs de consultas o rechazos (RN-54, RN-58; regla dura 13).

#### Scenario: Lectura operativa
- **WHEN** se consulta una agenda o historial de turnos
- **THEN** la respuesta incluye identificadores y nombre del paciente necesarios para operar, sin DNI, obra social ni bloque de cuenta

#### Scenario: Rechazo sin datos personales
- **WHEN** se registra una denegación de acceso
- **THEN** el registro no contiene DNI, contacto ni notas del paciente

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
