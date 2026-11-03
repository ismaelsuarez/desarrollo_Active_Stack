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
El despacho SHALL revisar primero vigencia, después intentos y después cupos al retomar una reclamación. Verificación y recuperación SHALL ser siempre vigentes; rechazo de vinculación SHALL requerir correo de cuenta verificado. Todas las salidas de enviando SHALL limpiar la marca (RN-61).

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
