# Spec Delta

## MODIFIED Requirements

### Requirement: Recuperación de reclamaciones vencidas
El despacho SHALL revisar vigencia, intentos y cupos en ese orden, al reclamar programadas o retomar vencidas. Verificación y recuperación SHALL ser siempre vigentes; rechazo de vinculación SHALL requerir correo verificado. Solicitud y recordatorio SHALL requerir turno, ciclo, estado e inicio vigentes y no haber alcanzado el siguiente hito. Avisos de hechos consumados SHALL conservar vigencia. Toda salida de enviando SHALL limpiar la marca (RN-61; CHANGES C-16).

#### Scenario: Reclamación vigente
- **WHEN** la marca no superó NOTIFICATION_CLAIM_TTL_SECONDS
- **THEN** no vuelve a reclamar ni enviar

#### Scenario: Reclamación vencida elegible
- **WHEN** expiró, el tipo sigue vigente, quedan intentos y hay cupo
- **THEN** reemplaza su marca por una posterior, incrementa intentos y reenvía

#### Scenario: Reclamación agotada
- **WHEN** venció y alcanzó NOTIFICATION_MAX_ATTEMPTS
- **THEN** pasa a fallida sin enviar, incluso sin cupo diario

#### Scenario: Rechazo de vinculación no vigente
- **WHEN** la cuenta no tiene correo verificado al tomar una programada o revisar una vencida de vinculacion_rechazada
- **THEN** pasa a omitida sin enviar, aun con intentos agotados o cupos completos

#### Scenario: Solicitud vigente y confirmada
- **WHEN** una solicitud programada o vencida está antes del siguiente hito y corresponde al ciclo vigente de un turno futuro pendiente, o el turno ya quedó confirmado
- **THEN** envía solo en el primer caso y en el segundo omite sin enviar ni consumir otro intento

#### Scenario: Recordatorio y bordes temporales
- **WHEN** un recordatorio programado o vencido corresponde a un turno pendiente o confirmado, del mismo ciclo
- **THEN** puede enviarse solo si inicio es posterior al reloj y no alcanzó el hito de liberación; se omite al alcanzar ese hito o cuando inicio es igual o anterior

#### Scenario: Cambio de ciclo o turno sin vigencia
- **WHEN** una solicitud o recordatorio tiene otro ciclo o su turno está cancelado, liberado, atendido, ausente o no existe
- **THEN** pasa a omitida sin enviar, aunque los cupos estén completos o sus intentos agotados, y limpia la reclamación anterior

#### Scenario: Avisos de hechos consumados
- **WHEN** hay avisos de liberacion, cancelacion_por_personal, reprogramacion_por_personal, resumen_reserva o cancelacion_por_paciente y el turno cambió de estado, ciclo o ya comenzó
- **THEN** siguen siendo elegibles por tipo y se envían si hay intentos y cupo, sin exigir un turno activo

#### Scenario: Tope no bloquea resolución sin envío
- **WHEN** se alcanzó el tope diario y hay una enviando vencida elegible, otra no vigente y otra agotada
- **THEN** conserva la elegible con sus intentos y marca originales, omite la no vigente y falla la agotada sin enviar ni contarlas como reclamaciones vigentes

#### Scenario: Barrido retrasado hasta el hito siguiente
- **WHEN** una solicitud sigue sin enviar a T-24 o un recordatorio sigue sin enviar a T-12 con parámetros 48/24/12
- **THEN** los omite sin envío retroactivo, tanto en programada como en enviando vencida; no crea una solicitud tardía que habilite la liberación

## ADDED Requirements

### Requirement: Fechas de envío pertenecen al ciclo vigente
Al registrar un envío exitoso propio de solicitud o recordatorio, el sistema SHALL actualizar confirmacion_solicitada_en o recordatorio_enviado_en únicamente si el turno sigue en el ciclo enviado. MUST descartar resultados sin reclamación propia y no escribir fechas sobre un ciclo nuevo (RN-32, RN-61; flujo 4).

#### Scenario: Resultado exitoso del ciclo actual
- **WHEN** el despacho registra enviada conservando su reclamación y el turno sigue en el ciclo de la solicitud o recordatorio
- **THEN** persiste junto al resultado la fecha de envío pertinente del reloj inyectado

#### Scenario: Resultado tardío tras reprogramación o pérdida de reclamación
- **WHEN** termina un envío del ciclo anterior o ya no conserva su reclamación
- **THEN** nunca contamina las fechas del ciclo nuevo y un resultado sin reclamación no modifica tampoco la notificación

### Requirement: Avisos de reserva y cancelación por el paciente
Una reserva exitosa SHALL programar resumen_reserva y una cancelación por paciente SHALL programar cancelacion_por_paciente, en la misma transacción del hecho con su ciclo y contenido mínimo capturado. Los avisos SHALL seguir vigentes ante cambios posteriores del turno y reutilizar despacho, cupos y reintentos (US-014, flujo 6, RN-54).

#### Scenario: Resumen independiente de cambios posteriores
- **WHEN** se reserva un turno con email utilizable y después se reprograma o cancela antes del envío
- **THEN** existe un solo resumen del ciclo original y se entrega con el horario capturado al reservar

#### Scenario: Cancelación por paciente y distinción del personal
- **WHEN** un paciente cancela correctamente o lo hace el personal
- **THEN** en el primer caso se programa solo su confirmación de cancelación, y en el segundo se conserva el aviso de personal existente, sin duplicar tipos de actores

#### Scenario: Fallo de programación y ausencia de contacto
- **WHEN** falla guardar el aviso o la ficha carece de email utilizable
- **THEN** el fallo revierte turno e historial; sin contacto no se inventa destinatario ni se impide la operación y se registra una señal técnica sin datos personales

#### Scenario: Contenido mínimo y fallo de transporte
- **WHEN** se entrega el aviso de un turno con DNI, obra social, notas o motivo interno, o SMTP falla después del commit
- **THEN** el correo excluye esos datos; el fallo conserva el hecho y aplica reintentos acotados sin exponer secretos
