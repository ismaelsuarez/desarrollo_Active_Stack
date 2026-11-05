# appointment-booking Specification

## Purpose

Permite reservar un turno de un paciente con un profesional y garantiza que dos turnos activos del mismo profesional nunca ocupen el mismo tiempo, incluso cuando dos reservas compiten a la vez.

## Requirements

### Requirement: Crear un turno en un horario libre
El sistema SHALL crear un turno regular para una ficha, profesional y prestación del mismo consultorio, con agenda válida y box fijo del profesional. Recepción/Administrador SHALL poder crearlo para fichas sin cuenta. El estado SHALL ser pendiente o confirmado por confirmación manual, y MUST ser confirmado si faltan menos de horas_confirmacion (RN-10, RN-14, RN-23, RN-29).

#### Scenario: Turno en un horario libre
- **GIVEN** un profesional libre, prestación de 30 minutos, agenda válida y reloj a más de 48 horas del inicio
- **WHEN** Recepción crea el turno sin confirmación manual
- **THEN** queda guardado con identificador propio, pendiente, no sobreturno y con el box fijo del profesional

#### Scenario: Otro profesional en el mismo horario
- **GIVEN** un turno activo del profesional A de 10:00 a 10:30 y un profesional B con agenda válida
- **WHEN** se crea un turno para B a las 10:00
- **THEN** B obtiene su turno y el de A no cambia

#### Scenario: Ficha sin cuenta y confirmación manual
- **GIVEN** una ficha del consultorio con usuario_id nulo y un horario válido a más de 48 horas
- **WHEN** Recepción crea el turno confirmándolo por teléfono
- **THEN** queda confirmado con esa ficha y el historial identifica al personal que confirmó

#### Scenario: Anticipación menor al umbral
- **GIVEN** horas_confirmacion 48 y un inicio válido a 47 horas 59 minutos del reloj
- **WHEN** Recepción crea un turno
- **THEN** nace confirmado y el historial distingue la asignación por RN-29 de una confirmación del paciente

#### Scenario: Anticipación exactamente igual al umbral
- **GIVEN** horas_confirmacion 48 y un inicio válido exactamente a 48 horas
- **WHEN** Recepción crea el turno sin confirmación manual
- **THEN** nace pendiente

### Requirement: La duración del turno es la de la prestación
El fin SHALL ser inicio más duración de la prestación o, si Recepción/Administrador fija otra, más la duración ajustada positiva en múltiplos de minutos_granularidad. El cliente MUST NOT fijar fin. Cambiar la prestación no altera turnos existentes y reprogramar conserva la duración actual salvo ajuste autorizado (RN-13, RN-15, RN-64).

#### Scenario: Prestación de 30 minutos
- **WHEN** se crea un turno sin ajuste con prestación de 30 minutos a las 10:00
- **THEN** termina a las 10:30

#### Scenario: Prestación de 60 minutos
- **WHEN** se crea un turno sin ajuste con prestación de 60 minutos a las 15:15
- **THEN** termina a las 16:15

#### Scenario: Duración ajustada válida
- **GIVEN** granularidad 15 y una prestación de 30 minutos
- **WHEN** Recepción fija 45 minutos para un turno en horario válido
- **THEN** se conserva el ajuste y el fin es inicio más 45 minutos

#### Scenario: Duración ajustada inválida
- **GIVEN** granularidad 15
- **WHEN** Recepción fija duración 20, cero o negativa
- **THEN** recibe 422 y no se guarda el turno

#### Scenario: El catálogo no se redondea a la grilla
- **GIVEN** una prestación de 20 minutos y granularidad 15
- **WHEN** se reserva sin ajuste con inicio en grilla y dentro de un bloque
- **THEN** el turno conserva los 20 minutos de la prestación

### Requirement: Rechazar un turno superpuesto del mismo profesional
El sistema MUST rechazar con horario ocupado la creación regular que intersecte otro turno activo del mismo profesional y consultorio (RN-17). Son activos pendiente, confirmado, atendido y ausente. También SHALL rechazar con 409 un regular sobre un sobreturno activo existente. Un rechazo MUST dejar turno e historial sin persistencia parcial.

#### Scenario: Superposición parcial
- **GIVEN** un turno activo del profesional A de 10:00 a 10:30
- **WHEN** se crea otro de A de 10:15 a 10:45
- **THEN** falla con horario ocupado y sigue existiendo un único turno

