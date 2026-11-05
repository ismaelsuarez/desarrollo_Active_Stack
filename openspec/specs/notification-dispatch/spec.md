# notification-dispatch Specification

## Purpose

Entregar los correos programados de cuenta con reintentos acotados, recuperación ante caídas y cupos diarios, sin duplicar reclamaciones activas ni prometer entrega exactamente una vez.

## Requirements

### Requirement: Programación y envío de cuenta
El sistema SHALL programar verificación y recuperación junto con el hecho que las origina y solicitar despacho inmediato después de confirmar. Un fallo de SMTP SHALL conservar el trabajo durable para reintento. Los enlaces SHALL llevar el token en el fragmento de FRONTEND_BASE_URL, sin DNI, contraseña ni otros datos sensibles (RN-03, RN-31).

#### Scenario: Verificación y recuperación
- **WHEN** se programa uno de esos correos
- **THEN** se intenta el envío en segundo plano y su enlace usa /verificar-email#token= o /restablecer-password#token= respectivamente

#### Scenario: Fallo de transporte
- **WHEN** SMTP falla
- **THEN** no revierte la cuenta y conserva la notificación reintentable o fallida según intentos, sin persistir ni registrar secretos del error

### Requirement: Reclamación exclusiva y resultado condicionado
El despacho SHALL reclamar solo una notificación email vencida programada o con reclamación expirada. SHALL confirmar su marca e incremento de intentos antes de enviar fuera de toda transacción y solo registrar resultado si conserva la reclamación propia (RN-61).

#### Scenario: Doble despacho concurrente
- **WHEN** dos despachadores intentan tomar la misma notificación
- **THEN** solo uno obtiene la reclamación y envía mientras esté vigente

#### Scenario: Resultado exitoso
- **WHEN** finaliza el envío y sigue vigente la reclamación propia
- **THEN** marca enviada, registra la hora y limpia la reclamación

#### Scenario: Fallo reintentable o definitivo
- **WHEN** falla el envío
- **THEN** vuelve a programada si no agotó intentos o pasa a fallida si los agotó, limpiando siempre la reclamación

#### Scenario: Resultado tardío
- **WHEN** otro despachador retomó una reclamación vencida antes de que llegue el resultado del primer envío
- **THEN** descarta ese resultado sin modificar estado ni intentos del segundo y registra solo la pérdida de reclamación sin datos personales

#### Scenario: Caída tras enviar
- **WHEN** ocurre una caída después del envío y antes de guardar el resultado
- **THEN** conserva enviando y al expirar la reclamación permite reenviar; la entrega es al menos una vez

### Requirement: Recuperación de reclamaciones vencidas
El despacho SHALL revisar vigencia, intentos y cupos en ese orden, al reclamar programadas o retomar vencidas. Verificación y recuperación SHALL ser siempre vigentes; rechazo de vinculación SHALL requerir correo verificado. Solicitud y recordatorio SHALL requerir turno, ciclo, estado e inicio vigentes; avisos de hechos consumados SHALL conservar vigencia. Toda salida de enviando SHALL limpiar la marca (RN-61; KB 04 Vigencia por tipo).

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
- **WHEN** una solicitud de confirmación programada o vencida corresponde al ciclo vigente de un turno futuro pendiente, o el turno ya quedó confirmado
- **THEN** envía solo en el primer caso y en el segundo omite sin enviar ni consumir otro intento

#### Scenario: Recordatorio y bordes temporales
- **WHEN** un recordatorio programado o vencido corresponde a un turno pendiente o confirmado, del mismo ciclo
- **THEN** puede enviarse solo si inicio es posterior al reloj y se omite cuando inicio es igual o anterior

#### Scenario: Cambio de ciclo o turno sin vigencia
- **WHEN** una solicitud o recordatorio tiene otro ciclo o su turno está cancelado, liberado, atendido, ausente o no existe
- **THEN** pasa a omitida sin enviar, aunque los cupos estén completos o sus intentos agotados, y limpia la reclamación anterior

#### Scenario: Avisos de hechos consumados
- **WHEN** hay avisos de liberacion, cancelacion_por_personal, reprogramacion_por_personal, resumen_reserva o cancelacion_por_paciente y el turno cambió de estado, ciclo o ya comenzó
- **THEN** siguen siendo elegibles por tipo y se envían si hay intentos y cupo, sin exigir un turno activo

#### Scenario: Tope no bloquea resolución sin envío
- **WHEN** se alcanzó el tope diario y hay una enviando vencida elegible, otra no vigente y otra agotada
- **THEN** conserva la elegible con sus intentos y marca originales, omite la no vigente y falla la agotada sin enviar ni contarlas como reclamaciones vigentes

