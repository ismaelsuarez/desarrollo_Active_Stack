# Spec Delta

## ADDED Requirements

### Requirement: Navegación coherente para el equipo
El personal SHALL disponer de navegación identificable y adaptable entre sus secciones autorizadas, incluido el acceso a Mi cuenta, sin mostrar como disponibles funciones que su rol no permite.

#### Scenario: Navegación entre pantallas autorizadas
- **WHEN** un integrante del equipo abre Inicio, Mi cuenta o una pantalla operativa autorizada
- **THEN** identifica la sección actual y puede acceder a las demás secciones permitidas para su rol.

#### Scenario: Navegación en móvil
- **WHEN** una persona usa la interfaz en una pantalla pequeña
- **THEN** puede acceder a las secciones autorizadas con teclado o controles táctiles sin desbordamiento horizontal.

### Requirement: Regreso desde Mi cuenta
La pantalla Mi cuenta SHALL ofrecer una acción Volver que lleve al contexto interno anterior si existe y, en caso contrario, al inicio del rol autenticado.

#### Scenario: Ingreso directo a Mi cuenta
- **WHEN** una persona autenticada abre Mi cuenta directamente sin una pantalla interna anterior identificable
- **THEN** Volver conduce al inicio correspondiente a su rol.

#### Scenario: Mi cuenta desde una pantalla interna
- **WHEN** una persona abre Mi cuenta desde una pantalla interna autorizada y elige Volver
- **THEN** regresa a esa pantalla interna.
