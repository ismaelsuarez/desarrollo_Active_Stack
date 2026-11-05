# appointment-confirmation Specification

## Purpose

Pedir y registrar confirmación de turnos, recordar su horario y resolver los pendientes con reglas temporales que protegen al paciente ante fallos del correo o del barrido.

## Requirements

### Requirement: Programación temporal transaccional
El sistema SHALL programar solicitudes email y recordatorios desde inicio y parámetros del consultorio, con el ciclo del turno y dentro de su transacción. SHALL omitir hitos ya vencidos al reservar/reprogramar, aplicar RN-29 y conservar idempotencia por turno/tipo/canal/ciclo (RN-25, RN-26, RN-32).

#### Scenario: Reserva normal y borde de confirmación
- **WHEN** se reserva un pendiente a más de 48 horas o exactamente a 48 horas con parámetros 48/24/12
- **THEN** se programan solicitud a T-48 y recordatorio a T-24 una sola vez; a 48 horas exactas la solicitud es inmediatamente elegible

#### Scenario: Reserva tardía y recordatorio futuro
- **WHEN** se reserva o reprograma a 30 horas con parámetros 48/24/12
- **THEN** el turno nace confirmado, no tiene solicitud y conserva el recordatorio futuro a T-24

#### Scenario: Hitos ya alcanzados al nacer
- **WHEN** se reserva o reprograma a 24 horas exactas o a 10 horas con parámetros 48/24/12
- **THEN** el turno nace confirmado, no se programa solicitud ni recordatorio retroactivo y nunca es candidato a marca o liberación automática

#### Scenario: Rollback e idempotencia
- **WHEN** falla la planificación dentro de una reserva o reprogramación, o se repite su programación válida
- **THEN** el fallo revierte turno, historial y comunicaciones; la repetición válida no duplica notificaciones del mismo ciclo

### Requirement: Confirmación por enlace de alcance limitado
POST /api/v1/turnos/confirmar-por-enlace SHALL aceptar únicamente un token en cuerpo, sin sesión ni consultorio del cliente. SHALL derivar consultorio/turno/ciclo del token de tipo confirmar_turno y confirmar solo un pendiente del ciclo vigente, registrando fecha, consumo e historial atómicos (RN-30, RN-59).

#### Scenario: Enlace válido con o sin cuenta
- **WHEN** se presenta un token válido de un pendiente del ciclo actual cuya ficha tiene o no tiene cuenta
- **THEN** responde 200 con identificador y estado confirmado mínimos, consume el token y registra una única confirmación sin exigir contraseña ni dar permiso para otra acción

#### Scenario: Consultorio del token
- **GIVEN** el consultorio activo configurado es distinto del consultorio del token válido
- **WHEN** se confirma por enlace o se agrega consultorio_id al cuerpo
- **THEN** el primer caso opera exclusivamente en el consultorio del token y el segundo responde 422 sin cambios

#### Scenario: Token inválido o de otro propósito
- **WHEN** el token no existe, ya fue usado, venció, tiene tipo de cuenta o pertenece a un ciclo anterior
- **THEN** responde 400 con error genérico de enlace inválido o vencido, sin consumo adicional ni cambios de turno/historial

#### Scenario: Liberado o estado incompatible
- **WHEN** un token válido se presenta para un turno liberado, cancelado, confirmado, atendido o ausente
- **THEN** responde 409 sin confirmar; para liberado indica que debe reservar de nuevo sin revelar datos personales

#### Scenario: Consumo simultáneo y fallo de historial
- **WHEN** dos solicitudes usan el mismo token, o falla guardar el historial de una confirmación
- **THEN** como máximo una confirma y consume; un fallo revierte consumo, estado e historial juntos

### Requirement: Enlace opaco sin persistencia en claro
El sistema SHALL emitir un token opaco de un solo uso por intento de solicitud que se enviará, almacenar solo su hash y asociarlo a turno/ciclo, con vencimiento al inicio. SHALL colocar el token en el fragmento de FRONTEND_BASE_URL/confirmar-turno, sin persistirlo en cuerpos ni logs (RN-30, RN-54; KB 04 token_usuario y flujo 1).

#### Scenario: Solicitud enviada y almacenamiento
- **WHEN** se entrega una solicitud de confirmación
- **THEN** el correo lleva /confirmar-turno#token= con token utilizable y la base conserva su hash, turno y ciclo, sin el token en claro en notificaciones ni historial

#### Scenario: Reintento y vencimiento
- **WHEN** se reintenta una solicitud todavía vigente después de una caída entre SMTP y resultado
- **THEN** puede emitir otro enlace del mismo ciclo sin invalidar el ya recibido; al confirmar uno el estado impide nuevas confirmaciones y al alcanzar el inicio todos los enlaces vencen

### Requirement: Recordatorio según posibilidad real de liberar
El recordatorio SHALL enviarse a pendientes y confirmados del ciclo vigente dentro de su ventana temporal. Para pendientes SHALL advertir liberación solo cuando el consultorio esté en automático, la solicitud email del ciclo actual esté enviada, no exista marca y el turno no haya comenzado; en los demás casos SHALL solo pedir confirmar (RN-26, RN-60).

