# patient-appointment-management Specification

## Purpose

Permitir que una cuenta de paciente verificada reserve y gestione sus turnos propios con límites consistentes, identidad vigente y protección frente a operaciones concurrentes.

## Requirements

### Requirement: Reserva para ficha vigente y correo verificado
El Paciente SHALL reservar sólo para su ficha vinculada vigente con correo verificado. La reserva SHALL registrar origen online y nacer pendiente, o confirmado por RN-29 si falta menos de horas_confirmacion. Sin ficha SHALL responder 403 pidiendo comunicarse con el consultorio sin DNI ni estado de solicitud (RN-06, RN-29, RN-62–63).

#### Scenario: Registro con ficha o vinculación posterior
- **WHEN** una cuenta verificada con ficha del registro o vinculada posteriormente reserva un horario válido
- **THEN** crea un turno para su propia ficha, origen online, historial y estado pendiente a 48 horas exactas o confirmado a 47 horas 59 minutos con umbral 48

#### Scenario: Correo sin verificar o cuenta sin ficha
- **WHEN** intenta reservar una cuenta sin verificar o sin ficha por solicitud pendiente, rechazada o desvinculación
- **THEN** recibe 403 sin turno ni historial nuevo; sin ficha el mensaje sólo indica que contacte al consultorio para verificar su cuenta

### Requirement: Límites online y máximo futuro atómico
La reserva online SHALL respetar grilla y horizonte local RN-64; fuera de ellos responderá 422. Al llegar a max_turnos_activos_paciente SHALL responder 409 indicando el máximo. SHALL contar sólo futuros pendientes y confirmados, incluidos los creados por personal. Dos reservas simultáneas MUST NOT superar el máximo.

#### Scenario: Último día y máximo configurable
- **WHEN** una cuenta reserva en día 60 y luego día 61 con horizonte 60, o intenta un tercer futuro con máximo 2
- **THEN** admite el día 60 si cumple el resto, rechaza el 61 con 422 y el exceso con 409 indicando 2

#### Scenario: Estados y liberación de cupo
- **WHEN** tiene dos futuros activos, cancela uno y reserva nuevamente, con otros turnos históricos o finales
- **THEN** vuelve a disponer de cupo y los pasados, atendidos, ausentes, cancelados y liberados no consumen ese máximo

#### Scenario: Dos reservas y un cupo
- **WHEN** dos transacciones de la misma ficha reservan horarios libres distintos cuando sólo resta un cupo
- **THEN** una responde 201 y la otra 409 con el máximo, sin superar el límite ni dejar historial parcial

#### Scenario: Grilla y personal
- **WHEN** un paciente pide 09:07 con bloque desde 09:00 y grilla 15, o personal reserva fuera del horizonte o superando el máximo
- **THEN** el paciente recibe 422; las reservas de personal conservan su exención de días y cantidad

### Requirement: Lectura propia consulta vínculo actual
GET /api/v1/turnos SHALL listar sólo turnos de la ficha vigente del Paciente y devolver 200 vacío sin ficha. El detalle e historial por identificador y toda acción SHALL comprobar ese mismo vínculo. MUST NOT usar una ficha almacenada en JWT ni mostrar turnos ajenos (RN-06, RN-35, RN-55, RN-63).

#### Scenario: Titular actual y turno ajeno
- **WHEN** el titular lista sus turnos y consulta detalle o historial propio y luego un identificador ajeno
- **THEN** ve sólo sus turnos y recibe 404 para el ajeno sin datos personales de otra cuenta

#### Scenario: JWT anterior a desvincular
- **WHEN** se elimina el vínculo en la base y el mismo JWT previo lista turnos o intenta ver, confirmar, cancelar o mover uno de su antigua ficha
- **THEN** la lista responde 200 vacía y las operaciones por identificador responden 404 sin cambios

### Requirement: Acciones propias según estado y ventana
El titular SHALL confirmar pendientes desde su cuenta y cancelar o reprogramar pendiente/confirmado hasta ahora <= inicio - horas_limite_paciente. La respuesta de sus turnos SHALL indicar acciones habilitadas según esas políticas. Fuera del plazo SHALL responder 403 con teléfono del consultorio; ajenos 404 y estados incompatibles 403 (RN-18–19, RN-30, RN-33, RN-35).

#### Scenario: Cancelación en límite y fuera de plazo
- **WHEN** el titular cancela a 24 horas exactas o a 23 horas 59 minutos con límite 24
- **THEN** el primer caso cancela con historial y libera el horario; el segundo responde 403 con teléfono sin cambios

#### Scenario: Confirmación y estados finales
- **WHEN** el titular confirma un pendiente o intenta confirmar un liberado o cancelar un atendido
- **THEN** confirma el pendiente con historial y rechaza estados incompatibles con 403; las acciones de lectura concuerdan con esos permisos

### Requirement: Reprogramación propia conserva duración y atomicidad
La reprogramación del Paciente SHALL conservar identificador y duración actual, cumplir ventana, grilla, horizonte y agenda, y excluir su turno de la ocupación. MUST NOT consumir un cupo nuevo. Un cambio exitoso SHALL reiniciar ciclo/estado según RN-29/RN-32; un rechazo MUST preservar turno, ciclo, marca e historial (RN-37, RN-64).

#### Scenario: Ajuste previo y cupo lleno
- **WHEN** el titular con máximo de futuros mueve un turno de 45 minutos ajustado por personal a un destino válido
- **THEN** conserva id y 45 minutos, no suma cupo, incrementa ciclo, limpia marca y aplica estado por anticipación

#### Scenario: Destino inválido u ocupado
- **WHEN** intenta mover a un horario fuera de grilla, a día 61 con máximo 60 o a un intervalo ocupado
- **THEN** responde 422 por grilla/horizonte o 409 por ocupación y conserva todos los datos del original

### Requirement: Conflictos ofrecen alternativas sin asegurar reserva
Un conflicto de ocupación en reserva o reprogramación online SHALL responder 409 con intervalos alternativos cercanos válidos para ese profesional y duración. Una lista vacía SHALL ser válida si no hay alternativas en el horizonte. MUST NOT mostrar ocupantes ni prometer que un intervalo seguirá libre (RN-17, RN-24).

#### Scenario: Dos cuentas y mismo hueco
- **WHEN** dos cuentas habilitadas reservan el mismo hueco con transacciones independientes
- **THEN** una obtiene 201 y la otra 409 con alternativas recalculadas sin ese hueco, con un único turno e historial de alta

#### Scenario: Sobreturno o agenda llena
- **WHEN** la solicitud directa intersecta un sobreturno activo o no hay otro hueco en el horizonte
- **THEN** responde 409 sin efectos parciales y las alternativas excluyen sobreturnos o son una lista vacía

### Requirement: Integración con hitos sin adelantar envíos
Las reservas y reprogramaciones online exitosas SHALL invocar el punto de integración de hitos del ciclo en su transacción. C-09 MUST NOT enviar ni programar correo real, barrido o confirmación por enlace; el adaptador nulo SHALL conservar el comportamiento sin efectos de C-07 (CHANGES C-09/C-16).

#### Scenario: Reserva y reprogramación exitosas
- **WHEN** se reserva o mueve un turno propio correctamente
- **THEN** se invoca la integración con turno y ciclo vigentes, y el adaptador nulo no agrega notificaciones

#### Scenario: Fallo de integración
- **WHEN** la integración falla antes del commit
- **THEN** se revierte turno e historial y la API no anuncia éxito
