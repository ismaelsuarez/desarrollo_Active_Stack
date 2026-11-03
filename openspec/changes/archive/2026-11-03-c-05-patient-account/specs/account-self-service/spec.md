## Purpose

Permitir que una cuenta autenticada cambie su contraseña y que el paciente mantenga sus datos de contacto, preservando la verificación de identidad y el aislamiento entre consultorios.

## ADDED Requirements

### Requirement: Cambio de contraseña autenticado
PATCH /api/v1/auth/cambiar-password SHALL exigir JWT y contraseña actual correcta, aceptar una nueva contraseña de al menos ocho caracteres y guardar solo su hash. La identidad y consultorio SHALL salir del Principal (US-005, RN-04, RN-59).

#### Scenario: Cambio autorizado
- **WHEN** una cuenta autenticada presenta su contraseña actual correcta y una nueva válida
- **THEN** cambia el hash y puede ingresar con la nueva contraseña

#### Scenario: Contraseña actual incorrecta
- **WHEN** la contraseña actual es incorrecta
- **THEN** rechaza sin cambiar el hash

#### Scenario: Solicitud no autorizada
- **WHEN** falta JWT o se intentan enviar usuario_id, consultorio_id u otros campos no declarados
- **THEN** rechaza la solicitud sin modificar otras cuentas

### Requirement: Actualización de contacto del paciente
PATCH /api/v1/auth/actualizar-cuenta SHALL permitir al paciente actualizar teléfono y/o correo propios, sin editar otros datos de ficha. Un correo diferente normalizado SHALL quedar sin verificar y generar verificación nueva; un correo equivalente SHALL conservar la verificación (US-005, RN-02, RN-63).

#### Scenario: Teléfono propio
- **WHEN** el paciente actualiza su teléfono
- **THEN** actualiza el contacto de su ficha vinculada actual dentro de su consultorio

#### Scenario: Cambio de correo
- **WHEN** el paciente cambia a un correo disponible diferente
- **THEN** actualiza la cuenta y el contacto de su ficha cuando exista, limpia la verificación anterior e invalida los enlaces de verificación previos antes de programar el nuevo

#### Scenario: Correo equivalente
- **WHEN** el correo solo difiere por espacios exteriores o mayúsculas
- **THEN** conserva su verificación y no programa un correo nuevo

#### Scenario: Conflicto o rol incorrecto
- **WHEN** el correo ya pertenece a otra cuenta del consultorio o el rol no es paciente
- **THEN** rechaza sin cambios parciales ni correo adicional

#### Scenario: Cuenta sin ficha
- **WHEN** una cuenta paciente sin ficha actualiza su correo
- **THEN** actualiza su cuenta sin vincular ni modificar una ficha ajena
