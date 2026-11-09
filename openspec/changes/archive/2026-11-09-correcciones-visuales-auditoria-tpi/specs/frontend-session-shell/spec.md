# Spec Delta

## ADDED Requirements

### Requirement: Orientación al navegar
La interfaz SHALL trasladar el foco al encabezado principal cuando cambia de pantalla sin interrumpir el foco en renderizaciones ordinarias.

#### Scenario: Navegación por teclado
- **WHEN** el usuario abre otra pantalla
- **THEN** el encabezado de destino recibe el foco.

### Requirement: Bienvenida coherente con el rol
La pantalla inicial SHALL describir el acceso a funciones disponibles para cada rol sin afirmar que no existen.

#### Scenario: Rol con funciones
- **WHEN** ingresa un paciente, recepcionista, profesional o administrador
- **THEN** ve orientación coherente con las opciones disponibles.

