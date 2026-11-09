# Spec Delta

## ADDED Requirements

### Requirement: Espera y recuperación de reserva
La interfaz SHALL indicar inmediatamente una búsqueda activa y evitar envíos duplicados. SHALL permitir reintentar la carga inicial fallida respetando los límites indicados por el servidor.

#### Scenario: Búsqueda en curso
- **WHEN** el paciente busca horarios y la respuesta está pendiente
- **THEN** ve un estado de búsqueda y no puede iniciar otra con el mismo formulario.

#### Scenario: Catálogo falla
- **WHEN** falla la carga inicial y no hay espera obligatoria por límite
- **THEN** puede solicitar nuevamente los datos.

### Requirement: Turnos propios ante fallo parcial
La interfaz SHALL conservar visibles los turnos recibidos aunque falle la carga de información pública complementaria y SHALL ofrecer recuperar esos datos.

#### Scenario: Fallan profesionales
- **WHEN** la consulta de turnos tiene éxito y falla el catálogo de profesionales
- **THEN** muestra los turnos y un aviso con reintento para los datos complementarios.

