# Spec Delta

## MODIFIED Requirements

### Requirement: Barrido durable acotado
El sistema SHALL procesar correos vencidos y reclamaciones vencidas en lotes finitos e integrar la evaluación de liberar/marcar turnos de C-16, compartida por ambos disparadores. SHALL informar reclamadas, enviadas, reintentadas, omitidas y fallidas propias. Una reclamación propia cuyo resultado se pierde SHALL contar solo como reclamada; no SHALL atribuir resultados ajenos ni confundir decisiones de turno con entregas de correo.

#### Scenario: Pendientes tras suspensión
- **WHEN** se ejecuta el barrido después de tres horas sin servicio
- **THEN** procesa el trabajo vencido del lote que conserve vigencia, conserva el futuro y una repetición no reenvía filas ya enviadas

#### Scenario: Fallo de una entrega y resumen
- **WHEN** un lote incluye un envío exitoso, un error reintentable, una fila no vigente y una agotada
- **THEN** el resumen distingue sus resultados y el fallo de una entrega no impide tratar las otras filas

#### Scenario: Lote finito sin inanición por cupo de cuenta
- **WHEN** hay más pendientes que el tamaño del lote y los correos de cuenta agotaron su cupo
- **THEN** la ejecución termina sin reintentar la misma fila en ese barrido y considera también correos de turnos con cupo disponible

#### Scenario: Hitos y decisión tras retraso prolongado
- **WHEN** el barrido se recupera después de T-12 y antes del inicio con solicitudes y recordatorios sin enviar
- **THEN** omite los hitos superados y marca el pendiente sin liberarlo; si la solicitud del ciclo ya estaba enviada, aplica RN-60 y programa el aviso solo al ganar la liberación

#### Scenario: Disparadores comparten decisiones y límites
- **WHEN** el endpoint interno o el bucle en proceso ejecuta un barrido con más candidatos a decisión que el lote
- **THEN** ambos aplican el mismo procesamiento finito ordenado; los candidatos restantes quedan para ejecuciones siguientes y ninguna decisión se cuenta como correo enviado

#### Scenario: Cuota agotada no bloquea decisiones
- **WHEN** el cupo de correo está completo al alcanzar el hito de decisión
- **THEN** la decisión de liberar o marcar no se frena por el cupo; el aviso de una liberación ganadora queda durable para despacho posterior
