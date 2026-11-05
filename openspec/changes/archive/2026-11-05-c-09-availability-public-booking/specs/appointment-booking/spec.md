# Spec Delta

## MODIFIED Requirements

### Requirement: Entrada de creación respeta autoridad del servidor
POST /api/v1/turnos SHALL habilitar el alta por personal autorizado y Paciente verificado con ficha vigente, resolviendo consultorio desde el principal. La entrada MUST rechazar campos no declarados con 422, incluido consultorio_id o fin. Para Paciente SHALL derivar ficha y origen online del servidor y rechazar paciente_id, duracion_min y confirmar enviados por cliente (RN-55, RN-62, RN-64).

#### Scenario: Consultorio enviado por cliente
- **WHEN** Recepción envía consultorio_id o un fin calculado en el payload
- **THEN** recibe 422 y no se persiste la reserva

#### Scenario: Recurso ajeno
- **WHEN** Recepción intenta reservar con una ficha, profesional o prestación de otro consultorio
- **THEN** recibe 404 sin revelar el recurso ni crear registros

#### Scenario: Entrada mínima online
- **WHEN** el Paciente habilitado envía profesional_id, prestacion_id e inicio con zona en un horario válido
- **THEN** el servidor reserva para su ficha vigente, calcula duración y origen online y responde 201

#### Scenario: Campos reservados al personal o al servidor
- **WHEN** un Paciente envía paciente_id, duracion_min, confirmar, origen, fin o consultorio_id, incluso con valores propios o null
- **THEN** recibe 422 sin turno ni historial; el personal conserva sus campos actuales paciente_id, duracion_min y confirmar
