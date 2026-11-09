# Spec Delta

## ADDED Requirements

### Requirement: Resultado incierto del restablecimiento
La interfaz SHALL distinguir un rechazo confirmado del enlace de una falla de red o servidor que deja incierto el resultado.

#### Scenario: Conexión interrumpida
- **WHEN** el restablecimiento no recibe una respuesta concluyente
- **THEN** informa la incertidumbre y recomienda probar la contraseña nueva o solicitar otro enlace, sin afirmar que venció.