#### Scenario: Pendiente elegible en automático
- **WHEN** a T-24 se prepara el envío de un pendiente futuro sin marca cuya solicitud email del ciclo actual está enviada en modo automático
- **THEN** el correo recuerda el horario y advierte la liberación al hito configurado si no confirma

#### Scenario: Solicitud no enviada o modo manual
- **WHEN** se prepara un recordatorio de pendiente en manual, marcado, sin solicitud o con solicitud programada, enviando, fallida, omitida o enviada solo en un ciclo anterior
- **THEN** el texto pide confirmar sin anunciar liberación automática

#### Scenario: Confirmado y privacidad
- **WHEN** se prepara el recordatorio de un confirmado con notas, DNI y obra social en su ficha
- **THEN** recuerda el turno sin pedir confirmación ni anunciar liberación, y excluye esos datos y motivos internos

### Requirement: Liberación automática protegida
El barrido SHALL liberar únicamente pendientes futuros sin marca al alcanzar inicio menos horas_liberacion, si el modo es automático y la solicitud email del ciclo actual está enviada. SHALL hacer disponible el hueco y confirmar juntos liberado_en, historial de sistema y aviso email de liberación solo si gana la actualización condicional (RN-22, RN-27, RN-60).

#### Scenario: Borde exacto y antes del hito
- **WHEN** un pendiente cumple RN-60 a 12 horas exactas o a 12 horas y un segundo con parámetro 12
- **THEN** solo el primero se libera, deja un historial liberar de sistema y programa un aviso; el segundo permanece pendiente sin marca

#### Scenario: Confirmado nunca se libera
- **WHEN** el barrido alcanza T-12 de un turno confirmado, incluso nacido confirmado por RN-29
- **THEN** no lo libera ni marca ni agrega historial de decisión automática

#### Scenario: Fallo de historial o aviso
- **WHEN** falla guardar el historial o el aviso asociado a una liberación automática
- **THEN** revierte toda la decisión y conserva el turno para un barrido posterior

### Requirement: Marca única por ciclo cuando no corresponde liberar
Al alcanzar el hito, el sistema SHALL dejar pendiente y marcar una sola vez al turno futuro sin marca si el modo es manual o no hay solicitud email enviada del ciclo actual. La marca SHALL impedir posteriores decisiones automáticas en ese ciclo; el historial marcar_sin_confirmar SHALL confirmarse junto con la marca (RN-28, RN-60).

#### Scenario: Manual y fallos de solicitud
- **WHEN** llega T-12 en manual o en automático con solicitud ausente, programada, enviando, fallida, omitida o enviada solo en otro ciclo
- **THEN** queda pendiente marcado, con una sola entrada marcar_sin_confirmar y sin aviso de liberación

#### Scenario: Envío posterior a la marca
- **WHEN** la solicitud del ciclo pasa a enviada después de marcar y se repite el barrido
- **THEN** el turno sigue pendiente marcado, no se reevalúa ni agrega historial ni aviso automático

#### Scenario: Reprogramación reinicia decisión
- **WHEN** se reprograma un turno marcado a un horario futuro que requiere confirmación
- **THEN** limpia la marca, incrementa ciclo, sale de la lista sin confirmar y se evalúa nuevamente al alcanzar el nuevo hito

### Requirement: Decisión concurrente sin efectos duplicados
Liberar o marcar SHALL exigir de forma condicional consultorio, pendiente, marca nula, ciclo evaluado e inicio posterior al reloj. Solo una actualización ganadora SHALL crear historial y aviso. Una confirmación, cancelación o reprogramación concurrente que gane SHALL impedir aplicar la decisión obsoleta (RN-60, DD-17).

#### Scenario: Dos barridos simultáneos
- **WHEN** dos barridos evalúan el mismo pendiente elegible para liberar o para marcar
- **THEN** ocurre una sola transición o marca y una sola entrada de historial, con como máximo un aviso de liberación

#### Scenario: Cambio concurrente del turno
- **WHEN** confirmar, cancelar o reprogramar gana antes de que se escriba una decisión de barrido basada en la lectura anterior
- **THEN** la decisión obsoleta no modifica el nuevo estado/ciclo ni crea historial o comunicaciones propios

### Requirement: Turnos iniciados quedan fuera de la decisión
La selección y la escritura de liberar/marcar SHALL excluir inicio menor o igual al reloj inyectado. Un pendiente iniciado SHALL quedar para el cierre de atención por personal y no volver a ser candidato en barridos sucesivos (RN-44, RN-60).

#### Scenario: Inicio exacto y pasado
- **WHEN** un pendiente con solicitud enviada llega al inicio exacto o el barrido se recupera después del inicio
- **THEN** no se selecciona ni libera ni marca, sin historial automático, incluso al repetir el barrido

#### Scenario: Inicio alcanzado entre selección y escritura
- **WHEN** el reloj alcanza el inicio luego de seleccionar el turno y antes de intentar liberar o marcar
- **THEN** la escritura verifica el instante actual y no produce ningún efecto
