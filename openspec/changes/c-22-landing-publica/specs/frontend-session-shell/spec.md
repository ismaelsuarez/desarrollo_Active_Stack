# Spec Delta

## ADDED Requirements

### Requirement: Entrada pública y acceso a sesión
La raíz SHALL mostrar la portada al visitante sin sesión y redirigir al panel del rol a quien ya tiene sesión; `/ingresar` SHALL conservar el formulario de acceso para visitantes.

#### Scenario: Sesión en restauración
- **WHEN** se está restaurando la sesión al abrir la raíz o ingreso
- **THEN** se informa la espera sin mostrar una portada o formulario equivocados.

#### Scenario: Sesión activa
- **WHEN** una persona con sesión visita `/` o `/ingresar`
- **THEN** se la redirige al panel correspondiente a su rol.
