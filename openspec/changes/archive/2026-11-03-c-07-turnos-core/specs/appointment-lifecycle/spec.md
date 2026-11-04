# Spec Delta

## Purpose

Permite al personal cambiar el horario y el estado de un turno con trazabilidad, sin perder el turno original ni persistir efectos parciales cuando una operación falla.

## ADDED Requirements

### Requirement: Reprogramación atómica del mismo turno
El sistema SHALL reprogramar un turno modificable sobre el mismo identificador, conservar su duración actual salvo ajuste autorizado y validar agenda y solapamientos. Si falla, MUST conservar horario, estado, ciclo, marca e historial originales (RN-14, RN-17, RN-37, RN-64).

#### Scenario: Mover conserva duración ajustada
- **GIVEN** un turno de 45 minutos y una prestación cuya duración actual es 30
- **WHEN** Recepción lo mueve a un horario válido y libre sin ajustar duración
- **THEN** conserva su identificador y sus 45 minutos y registra la reprogramación

#### Scenario: Destino ocupado no deja cambios parciales
- **GIVEN** un turno pendiente con marca sin confirmar y un destino ocupado por otro turno regular
- **WHEN** Recepción intenta reprogramarlo a ese destino
- **THEN** recibe 409 horario ocupado y el turno, ciclo, marca e historial permanecen intactos

#### Scenario: La fila no entra en conflicto consigo misma
- **GIVEN** un turno regular de 10:00 a 10:30 sin otros turnos ni bloqueos
- **WHEN** Recepción lo reprograma a 10:15 en una grilla válida
- **THEN** conserva el identificador y termina a 10:45 sin un segundo turno

### Requirement: Reprogramar reinicia el ciclo de confirmación
Una reprogramación exitosa SHALL incrementar el ciclo y limpiar la marca sin confirmar. SHALL dejar el turno confirmado si faltan menos de horas_confirmacion, y pendiente en otro caso, registrando el motivo de la regla temporal en el historial (RN-29, RN-32, RN-37).

#### Scenario: Turno marcado vuelve al ciclo normal
- **GIVEN** un turno marcado en ciclo 2 y un destino libre a más de 48 horas con parámetro 48
- **WHEN** Recepción lo reprograma
- **THEN** queda pendiente en ciclo 3, con marca nula y un registro de reprogramación

#### Scenario: Destino a menos de 48 horas
- **GIVEN** horas_confirmacion 48 y un destino libre a 47 horas 59 minutos
- **WHEN** Recepción reprograma un turno pendiente
- **THEN** queda confirmado, incrementa el ciclo y el historial identifica RN-29 como motivo

#### Scenario: Destino exactamente a 48 horas
- **GIVEN** horas_confirmacion 48 y un destino libre exactamente a 48 horas
- **WHEN** Recepción reprograma el turno
- **THEN** queda pendiente en el nuevo ciclo y sin la marca del ciclo anterior

### Requirement: Cancelación por el personal conserva trazabilidad
Recepción y Administrador SHALL cancelar turnos modificables con motivo, actor y fecha, conservando la fila y liberando el hueco. Los turnos atendido, cancelado, liberado o ausente MUST rechazar cancelación con 403 (RN-19, RN-22, RN-34, RN-36).

#### Scenario: Cancelar un turno confirmado
- **WHEN** Recepción cancela un confirmado con motivo válido
- **THEN** queda cancelado con actor, fecha y motivo; el historial registra el cambio y el hueco queda libre

#### Scenario: Cancelar un turno atendido
- **WHEN** Administrador intenta cancelar un atendido
- **THEN** recibe 403 y no cambian el turno ni su historial

### Requirement: Confirmación manual y liberación controlada
Recepción y Administrador SHALL confirmar pendientes y liberarlos si el modo es manual o tienen marca sin confirmar. En otro estado, o en modo automático sin marca para liberar, MUST responder 403 sin cambios (RN-23, RN-30, RN-60; KB 11).

#### Scenario: Confirmar por teléfono
- **WHEN** Recepción confirma un pendiente
- **THEN** queda confirmado con fecha y actor en el historial

#### Scenario: Liberar un pendiente marcado
- **GIVEN** modo automático y un pendiente con marca sin confirmar
- **WHEN** Recepción lo libera
- **THEN** queda liberado con historial y el horario disponible

#### Scenario: Liberar en modo manual
- **GIVEN** modo manual y un turno pendiente sin marca
- **WHEN** Administrador lo libera
- **THEN** queda liberado con fecha e historial

#### Scenario: Liberación o confirmación no permitidas
- **WHEN** se intenta liberar un pendiente sin marca en modo automático o confirmar un liberado
- **THEN** recibe 403 y no hay efectos persistidos

### Requirement: Registro de atención y corrección de ausencia
El personal autorizado SHALL marcar atendido o ausente desde pendiente o confirmado, con historial, cuando ahora >= inicio. Antes del inicio MUST rechazar ambas acciones con 403. Atendido MUST ser inmutable y solo Recepción/Administrador SHALL corregir ausente a atendido (RN-18, RN-19, RN-21, RN-38, RN-44; criterio temporal confirmado por el usuario para C-07).

#### Scenario: Atendido al alcanzar el inicio
- **GIVEN** un turno de la agenda del Profesional y ahora igual a su inicio
- **WHEN** el Profesional marca atendido
- **THEN** queda atendido y el historial registra la acción

#### Scenario: Ausente después del inicio
- **GIVEN** un turno de la agenda del Profesional y ahora un segundo posterior al inicio
- **WHEN** el Profesional marca ausente
- **THEN** queda ausente con registro de actor y fecha

#### Scenario: Ausente exactamente al inicio
- **GIVEN** un turno pendiente o confirmado y ahora exactamente igual al inicio, con reloj inyectado
- **WHEN** el Profesional de esa agenda, Recepción o Administrador marca ausente
- **THEN** la operación se permite y confirma juntos el estado ausente y su historial con actor y fecha

#### Scenario: Rechazo antes del inicio
- **GIVEN** ahora un segundo anterior al inicio
- **WHEN** el Profesional intenta marcar atendido o ausente
- **THEN** recibe 403 sin cambios ni historial adicional

#### Scenario: Corregir ausencia
- **WHEN** Recepción corrige un ausente a atendido
- **THEN** queda atendido y se agrega una acción corregir sin modificar el historial anterior

#### Scenario: Corrección o modificación no autorizadas
- **WHEN** un Profesional intenta corregir ausente o cualquier rol intenta mover un atendido
- **THEN** recibe 403 y se conserva el estado anterior

### Requirement: Historial y operación se confirman juntos
Cada alta, transición y reprogramación exitosa SHALL agregar historial con consultorio, turno, actor, acción, estados y fecha del reloj. El historial MUST ser solo de inserción. Una operación rechazada MUST dejar turno e historial sin cambios parciales (RN-21; KB 04 §turno_historial).

#### Scenario: Cambio exitoso deja un registro
- **WHEN** se confirma un pendiente correctamente
- **THEN** se observan juntos el nuevo estado y un único registro de confirmar

#### Scenario: Fallo del historial revierte la operación
- **WHEN** falla la persistencia del historial de una reprogramación
- **THEN** no se confirma ningún cambio del turno ni del historial

Trazabilidad del borde temporal: el usuario confirmó ahora >= inicio para C-07 el 2026-11-03. Esto resuelve el criterio del change conforme a KB 11 y flujo 8, sin modificar el texto de RN-44/US-028 en la base de conocimiento ni asignar una nueva DD.
