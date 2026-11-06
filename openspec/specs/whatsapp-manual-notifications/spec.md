# whatsapp-manual-notifications Specification

## Purpose

Permitir que Recepción prepare y registre avisos manuales de WhatsApp de forma privada y vinculada al ciclo del turno.

## Requirements

### Requirement: Normalización y mensaje mínimo
El sistema SHALL normalizar teléfonos internacionales con Argentina como país predeterminado, crear enlaces `https://wa.me/` codificados y limitar el mensaje a nombre del paciente, fecha, hora, profesional, consultorio y acción requerida (RN-53, RN-54).

#### Scenario: Formatos de teléfono
- **WHEN** se prepara un mensaje para teléfonos argentinos con formato local o internacionales con prefijo explícito
- **THEN** el enlace contiene un número internacional normalizado y el texto codificado, sin símbolos de formato en el número

#### Scenario: Datos sensibles y caracteres especiales
- **WHEN** el paciente tiene DNI, obra social, notas o prestación y los nombres contienen acentos o símbolos
- **THEN** ninguno de esos datos sensibles figura en mensaje ni enlace y el texto permitido se recupera intacto al decodificarlo

#### Scenario: Teléfono inexistente o inválido
- **WHEN** no existe teléfono utilizable o no puede normalizarse
- **THEN** no se genera enlace ni se inventa destinatario, no se bloquea el turno ni el correo y el diagnóstico técnico no expone datos personales

### Requirement: Preparación de hitos y hechos
El barrido SHALL preparar una fila WhatsApp para solicitud, recordatorio, liberación y avisos por cancelación o reprogramación del personal, respetando el ciclo, vigencia por tipo e idempotencia por turno, tipo, canal y ciclo (RN-25, RN-26, RN-32, US-034).

#### Scenario: Hitos vigentes
- **WHEN** se alcanzan los hitos de solicitud o recordatorio de un turno elegible con teléfono utilizable
- **THEN** cada hito genera una fila preparada con mensaje y enlace sin depender de que exista o se envíe el correo

#### Scenario: Barrido repetido o simultáneo
- **WHEN** dos barridos concurren o se repite el mismo barrido para el mismo turno, tipo y ciclo
- **THEN** hay como máximo una notificación WhatsApp correspondiente y un nuevo ciclo permite otra

#### Scenario: Aviso de hecho consumado
- **WHEN** un cambio del personal o una liberación ganadora ocurre y luego corre el barrido
- **THEN** se prepara el aviso del hecho aunque el turno después cambie de estado o ciclo, sin duplicarlo

#### Scenario: Ventana de hito superada
- **WHEN** el barrido se retrasa hasta el hito siguiente, o el turno dejó de ser elegible antes de preparar una solicitud o recordatorio
- **THEN** no crea un mensaje obsoleto ni habilita la liberación automática por una preparación de WhatsApp

#### Scenario: Recordatorio y liberación
- **WHEN** se prepara un recordatorio para un pendiente
- **THEN** solo advierte liberación si se cumplen las condiciones de RN-26 y RN-60, y en los demás casos solicita confirmar sin prometer liberación

### Requirement: Vigencia y carreras de mensajes preparados
Al cancelar, liberar o reprogramar SHALL omitirse las solicitudes y recordatorios `preparada` del ciclo afectado; los avisos de hechos consumados SHALL conservarse. La preparación concurrente SHALL respetar el mismo estado y ciclo vigentes.

#### Scenario: Reprogramación de turno
- **WHEN** se reprograma un turno con solicitud y recordatorio preparados del ciclo anterior y un aviso preparado de reprogramación
- **THEN** las dos primeras pasan a omitida y dejan de listarse; el aviso del hecho permanece preparado

#### Scenario: Cancelación o liberación concurrente
- **WHEN** un barrido y una cancelación, liberación o reprogramación compiten por el mismo hito
- **THEN** no queda preparada una solicitud ni recordatorio obsoletos en la bandeja después de confirmadas ambas operaciones

### Requirement: Consultar enlace y marcar envío manual
Recepción y Administrador SHALL obtener el enlace de una notificación WhatsApp preparada de su consultorio y marcarla `enviada_manual` con fecha y actor. Abrir el enlace no SHALL registrar un envío ni verificar su entrega.

#### Scenario: Enlace y registro
- **WHEN** Recepción obtiene el enlace de una preparada y luego la marca enviada
- **THEN** recibe el enlace prellenado y la transición registra actor y fecha del servidor, sin afirmar entrega a WhatsApp

#### Scenario: Roles y consultorios
- **WHEN** un rol distinto de Recepción o Administrador accede o el identificador pertenece a otro consultorio
- **THEN** se rechaza sin revelar el contenido ni modificar la notificación

#### Scenario: Estado incompatible o marca concurrente
- **WHEN** se solicita el enlace o se intenta marcar una omitida, de otro canal o ya marcada, o dos operadores marcan la misma fila a la vez
- **THEN** solo una transición desde preparada puede confirmarse, se rechazan los demás intentos y se conserva el actor ganador