#### Scenario: Mismo horario exacto
- **GIVEN** un turno activo de A de 10:00 a 10:30
- **WHEN** se crea otro de A con el mismo intervalo
- **THEN** falla con horario ocupado

#### Scenario: Turno nuevo que contiene a uno existente
- **GIVEN** un turno activo de A de 10:15 a 10:45
- **WHEN** se crea otro de A de 10:00 a 11:00
- **THEN** falla con horario ocupado

#### Scenario: Turno nuevo contenido por uno existente
- **GIVEN** un turno activo de A de 10:00 a 11:00
- **WHEN** se crea otro de A de 10:15 a 10:45
- **THEN** falla con horario ocupado

#### Scenario: Superposición por el extremo final
- **GIVEN** un turno activo de A de 10:00 a 10:30
- **WHEN** se crea otro de A de 09:45 a 10:15
- **THEN** falla con horario ocupado

#### Scenario: Sobreturno activo ya existente
- **GIVEN** un sobreturno activo de A de 10:00 a 10:30 preparado mediante fixture
- **WHEN** Recepción crea un regular de A a las 10:00
- **THEN** recibe 409 sin un nuevo turno ni historial

### Requirement: Los turnos contiguos no se superponen
El intervalo de un turno SHALL incluir su inicio y excluir su fin. Un turno que empieza en el instante exacto en que termina otro del mismo profesional, o que termina en el instante exacto en que otro empieza, MUST aceptarse.

#### Scenario: Empieza cuando termina otro
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:30 del mismo día
- **THEN** el turno queda guardado de 10:30 a 11:00

#### Scenario: Termina cuando empieza otro
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:30 a 11:00
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno queda guardado de 10:00 a 10:30

### Requirement: Los turnos cancelados y liberados no ocupan el horario
Un turno en estado `cancelado` o `liberado` MUST NOT impedir la creación de otro turno del mismo profesional en su mismo horario (RN-17, RN-22).

#### Scenario: Horario de un turno cancelado
- **GIVEN** un turno `cancelado` del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno nuevo queda guardado en estado `pendiente`

#### Scenario: Horario de un turno liberado
- **GIVEN** un turno `liberado` del profesional A el 2026-11-02 de 10:00 a 10:30
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio a las 10:00 del mismo día
- **THEN** el turno nuevo queda guardado en estado `pendiente`

### Requirement: Solo una de dos reservas simultáneas prospera
Ante dos creaciones regulares simultáneas del mismo profesional y consultorio con intervalos superpuestos, el sistema MUST guardar exactamente una y rechazar la otra con horario ocupado, aun si ambas vieron libre el hueco. En la API el conflicto SHALL responder 409 sin efectos parciales (RN-24).

#### Scenario: Dos creaciones simultáneas del mismo horario
- **GIVEN** un profesional A sin turnos en un horario válido
- **WHEN** dos creaciones independientes piden simultáneamente el mismo hueco
- **THEN** exactamente una guarda su turno y su historial; la otra recibe horario ocupado y el conteo final es un turno

#### Scenario: Dos solicitudes API compiten
- **GIVEN** dos solicitudes autorizadas del mismo consultorio y un intervalo libre
- **WHEN** ambas reservan ese intervalo para el mismo profesional con transacciones independientes
- **THEN** una responde con éxito y otra 409 horario ocupado, sin determinar de antemano cuál gana

### Requirement: El profesional y la prestación pertenecen al consultorio
El sistema MUST rechazar la creación de un turno cuyo profesional o cuya prestación no existen en el consultorio indicado, con un error que distingue cuál de los dos falta. Un profesional o una prestación de otro consultorio se tratan como inexistentes (RN-55). Un turno rechazado no se guarda.

#### Scenario: Profesional inexistente
- **WHEN** se crea un turno en el consultorio 1 con un identificador de profesional que no existe
- **THEN** la creación falla con el error "profesional inexistente"
- **AND** no se guarda ningún turno

#### Scenario: Prestación de otro consultorio
- **GIVEN** una prestación que pertenece al consultorio 2
- **WHEN** se crea un turno en el consultorio 1 con esa prestación y un profesional del consultorio 1
- **THEN** la creación falla con el error "prestación inexistente"
- **AND** no se guarda ningún turno

