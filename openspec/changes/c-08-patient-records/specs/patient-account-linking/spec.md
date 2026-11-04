# Spec Delta

## Purpose

Permitir al personal resolver y corregir vínculos de cuentas con fichas de paciente sin duplicarlas, perder sus turnos ni dejar efectos parciales ante solicitudes concurrentes.

## ADDED Requirements

### Requirement: Solicitudes visibles y resoluciones conservadas
GET /api/v1/solicitudes-vinculacion SHALL permitir a Recepción y Administrador consultar solicitudes de su consultorio, con filtro opcional de estado. Sin filtro SHALL incluir resueltas. SHALL mostrar DNI declarado, correo y verificación, ficha coincidente y, en vinculada, ficha vinculada mínima (RN-62, RN-63).

#### Scenario: Pendientes y consulta completa
- **WHEN** se consulta con estado pendiente antes y después de resolver y después sin filtro
- **THEN** la solicitud deja de aparecer entre pendientes y sigue consultable con su estado, última resolución y actor/fecha

#### Scenario: Datos mínimos y estado inválido
- **WHEN** una solicitud está vinculada, pendiente o rechazada, o se pide un estado desconocido
- **THEN** vinculada muestra sólo id/nombre/apellido de su ficha vinculada, los otros estados no la presentan como vínculo vigente y el filtro inválido responde 422; no expone hashes ni datos extra de cuenta

#### Scenario: Aislamiento y rol
- **WHEN** el consultorio tiene solicitudes homónimas de otros consultorios o consulta Profesional, Paciente o Administrativo
- **THEN** no se filtran filas ajenas y los roles no habilitados reciben 403

### Requirement: Vinculación manual elegida por personal
POST /api/v1/solicitudes-vinculacion/{id}/vincular SHALL aceptar paciente_id y vincular sólo una solicitud pendiente o rechazada con una ficha activa y sin cuenta del mismo consultorio, para una cuenta con correo verificado. SHALL registrar actor y fecha y conservar el motivo anterior (RN-49, RN-62; SU-42).

#### Scenario: Vincular pendiente o rechazada
- **WHEN** Recepción elige una ficha elegible para una solicitud pendiente o rechazada
- **THEN** la solicitud queda vinculada a esa ficha y la ficha a la cuenta, con actor/fecha, sin borrar un motivo de rechazo previo ni alterar datos de la ficha

#### Scenario: DNI informativo y ficha nueva
- **WHEN** el DNI de la ficha cambió después de la solicitud o Recepción creó una ficha nueva para la persona
- **THEN** puede elegirla sin exigir coincidencia con dni_declarado ni crear una segunda cuenta

#### Scenario: Estado o cuenta incompatibles
- **WHEN** la solicitud ya está vinculada, la ficha está inactiva o tiene cuenta, el correo no está verificado o la cuenta ya tiene otra ficha
- **THEN** responde 409 y conserva ficha, solicitud y cuenta sin escrituras parciales

#### Scenario: Referencias ajenas y entrada estricta
- **WHEN** solicitud o ficha no existen en el consultorio o se envían estado, usuario_id, consultorio_id o campos no declarados
- **THEN** responde 404 para referencias fuera de alcance o 422 para la entrada inválida, sin cambios

### Requirement: Conflictos de vinculación son atómicos
Las resoluciones SHALL serializar el acceso a la ficha elegida y comprobar condicionalmente el estado de solicitud y la elegibilidad de la ficha. Un conflicto de estado, unicidad de cuenta, interbloqueo o serialización SHALL responder 409 con reversión completa. MUST NOT devolver éxito antes de confirmar (RN-62).

#### Scenario: Dos cuentas y una ficha
- **WHEN** dos sesiones independientes intentan vincular cuentas diferentes a la misma ficha simultáneamente
- **THEN** una prospera, la otra recibe 409, sólo una cuenta queda vinculada y la solicitud perdedora conserva su estado original

#### Scenario: Una solicitud y dos fichas
- **WHEN** dos sesiones intentan vincular la misma solicitud con fichas diferentes simultáneamente
- **THEN** sólo una resolución prospera y la otra recibe 409, sin asociar la cuenta a dos fichas ni modificar la ficha perdedora

#### Scenario: Rechazo concurrente con vínculo
- **WHEN** dos sesiones intentan rechazar y vincular la misma solicitud pendiente
- **THEN** persiste una resolución y la otra recibe 409 sin efectos parciales; sólo si gana el rechazo puede programarse su correo

#### Scenario: Error del motor o fallo intermedio
- **WHEN** se informa 40P01, 40001, unicidad de paciente.usuario_id o un fallo después de la primera escritura
- **THEN** los conflictos previstos responden 409 y cualquier fallo revierte la operación completa, sin ocultar otros errores de integridad como conflictos de vínculo

### Requirement: Rechazo con correo mínimo y durable
POST /api/v1/solicitudes-vinculacion/{id}/rechazar SHALL aceptar motivo opcional y resolver sólo pendiente. Con correo verificado SHALL programar un único vinculacion_rechazada en la misma transacción e intentar despacho después del commit. Sin verificar MUST NOT programar correo (RN-54, RN-62; US-039).

#### Scenario: Cuenta verificada
- **WHEN** Recepción rechaza una solicitud pendiente de una cuenta verificada
- **THEN** conserva motivo y actor/fecha, deja la cuenta sin ficha, programa una notificación y solicita despacho inmediato con un texto que pide comunicarse con el consultorio sin motivo, DNI ni datos de salud