### Requirement: Cupo total y cupo de cuenta
Antes de reclamar para enviar, el sistema SHALL comprobar EMAIL_DAILY_LIMIT y para tipos de cuenta también EMAIL_DAILY_LIMIT_ACCOUNT. SHALL contar emails enviados dentro del día del consultorio y reclamaciones no vencidas; al alcanzar EMAIL_DAILY_ALERT_RATIO SHALL alertar sin datos sensibles (DD-29).

#### Scenario: Cupo de cuenta completo
- **WHEN** se alcanzó el cupo de cuenta pero queda cupo total
- **THEN** una verificación permanece programada sin incrementar intentos y un correo de turno preparado para la prueba puede enviarse

#### Scenario: Tope total completo
- **WHEN** se alcanzó el tope total
- **THEN** no reclama nuevos envíos ni retoma vencidos que enviarían; conserva estado e intentos

#### Scenario: Conteo y cambio de día
- **WHEN** hay emails enviados del día, enviando vigente y enviando vencido
- **THEN** cuenta los dos primeros, excluye el vencido y aplica el día calendario de la zona del consultorio, reabriendo el cupo al siguiente día

#### Scenario: Alerta
- **WHEN** el conteo alcanza el ochenta por ciento configurado
- **THEN** emite la alerta y al cien por ciento deja de reclamar correos

### Requirement: Configuración y transporte SMTP
La configuración SHALL aceptar SMTP con STARTTLS en 587 y un transporte local sin TLS para Mailpit. SHALL rechazar cupo de cuenta mayor o igual al total y ventana de registro mayor a 1440 minutos. El transporte SHALL tener timeout menor al TTL de reclamación y no exponer credenciales.

#### Scenario: Configuración válida
- **WHEN** se configura el transporte local o SMTP STARTTLS y cupos válidos
- **THEN** permite enviar mensajes de texto y recibirlos en Mailpit durante las pruebas de integración

#### Scenario: Configuración inconsistente
- **WHEN** el cupo de cuenta iguala o supera el total, la ventana excede retención o el timeout alcanza el TTL
- **THEN** rechaza el arranque con errores que no contienen secretos

### Requirement: Programación única por ciclo
La programación SHALL impedir dos notificaciones del mismo turno, tipo, canal y ciclo, incluso con concurrencia. SHALL copiar el ciclo vigente del turno, conservar filas históricas y permitir múltiples correos de cuenta con turno nulo (RN-32, RN-61).

#### Scenario: Repetición y carrera de programación
- **WHEN** se programa dos veces o concurrentemente el mismo aviso del mismo turno, tipo, canal y ciclo
- **THEN** persiste una sola fila sin revertir la operación válida por una duplicación idempotente

#### Scenario: Nuevos ciclos y correos sin turno
- **WHEN** cambia el ciclo, el tipo o el canal, o se programan varios correos de cuenta sin turno
- **THEN** permite esas filas distintas sin confundir la deduplicación con la exclusividad de reclamaciones

### Requirement: Avisos transaccionales por cambios del personal
Una cancelación o reprogramación exitosa por Recepción o Administrador SHALL programar su aviso email en la misma transacción del turno e historial, con el ciclo vigente del hecho. Fallar en esa programación MUST revertir todo. El envío posterior no SHALL revertir el cambio de turno (US-034, RN-31).

#### Scenario: Cancelación y reprogramación por personal
- **WHEN** el personal cancela o reprograma correctamente un turno con email de contacto utilizable
- **THEN** confirma junto al turno e historial un aviso del tipo correspondiente, con el ciclo vigente o el nuevo de la reprogramación, que no se omite por ese cambio

#### Scenario: Fallo de programación o transporte
- **WHEN** falla guardar el aviso, o falla su envío después del commit
- **THEN** en el primer caso revierte turno, historial y aviso; en el segundo conserva el cambio y aplica el reintento acotado del correo

#### Scenario: Paciente y contacto ausente
- **WHEN** el cambio lo realiza el paciente o no existe email de contacto utilizable
- **THEN** no crea un aviso por personal ni inventa un destinatario; la ausencia de contacto no impide el cambio de turno y es observable sin datos personales

### Requirement: Plantillas de aviso con datos mínimos
Los correos de cambios del personal SHALL limitarse a nombre, fecha, hora, profesional, consultorio y acción. MUST excluir DNI, obra social, observaciones, motivo interno, datos de salud y secretos en cuerpo y asunto (RN-54).

#### Scenario: Contenido y privacidad
- **WHEN** el turno contiene un motivo interno y observaciones sensibles y se genera su aviso
- **THEN** el mensaje recibido contiene el horario y acción pertinentes y no incluye esos campos, DNI, obra social ni credenciales

#### Scenario: Aviso de reprogramación
- **WHEN** el personal mueve el turno y el aviso se entrega después de otro cambio
- **THEN** el correo representa el hecho y horario capturados al programarlo, sin reconstruir su contenido desde el estado posterior
