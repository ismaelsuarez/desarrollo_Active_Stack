# Spec Delta

## Purpose

Permitir a pacientes consultar disponibilidad pública y gestionar sus turnos propios mediante una interfaz accesible.

## ADDED Requirements

### Requirement: Consulta pública de disponibilidad
La interfaz SHALL mostrar los datos públicos del consultorio y permitir elegir prestación, profesional, fecha y un intervalo ofrecido sin iniciar sesión. SHALL presentar estados de carga, lista vacía y error sin revelar datos de otros pacientes.

#### Scenario: Consulta sin cuenta
- **WHEN** un visitante elige prestación, profesional y fecha con horarios disponibles
- **THEN** ve los intervalos devueltos con su fecha y hora del consultorio sin iniciar sesión.

#### Scenario: Sin resultados o con límite
- **WHEN** la API devuelve una lista vacía o 429
- **THEN** la interfaz comunica respectivamente que no hay horarios o que debe volver a intentar más tarde.

### Requirement: Reserva con cuenta habilitada
La interfaz SHALL conducir al visitante sin sesión a ingresar o registrarse antes de reservar y MUST NOT crear una reserva hasta que el paciente solicite expresamente enviarla. Una cuenta sin verificar o sin ficha SHALL recibir orientación recuperable sin revelar DNI ni estado de vinculación.

#### Scenario: Visitante inicia reserva
- **WHEN** un visitante selecciona un horario e intenta reservar
- **THEN** puede ingresar o registrarse y recibe indicación de verificar su correo antes de completar la reserva.

#### Scenario: Paciente habilitado reserva
- **WHEN** un paciente habilitado confirma un horario aún válido
- **THEN** la interfaz envía la selección a la API y muestra el resultado real con estado, fecha y hora.

#### Scenario: Cuenta no habilitada
- **WHEN** la API rechaza por correo no verificado o falta de ficha
- **THEN** la interfaz informa cómo verificar el correo o contactar al consultorio según corresponda, sin informar éxito.

### Requirement: Consulta y acciones sobre turnos propios
La interfaz SHALL mostrar turnos propios pasados y futuros con fecha, estado, prestación y profesional. SHALL usar las acciones autorizadas por la API y ofrecer confirmar, cancelar o reprogramar solo cuando corresponda; fuera del plazo SHALL mostrar el teléfono público si está disponible.

#### Scenario: Acciones disponibles y vencidas
- **WHEN** la respuesta habilita cancelar y reprogramar para un turno y las omite para otro fuera de plazo
- **THEN** solo el primero muestra esas acciones y el segundo ofrece contactar al consultorio.

#### Scenario: Confirmar o cancelar
- **WHEN** el paciente ejecuta una acción disponible y la API la acepta
- **THEN** se actualiza la vista con el estado devuelto; si se rechaza, se informa y se consulta el estado vigente.

#### Scenario: Turno liberado
- **WHEN** el paciente consulta un turno liberado o la API rechaza su confirmación por ese estado
- **THEN** se informa que no puede confirmarse y se ofrece iniciar una nueva reserva.

### Requirement: Conflictos de horario y reprogramación
La interfaz SHALL comunicar conflictos de ocupación y mostrar las alternativas recibidas sin prometer que siguen libres. Una reprogramación rechazada MUST NOT presentarse como exitosa y SHALL conservar visible el turno original.

#### Scenario: Conflicto con alternativas
- **WHEN** una reserva o reprogramación recibe 409 de ocupación con alternativas
- **THEN** se muestra el conflicto y las alternativas, que requieren una nueva elección y envío explícitos.

#### Scenario: Sin alternativas o conflicto de límite
- **WHEN** la API devuelve alternativas vacías o un 409 por máximo de turnos
- **THEN** se informa la causa disponible sin inventar horarios ni afirmar que la operación se completó.

### Requirement: Espera, seguridad y accesibilidad
La interfaz SHALL informar la espera de lecturas lentas y su fallo final, permitir reintento acotado de lectura y MUST NOT repetir automáticamente escrituras de resultado incierto. Los controles y mensajes SHALL ser utilizables con teclado y adaptarse a pantallas pequeñas.

#### Scenario: Servicio lento
- **WHEN** una lectura pública demora y luego responde
- **THEN** se presenta la espera y después los datos sin perder la selección válida.

#### Scenario: Escritura sin respuesta
- **WHEN** una reserva o cambio queda sin respuesta
- **THEN** se informa el resultado incierto y se invita a verificar sus turnos antes de intentar nuevamente, sin repetir la escritura.
