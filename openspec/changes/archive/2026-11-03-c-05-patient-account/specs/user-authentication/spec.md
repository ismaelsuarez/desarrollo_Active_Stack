## ADDED Requirements

### Requirement: Activación de cuenta y recuperación integradas
La autenticación SHALL permitir ingresar después de verificar el correo y SHALL exigir reverificación tras cambiarlo. El restablecimiento SHALL invalidar todos los refresh tokens de la cuenta preservando el aislamiento y los claims existentes sin ficha de paciente (RN-02, RN-05, RN-06).

#### Scenario: Activación
- **WHEN** un paciente verifica correctamente su correo y presenta credenciales válidas
- **THEN** puede ingresar con los mismos contratos JWT y cookies de C-03

#### Scenario: Correo cambiado
- **WHEN** el paciente cambia su correo y todavía no verifica el nuevo
- **THEN** un nuevo ingreso se rechaza hasta completar la verificación

#### Scenario: Recuperación de acceso
- **WHEN** se restablece la contraseña mediante token válido
- **THEN** los refresh tokens anteriores se rechazan y las credenciales nuevas permiten ingresar si el correo está verificado
