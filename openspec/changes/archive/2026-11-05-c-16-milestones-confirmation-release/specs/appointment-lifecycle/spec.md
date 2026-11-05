# Spec Delta

## MODIFIED Requirements

### Requirement: Reprogramar reinicia el ciclo de confirmación
Una reprogramación exitosa SHALL incrementar el ciclo y limpiar la marca sin confirmar. SHALL dejar el turno confirmado si faltan menos de horas_confirmacion, y pendiente en otro caso, registrando el motivo de la regla temporal en el historial. SHALL omitir solicitud/recordatorio programada o preparada del ciclo anterior en todos los canales y planificar los nuevos hitos en la misma transacción (RN-29, RN-32, RN-37).

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

#### Scenario: Omisión por tipo y ciclo
- **GIVEN** solicitudes y recordatorios del ciclo anterior en programada, preparada, enviada y enviando, además de avisos de reprogramación y reserva
- **WHEN** se reprograma correctamente
- **THEN** solo solicitud/recordatorio programada o preparada pasan a omitida en cualquier canal; los avisos de hechos consumados y las enviadas/enviando conservan su estado, y los hitos nuevos llevan el ciclo nuevo

#### Scenario: Fallo de la nueva planificación
- **WHEN** falla omitir o programar hitos al reprogramar
- **THEN** se conservan turno, ciclo, marca, historial y notificaciones originales sin efectos parciales

## ADDED Requirements

### Requirement: Cancelar y liberar omiten hitos del ciclo vigente
Una cancelación o liberación exitosa por paciente, personal o sistema SHALL omitir en la misma transacción las solicitudes y recordatorios programada o preparada del ciclo vigente, en todos los canales. MUST conservar avisos de hechos consumados y no interrumpir una reclamación enviando vigente (RN-32; KB 04 Vigencia por tipo).

#### Scenario: Cancelar o liberar con hitos pendientes
- **WHEN** se cancela o libera un turno con solicitudes/recordatorios programada o preparada y un resumen de reserva programado
- **THEN** los dos primeros tipos quedan omitidos y el resumen permanece programado junto al nuevo aviso pertinente

#### Scenario: Reclamación en vuelo y error transaccional
- **WHEN** se cancela un turno cuya solicitud está enviando, o falla la omisión transaccional de otra notificación
- **THEN** una reclamación vigente puede terminar sin ser sobrescrita y una vencida se revalida; un fallo revierte la cancelación y sus demás efectos
