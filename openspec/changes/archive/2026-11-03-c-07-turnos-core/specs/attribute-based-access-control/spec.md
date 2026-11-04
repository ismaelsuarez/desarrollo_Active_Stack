# Spec Delta

## MODIFIED Requirements

### Requirement: Propiedad de agenda y titularidad de turnos (A1)
Un profesional MUST acceder solo a turnos de su agenda. Un paciente MUST operar solo sobre turnos de su ficha vigente. Turno ajeno consultado u operado por identificador, ficha no vinculada y recurso de otro consultorio SHALL responder 404; pedir la agenda de un colega del mismo consultorio SHALL responder 403 (KB 11 §Matriz de decisión; RN-35, RN-50, RN-55).

#### Scenario: Profesional accede a turno de su propia agenda
- **WHEN** un profesional solicita ver o gestionar un turno asignado a su identificador profesional
- **THEN** la política de dueño de agenda permite continuar con las restantes comprobaciones de la acción

#### Scenario: Profesional intenta acceder a turno de otro profesional
- **WHEN** un profesional solicita ver o gestionar por identificador un turno asignado a otro profesional
- **THEN** la política deniega el acceso con código HTTP 404

#### Scenario: Paciente con ficha vigente opera sobre su turno
- **WHEN** un paciente con ficha_vigente_id válida opera sobre un turno asociado a ese mismo paciente_id
- **THEN** la política de titularidad permite continuar con las restantes comprobaciones de la acción

#### Scenario: Paciente intenta operar sobre turno ajeno o sin ficha vigente
- **WHEN** un paciente intenta operar sobre un turno de otro paciente o la cuenta no tiene ficha vinculada
- **THEN** la política deniega el acceso con código HTTP 404

#### Scenario: Profesional solicita agenda de un colega
- **WHEN** un profesional consulta la agenda de otro profesional del mismo consultorio
- **THEN** la política deniega con 403, sin alterar el 404 aplicable a turnos por identificador
