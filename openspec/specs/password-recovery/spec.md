# password-recovery Specification

## Purpose

Recuperar el acceso mediante enlaces privados de un solo uso sin revelar qué cuentas existen y revocando las sesiones renovables al cambiar la contraseña.

## Requirements

### Requirement: Recuperación sin enumeración
POST /api/v1/auth/recuperar-password SHALL responder igual para correos existentes e inexistentes, normalizados y dentro del consultorio configurado. Solo SHALL programar recuperación para cuentas activas con correo verificado y aplicar límites durables configurables (RN-05, RN-59).

#### Scenario: Cuenta elegible
- **WHEN** se solicita recuperación de una cuenta activa con correo verificado
- **THEN** programa un correo con enlace privado de recuperación y devuelve la respuesta genérica

#### Scenario: Cuenta inexistente o no verificada
- **WHEN** el correo no existe, la cuenta está inactiva o no está verificada
- **THEN** devuelve la misma respuesta sin enviar recuperación

#### Scenario: Abuso de recuperación
- **WHEN** se supera el umbral configurado de solicitudes en la ventana
- **THEN** bloquea nuevos envíos sin exponer la existencia de la cuenta

### Requirement: Restablecimiento de un solo uso
POST /api/v1/auth/restablecer-password SHALL validar el propósito, vigencia y uso del token hasheado y tomar el consultorio de su fila. SHALL guardar la nueva contraseña con Argon2, consumir el token y revocar todas las sesiones renovables en la misma transacción (RN-03, RN-04, RN-05, RN-59).

#### Scenario: Restablecimiento correcto
- **WHEN** se presenta un token válido y una contraseña de al menos ocho caracteres
- **THEN** actualiza el hash, consume el token y revoca los refresh tokens de esa cuenta sin afectar otras cuentas

#### Scenario: Token rechazado
- **WHEN** se presenta un token usado, vencido, inexistente o de otro propósito
- **THEN** rechaza sin modificar contraseña ni sesiones

#### Scenario: Solicitudes simultáneas
- **WHEN** dos solicitudes intentan consumir el mismo token
- **THEN** solo una puede restablecer la contraseña

#### Scenario: Datos no declarados
- **WHEN** el cuerpo incluye consultorio_id o la nueva contraseña tiene menos de ocho caracteres
- **THEN** responde 422 sin cambiar cuenta ni sesiones

#### Scenario: Acceso emitido previamente
- **WHEN** se revocan las sesiones tras restablecer
- **THEN** los refresh tokens dejan de funcionar y un access token emitido conserva su vencimiento previo de hasta quince minutos
