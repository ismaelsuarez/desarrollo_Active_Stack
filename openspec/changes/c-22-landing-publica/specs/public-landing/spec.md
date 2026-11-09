# Spec Delta

## Purpose

Presentar el consultorio y sus flujos de turnos a pacientes y personas que conocen el proyecto, facilitando el acceso a la reserva y a la cuenta.

## ADDED Requirements

### Requirement: Portada con acciones disponibles
La portada pública SHALL explicar la reserva y ofrecer enlaces claros para reservar, ingresar y crear una cuenta, incluso mientras se cargan datos o ante errores.

#### Scenario: Visitante abre la portada
- **WHEN** una persona sin sesión entra en `/`
- **THEN** puede acceder a la reserva, al ingreso y al registro y comprender que puede explorar turnos antes de ingresar.

#### Scenario: Fallo de datos públicos
- **WHEN** falla la carga del consultorio o las prestaciones
- **THEN** la portada comunica el estado y ofrece recuperación sin ocultar las acciones principales ni inventar información.

### Requirement: Datos públicos y contenido fiel
La portada SHALL mostrar solo datos públicos disponibles del consultorio y prestaciones activas y describir únicamente funciones existentes.

#### Scenario: Datos opcionales ausentes
- **WHEN** no hay teléfono, dirección o prestaciones
- **THEN** no muestra valores vacíos como datos reales y presenta un estado neutro donde corresponda.

### Requirement: Portada accesible y adaptable
La portada SHALL poder utilizarse con teclado y adaptarse a escritorio y celular con títulos y enlaces identificables.

#### Scenario: Navegación móvil o por teclado
- **WHEN** una persona utiliza la portada con teclado o un viewport móvil
- **THEN** puede identificar y alcanzar las acciones y leer el contenido sin desbordamiento horizontal.
