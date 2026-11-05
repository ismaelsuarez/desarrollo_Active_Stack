# Spec Delta

## Purpose

Permitir elegir horarios libres de atención sin iniciar sesión, respetando la agenda real del consultorio y sin revelar datos de otros pacientes.

## ADDED Requirements

### Requirement: Catálogo público mínimo del consultorio
Las lecturas GET /api/v1/publico/consultorio, /prestaciones y /profesionales bajo el mismo prefijo publico SHALL funcionar sin ingreso y resolver el consultorio en el servidor. SHALL mostrar datos públicos del consultorio y sólo prestaciones y profesionales activos, sin cuentas ni fichas (RN-59; US-013).

#### Scenario: Catálogo sin sesión
- **WHEN** una persona consulta las tres lecturas sin token
- **THEN** recibe nombre, dirección, teléfono y zona del consultorio, prestaciones activas con id/nombre/duración y profesionales activos con id/nombre operativo, sin credenciales ni datos de pacientes

#### Scenario: Aislamiento y entradas estrictas
- **WHEN** existen catálogos de otro consultorio o se intenta elegir consultorio_id por query
- **THEN** sólo se muestran recursos del consultorio configurado y consultorio_id se rechaza con 422 sin cambiar la configuración

### Requirement: Disponibilidad respeta agenda y ocupación
GET /api/v1/publico/disponibilidad SHALL aceptar profesional_id, prestacion_id y fecha local y devolver intervalos libres para la duración vigente de la prestación. Cada intervalo SHALL caber en un bloque y excluir excepciones globales o propias y turnos ocupantes, incluidos sobreturnos activos. Cancelados y liberados MUST NOT ocupar (RN-11–17, RN-22).

#### Scenario: Bloque, excepción y turnos
- **WHEN** se consulta un bloque 09:00–12:00 con prestación 30 minutos, bloqueo 10:00–10:30 y turno 11:00–11:30
- **THEN** no ofrece intervalos que intersectan esos obstáculos y permite intervalos contiguos a sus extremos

#### Scenario: Duración y pausa
- **WHEN** una prestación de 60 minutos se consulta con bloques 09:00–10:00 y 10:30–11:00
- **THEN** ofrece 09:00–10:00 si está libre y no parte turnos entre bloques ni ofrece uno que exceda 11:00

#### Scenario: Sobreturnos y estados sin ocupación
- **WHEN** hay un sobreturno activo y turnos cancelados o liberados preparados en la base
- **THEN** excluye el sobreturno y permite horarios de los cancelados y liberados sin exponer identificadores de turnos

#### Scenario: Recurso inválido o día sin atención
- **WHEN** profesional o prestación no existe, es ajeno o está inactivo, o el día no tiene bloques disponibles
- **THEN** responde 404 por referencia no disponible o 200 con lista vacía por día sin atención

### Requirement: Grilla y horizonte de días locales
Los inicios ofrecidos SHALL anclarse al comienzo de cada bloque y avanzar por minutos_granularidad sin redondear la duración del catálogo. SHALL excluir horarios pasados y fechas posteriores a hoy local más dias_anticipacion_maxima, incluyendo el último día permitido (RN-64; DD-27).

#### Scenario: Granularidad configurable
- **WHEN** el bloque empieza 09:10, granularidad vale 15 y luego cambia a 20
- **THEN** los inicios avanzan 09:10,09:25,09:40 y luego 09:10,09:30,09:50 respectivamente si caben y están libres

#### Scenario: Último día y zona
- **WHEN** el máximo es 60 y se consultan días locales 60 y 61 desde el reloj, incluso cerca de medianoche UTC
- **THEN** el día 60 puede ofrecer intervalos y el 61 devuelve lista vacía; la fecha de referencia es la del consultorio

#### Scenario: Hoy y prestación no múltiplo
- **WHEN** se consulta hoy con una prestación de 20 minutos y grilla 15
- **THEN** sólo se ofrecen inicios futuros en grilla y los intervalos conservan 20 minutos

### Requirement: Lecturas públicas limitadas y privadas
Las cuatro lecturas públicas SHALL limitar solicitudes por origen y proceso, responder 429 al exceder su cuota y permitir reintentar al renovar la ventana. MUST NOT exigir Redis ni incluir datos de pacientes, consultas privadas o credenciales en respuesta o logs (RN-54, RN-58; CHANGES C-09).

#### Scenario: Cuota y recuperación
- **WHEN** un origen agota la cuota configurada y consulta otra lectura pública, y luego transcurre la ventana
- **THEN** recibe 429 con Retry-After durante el exceso y vuelve a consultar normalmente al renovarse la ventana

#### Scenario: Otro origen y datos mínimos
- **WHEN** otro origen consulta después del exceso anterior y existen turnos con datos personales sintéticos
- **THEN** mantiene su cuota independiente y sólo recibe catálogos o intervalos, sin identidad de ocupantes ni valores privados en logs
