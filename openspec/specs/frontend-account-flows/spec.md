# frontend-account-flows Specification

## Purpose

Permitir que usuarios y pacientes completen sus flujos de cuenta y enlaces privados desde la interfaz.

## Requirements
### Requirement: Registro con aviso de privacidad vigente
La pantalla de registro SHALL mostrar texto y versión obtenidos de la API y requerir aceptación inicialmente desmarcada antes de habilitar el envío. SHALL enviar la versión mostrada junto con los datos requeridos por el contrato de registro.

#### Scenario: Aviso cargado y aceptado
- **WHEN** el paciente completa los datos y acepta el aviso recibido
- **THEN** puede registrar la cuenta y se envían aceptación verdadera y la versión mostrada.

#### Scenario: Aviso no disponible o no aceptado
- **WHEN** no se obtuvo el aviso o su casilla permanece desmarcada
- **THEN** el envío permanece deshabilitado y se informa el problema si corresponde.

#### Scenario: Versión desactualizada
- **WHEN** el servidor rechaza la versión mostrada por haber cambiado
- **THEN** se informa y se vuelve a obtener el aviso para una nueva aceptación explícita.

### Requirement: Acceso y recuperación
La interfaz SHALL permitir ingresar, solicitar reenvío de verificación o recuperación y restablecer la contraseña usando los endpoints existentes; SHALL mostrar respuestas genéricas de recuperación y reenvío sin inferir si una cuenta existe.

#### Scenario: Credenciales incorrectas o correo sin verificar
- **WHEN** el ingreso recibe 401 o la respuesta 403 de correo sin verificar
- **THEN** presenta el error correspondiente y ofrece reenvío cuando corresponda.

#### Scenario: Recuperación solicitada
- **WHEN** el usuario solicita recuperación o reenvío
- **THEN** ve el mensaje genérico de la API sin revelar si existe la cuenta.

#### Scenario: Restablecimiento
- **WHEN** el usuario presenta un enlace válido y una contraseña nueva válida
- **THEN** la interfaz envía el token y la contraseña en el cuerpo y muestra el resultado.

### Requirement: Enlaces privados de correo
La SPA SHALL resolver `/verificar-email`, `/restablecer-password` y `/confirmar-turno` emitidas por la API, y los alias documentados `/restablecer` y `/confirmar`. Los tokens SHALL leerse del fragmento y enviarse en el cuerpo al endpoint correspondiente, sin mostrarse ni incluirse en la consulta o registros.

#### Scenario: Verificación o confirmación válida
- **WHEN** se abre un enlace con token válido
- **THEN** se procesa el token mediante POST y se muestra el resultado de la API.

#### Scenario: Token ausente, usado o vencido
- **WHEN** falta el token o la API lo rechaza
- **THEN** se muestra un error recuperable sin exponerlo ni repetir automáticamente la operación.

### Requirement: Gestión de cuenta propia
La interfaz SHALL permitir a cualquier cuenta autenticada cambiar su contraseña y al paciente actualizar correo y/o teléfono, respetando los campos y permisos de la API.

#### Scenario: Actualización de contacto
- **WHEN** un paciente envía un cambio válido de contacto
- **THEN** se informa el resultado y la necesidad de verificar nuevamente un correo diferente.

#### Scenario: Contraseña actual incorrecta
- **WHEN** el usuario intenta cambiar su contraseña con la actual incorrecta
- **THEN** se muestra el error y el formulario no informa éxito.
