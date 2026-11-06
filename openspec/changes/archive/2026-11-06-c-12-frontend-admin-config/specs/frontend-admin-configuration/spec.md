# Configuración administrativa

## Purpose

Permitir al administrador configurar de forma comprensible el personal y la agenda del consultorio desde la aplicación.

## ADDED Requirements

### Requirement: Acceso a configuración solo de administrador
La aplicación SHALL ofrecer navegación a configuración únicamente al administrador autenticado y proteger todas sus rutas, dejando la autorización efectiva a la API.

#### Scenario: Administrador accede
- **WHEN** un administrador ingresa a configuración
- **THEN** puede navegar entre personal, profesionales, horarios, bloqueos, prestaciones y parámetros.

#### Scenario: Otro rol intenta acceso directo
- **WHEN** una persona sin rol administrador intenta acceder a una ruta de configuración
- **THEN** no ve sus datos ni controles y recibe acceso denegado o redirección apropiada.

### Requirement: Gestión de personal
El administrador SHALL poder consultar, crear, editar y desactivar cuentas del personal con usuario, correo y un único rol permitido, mostrando estado y errores de validación. El alta incluye la contraseña inicial y no solicita nombre ni apellido de la persona.

#### Scenario: Alta válida
- **WHEN** completa una cuenta con rol de personal válido y la API acepta el alta
- **THEN** la lista refleja la cuenta creada.

#### Scenario: Rechazo o desactivación
- **WHEN** la API rechaza un dato o se desactiva una cuenta
- **THEN** se muestra el error pertinente o el estado inactivo respectivamente, sin afirmar que se borró su historial.

### Requirement: Profesionales y boxes
El administrador SHALL poder listar y crear boxes, crear y editar profesionales, asignarles un box y activar o desactivar profesionales mediante las operaciones disponibles.

#### Scenario: Cuenta y box compatibles
- **WHEN** se asocia un profesional a una cuenta compatible y un box disponible y la API lo acepta
- **THEN** se muestra la asignación actualizada.

#### Scenario: Asociación rechazada
- **WHEN** la API rechaza por box ocupado o cuenta incompatible
- **THEN** se explica el conflicto y se conservan los datos editados.

### Requirement: Editor de horario semanal
El administrador SHALL consultar y reemplazar los bloques semanales de un profesional, validando día y orden de horas y evitando enviar bloques solapados del mismo día.

#### Scenario: Bloques compatibles
- **WHEN** se guardan bloques válidos no superpuestos, incluidos bloques contiguos
- **THEN** se envía el horario completo y se muestra el resultado confirmado por la API.

#### Scenario: Bloques superpuestos
- **WHEN** dos bloques de un mismo día se superponen
- **THEN** se identifica el error y no se envía el horario.

### Requirement: Bloqueos y turnos afectados
El administrador SHALL listar, crear y eliminar bloqueos globales o de un profesional; ante turnos afectados SHALL mostrarlos y exigir su resolución explícita antes de reintentar, sin modificar ni cancelar turnos automáticamente.

#### Scenario: Intervalo libre
- **WHEN** se crea un bloqueo válido sin turnos afectados
- **THEN** se confirma su creación y se actualiza la lista.

#### Scenario: Intervalo ocupado
- **WHEN** la API responde con turnos afectados
- **THEN** se informa que el bloqueo no fue creado, se listan los turnos devueltos y se facilita resolverlos explícitamente antes de volver a intentar.

#### Scenario: Conflicto persistente
- **WHEN** se reintenta y la API vuelve a informar turnos afectados
- **THEN** el bloqueo sigue sin confirmarse y se muestra la lista actualizada.

### Requirement: Prestaciones y parámetros
El administrador SHALL listar, crear, editar y desactivar prestaciones, y consultar y actualizar modo de liberación, plazos, teléfono y límites de reserva establecidos por la API.

#### Scenario: Guardar configuración válida
- **WHEN** la API acepta cambios en una prestación o parámetros
- **THEN** la pantalla muestra los valores confirmados y su estado.

#### Scenario: Campo rechazado
- **WHEN** la API rechaza una duración, un plazo o límite inválido
- **THEN** la pantalla presenta el error junto al campo cuando sea identificable y conserva la entrada.

### Requirement: Estados y errores de operaciones
Las pantallas SHALL presentar estados de carga, lista vacía, fallo y confirmación accesibles; las escrituras de resultado incierto no SHALL repetirse automáticamente.

#### Scenario: Lectura fallida
- **WHEN** una lectura de configuración falla
- **THEN** se muestra un error comprensible y una opción para volver a intentar.

#### Scenario: Escritura sin respuesta
- **WHEN** una escritura queda sin respuesta
- **THEN** se comunica que su resultado es incierto y se permite comprobar el estado antes de volver a intentar.
