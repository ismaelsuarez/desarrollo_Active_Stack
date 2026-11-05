# Spec Delta

## ADDED Requirements

### Requirement: Acceso a fichas por vínculo vigente y agenda
paciente.ver y paciente.editar SHALL usar consultorio y vínculo leídos para la solicitud actual. Recepción/Administrador SHALL acceder a su consultorio; Profesional sólo SHALL leer pacientes de su agenda; Paciente sólo SHALL leer su ficha y editar contacto propio. Una ficha ajena por id SHALL responder 404 (RN-06, RN-50, RN-55, RN-63; KB 11).

#### Scenario: Personal y agenda autorizados
- **WHEN** el personal de Recepción/Administración consulta una ficha de su consultorio o un Profesional consulta un paciente de su agenda
- **THEN** autorizar permite la lectura y el Profesional no puede editar ni recibir datos de cuenta

#### Scenario: Ficha fuera de alcance
- **WHEN** el Profesional pide una ficha fuera de su agenda, el Paciente pide la de otra cuenta o el recurso es de otro consultorio
- **THEN** responde 404 sin revelar la ficha; los filtros se aplican también a búsquedas y sus totales

#### Scenario: Vínculo leído después de emitir el token
- **WHEN** una cuenta desvinculada usa un JWT emitido antes para leer o editar su antigua ficha
- **THEN** recibe 404 porque el vínculo ya no le corresponde, sin agregar paciente_id a los claims

### Requirement: Resoluciones de vínculo reservadas al personal
paciente.vincular, paciente.desvincular y paciente.reactivar SHALL permitirse sólo a Recepción y Administrador. Las solicitudes de vinculación SHALL tener ese mismo alcance de rol y consultorio. Estado incompatible al escribir SHALL ser 409 y no una ampliación de la política (RN-62, RN-63; KB 11).

#### Scenario: Actor sin permiso funcional
- **WHEN** Profesional, Paciente o Administrativo lista solicitudes o intenta vincular, rechazar, desvincular o reactivar
- **THEN** recibe 403 y no cambia ficha, solicitud, sesiones ni notificaciones

#### Scenario: Recurso ajeno y estado incompatible
- **WHEN** un actor permitido opera un recurso de otro consultorio o una transición incompatible con los datos actuales
- **THEN** el recurso ajeno responde 404 y el conflicto al escribir responde 409 con rollback; ninguna ruta autoriza ad hoc fuera del punto de entrada central