### Requirement: El inicio del turno es un instante con zona horaria
El sistema MUST rechazar la creación de un turno cuyo inicio no indica zona horaria, para que el horario no dependa de la configuración del servidor. Un turno rechazado no se guarda.

#### Scenario: Inicio sin zona horaria
- **WHEN** se crea un turno con el inicio `2026-11-02 10:00` sin zona horaria
- **THEN** la creación falla con el error "el inicio debe indicar zona horaria"
- **AND** no se guarda ningún turno

#### Scenario: Mismo instante expresado en otra zona
- **GIVEN** un turno activo del profesional A el 2026-11-02 de 10:00 a 10:30, hora de Buenos Aires
- **WHEN** se crea un turno del profesional A con una prestación de 30 minutos e inicio el 2026-11-02 a las 13:00 UTC
- **THEN** la creación falla con el error "horario ocupado"

### Requirement: Reserva dentro de un bloque y sin excepciones
La reserva SHALL caber completa en un único bloque semanal del profesional y MUST NOT intersectar bloqueos globales o propios. El inicio SHALL pertenecer a la grilla anclada al inicio de ese bloque. Entradas fuera de horario o grilla MUST responder 422 sin persistir (RN-14, RN-64).

#### Scenario: Extremos del bloque
- **GIVEN** un bloque 09:00–12:00 con grilla 15 y sin excepciones
- **WHEN** se reserva 09:00–09:30 o 11:30–12:00
- **THEN** el intervalo es válido

#### Scenario: Fuera de grilla
- **GIVEN** un bloque desde 09:00 y granularidad 15
- **WHEN** se solicita inicio 09:07
- **THEN** recibe 422 sin guardar el turno

#### Scenario: Turno atraviesa pausa o fin de bloque
- **GIVEN** bloques 09:00–12:00 y 13:00–17:00
- **WHEN** se solicita 11:45–12:15 o 11:45–13:15
- **THEN** recibe 422 porque el intervalo no cabe en un bloque

#### Scenario: Excepción global o propia
- **GIVEN** un bloqueo que afecta total o parcialmente el turno solicitado
- **WHEN** Recepción intenta reservarlo
- **THEN** recibe 422 sin crear turno ni historial

### Requirement: El personal no hereda límites de reserva del paciente
La creación por Recepción/Administrador MUST NOT aplicar el máximo de días de anticipación ni el máximo de turnos activos del paciente; SHALL conservar las validaciones de agenda, duración y solapamiento (RN-64 e).

#### Scenario: Más de sesenta días
- **WHEN** Recepción reserva un intervalo válido y libre a 61 días con parámetro máximo 60
- **THEN** el turno se acepta

#### Scenario: Tercer turno activo
- **GIVEN** una ficha con dos turnos futuros y máximo de paciente 2
- **WHEN** Administrador crea un tercero válido sin solapamiento
- **THEN** se acepta

### Requirement: Entrada de creación respeta autoridad del servidor
POST /api/v1/turnos SHALL habilitar el alta por personal autorizado y Paciente verificado con ficha vigente, resolviendo consultorio desde el principal. La entrada MUST rechazar campos no declarados con 422, incluido consultorio_id o fin. Para Paciente SHALL derivar ficha y origen online del servidor y rechazar paciente_id, duracion_min y confirmar enviados por cliente (RN-55, RN-62, RN-64).

#### Scenario: Consultorio enviado por cliente
- **WHEN** Recepción envía consultorio_id o un fin calculado en el payload
- **THEN** recibe 422 y no se persiste la reserva

#### Scenario: Recurso ajeno
- **WHEN** Recepción intenta reservar con una ficha, profesional o prestación de otro consultorio
- **THEN** recibe 404 sin revelar el recurso ni crear registros

#### Scenario: Entrada mínima online
- **WHEN** el Paciente habilitado envía profesional_id, prestacion_id e inicio con zona en un horario válido
- **THEN** el servidor reserva para su ficha vigente, calcula duración y origen online y responde 201

#### Scenario: Campos reservados al personal o al servidor
- **WHEN** un Paciente envía paciente_id, duracion_min, confirmar, origen, fin o consultorio_id, incluso con valores propios o null
- **THEN** recibe 422 sin turno ni historial; el personal conserva sus campos actuales paciente_id, duracion_min y confirmar