#### Scenario: Cuenta sin verificar o resolución repetida
- **WHEN** se rechaza una cuenta sin verificar o se repite el rechazo de una solicitud ya resuelta
- **THEN** el primer caso registra el rechazo sin correo y el segundo responde 409 sin correo ni resolución adicional

#### Scenario: Fallo de programación o transporte
- **WHEN** falla persistir la notificación o falla SMTP después de confirmar el rechazo
- **THEN** el primer fallo revierte solicitud y notificación juntas; el fallo de transporte conserva el rechazo y el trabajo durable para el despacho existente, sin exigir el barrido C-15

### Requirement: Desvinculación conserva ficha y registra su origen
POST /api/v1/pacientes/{id}/desvincular SHALL exigir motivo y personal habilitado. SHALL quitar condicionalmente la cuenta leída, dejar o crear su solicitud rechazada con ficha de origen, actor, fecha y motivo y revocar refresh tokens en una sola transacción. MUST NOT enviar correo ni cambiar datos o turnos (RN-63).

#### Scenario: Cuenta con solicitud vinculada
- **WHEN** se desvincula una ficha con una cuenta y su solicitud vinculada
- **THEN** usuario_id queda null y la solicitud rechazada conserva origen, motivo y resolución, sin otra alteración de ficha/turnos ni notificación

#### Scenario: Cuenta registrada con DNI nuevo
- **WHEN** la cuenta no tenía solicitud porque recibió su ficha al registrarse
- **THEN** crea una solicitud rechazada con dni_declarado igual al DNI actual de la ficha y conserva la ficha de origen

#### Scenario: Motivo y referencias
- **WHEN** falta motivo, la ficha no tiene cuenta o la ficha no existe en el consultorio
- **THEN** responde 422, 409 o 404 respectivamente sin cambios; Profesional y Paciente reciben 403

#### Scenario: Solicitud incompatible o fallo de revocación
- **WHEN** una solicitud existente no está vinculada o falla persistir resolución o revocar sesiones
- **THEN** responde conflicto cuando corresponde y revierte también el cambio de usuario_id, sin perder el vínculo anterior

### Requirement: Desvinculación es segura con operaciones concurrentes
Desvincular SHALL comprobar el vínculo vigente al escribir y serializarse con otras operaciones sobre la ficha. La revocación SHALL cubrir sesiones renovadas en vuelo. Los access tokens previos MUST NOT conceder acceso a la antigua ficha, aunque sigan vigentes (RN-06, RN-63).

#### Scenario: Doble desvinculación
- **WHEN** dos sesiones independientes desvinculan la misma ficha simultáneamente
- **THEN** una prospera y la otra recibe 409, con una sola resolución efectiva y sin correos

#### Scenario: Vínculo concurrente y refresh
- **WHEN** un vínculo compite con una desvinculación o un refresh está en vuelo al desvincular
- **THEN** la ficha nunca queda con dos cuentas, las operaciones conservan atomicidad y ningún refresh de la cuenta desvinculada queda renovable al terminar la desvinculación

#### Scenario: JWT emitido antes del cambio
- **WHEN** el mismo JWT de acceso anterior intenta leer la antigua ficha después de desvincular
- **THEN** recibe 404 porque se consulta el vínculo vigente; sus refresh tokens responden como revocados y no renuevan

### Requirement: Reactivación condicional y recuperación del vínculo
POST /api/v1/pacientes/{id}/reactivar SHALL permitir sólo a Recepción y Administrador activar una ficha inactiva, sin motivo ni cambios en otros campos o turnos. SHALL responder 409 si ya está activa y 404 si no existe en su consultorio (RN-63; SU-44, SU-47).

#### Scenario: Reactivar y vincular
- **WHEN** se reactiva una ficha inactiva y después se elige para una solicitud elegible
- **THEN** la ficha queda activa y la cuenta puede vincularse con la transición normal

#### Scenario: Doble reactivación
- **WHEN** dos sesiones intentan reactivar la misma ficha inactiva
- **THEN** una prospera y la otra recibe 409, sin perder datos ni turnos

#### Scenario: Reactivación inválida
- **WHEN** se pide una ficha inexistente o ajena, ya activa, con campos no declarados o desde un rol no permitido
- **THEN** responde 404, 409, 422 o 403 según corresponda y no modifica la ficha

### Requirement: Recuperación manual de vínculos equivocados
El personal SHALL poder resolver los cuatro recorridos de RN-63 con registro C-05 y las acciones C-08: vínculo equivocado, ficha ocupada, ficha inactiva y ficha tomada por un tercero. MUST NOT agregar recuperación automática, formulario de reintento ni auditoría general (DD-19, DD-20; US-039, US-041, US-042).

#### Scenario: Vínculo equivocado o ficha ocupada
- **WHEN** Recepción verifica a quién corresponde la ficha
- **THEN** puede desvincular y vincular con la correcta, o rechazar si la ficha corresponde a la otra cuenta, preservando ambas fichas y sus turnos

#### Scenario: Ficha inactiva o tomada por tercero
- **WHEN** la ficha correcta está inactiva o fue tomada por otra cuenta registrada primero
- **THEN** puede reactivar y vincular, o desvincular, corregir la ficha y vincular a la persona correcta; conserva los turnos para su gestión normal, sin borrarlos automáticamente
