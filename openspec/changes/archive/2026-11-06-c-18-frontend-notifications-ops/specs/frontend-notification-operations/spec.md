# Operación visual de notificaciones

## Purpose

Permitir al personal autorizado gestionar mensajes preparados, turnos sin confirmar y salud operativa desde una interfaz accesible.

## ADDED Requirements

### Requirement: Acceso y protección de pantallas operativas
La interfaz SHALL mostrar los accesos operativos únicamente a Recepción y Administrador y preservar la autorización del servidor. El panel de salud SHALL estar disponible al Administrador.

#### Scenario: Rol no autorizado
- **WHEN** un Profesional o Paciente intenta abrir las pantallas operativas
- **THEN** no se muestran datos ni acciones y se informa acceso no permitido

#### Scenario: Sesión vencida
- **WHEN** una solicitud devuelve 401
- **THEN** se aplica el flujo de sesión existente sin revelar datos anteriores a otra cuenta

### Requirement: Bandejas de notificaciones con estados explícitos
La interfaz SHALL presentar listas paginadas de WhatsApp preparado y correo fallido usando la proyección mínima del servidor, distinguiendo carga, vacío y error recuperable.

#### Scenario: Páginas y privacidad
- **WHEN** Recepción consulta una página de mensajes preparados o correos fallidos
- **THEN** ve solo las filas del canal y estado elegidos con información operativa disponible, sin inventar nombres, destinatarios o contenido

#### Scenario: Sin resultados o error
- **WHEN** una lista está vacía o falla su lectura
- **THEN** se comunica el estado y en caso de error se ofrece reintentar la lectura

### Requirement: Envío manual explícito de WhatsApp
La interfaz SHALL obtener el enlace del servidor y abrirlo en otra pestaña mediante una acción de usuario; marcar enviada SHALL ser una acción separada y explícita que no afirme entrega.

#### Scenario: Preparar y marcar
- **WHEN** Recepción abre el enlace recibido y posteriormente marca enviada
- **THEN** se abre el destino autorizado y, tras éxito de la marca, la lista se actualiza sin asegurar entrega

#### Scenario: Conflicto o resultado incierto
- **WHEN** la marca recibe 409 o falla sin confirmación del servidor
- **THEN** se muestra el resultado y se vuelve a consultar el estado antes de una nueva acción, sin repetir automáticamente la escritura

### Requirement: Turnos sin confirmar y acciones autorizadas
La interfaz SHALL listar los turnos devueltos por el filtro sin confirmar y ofrecer únicamente las acciones indicadas por el servidor, con acceso al detalle existente.

#### Scenario: Resolver turno
- **WHEN** un turno habilita confirmar, cancelar o liberar
- **THEN** se ofrece la acción autorizada y tras su éxito se actualiza la lista

#### Scenario: Acción vencida
- **WHEN** el servidor rechaza una acción por conflicto o permiso
- **THEN** se informa el problema y se actualiza el estado sin declarar éxito

### Requirement: Señales de operación para recepción
La navegación de Recepción SHALL mostrar accesos y contadores basados en datos disponibles, diferenciando cero, carga y error sin presentar conteos parciales como totales.

#### Scenario: Error de lectura
- **WHEN** no se puede obtener un contador
- **THEN** la interfaz indica que no está disponible en lugar de mostrar cero

### Requirement: Salud del barrido y cuota
El Administrador SHALL ver último barrido, antigüedad de la programada más antigua, cantidad y antigüedad de enviando, fallidas y uso de cuota con alerta indicada por el servidor.

#### Scenario: Umbral de correo
- **WHEN** los indicadores señalan alerta al 80 por ciento configurado
- **THEN** se muestra una advertencia visible; antes del umbral no se muestra esa advertencia

#### Scenario: Sin barrido o barrido antiguo
- **WHEN** no hay barrido previo o el último es antiguo
- **THEN** se distingue ausencia de ejecución y se advierte la antigüedad, sin inventar datos

#### Scenario: Enviando antigua
- **WHEN** existen filas enviando y antigüedad disponible
- **THEN** se muestran su cantidad y antigüedad; un valor nulo se representa como no disponible

### Requirement: Interfaz adaptable y accesible
Las pantallas SHALL admitir teléfono y escritorio, navegación por teclado, foco visible y nombres accesibles para acciones y estados.

#### Scenario: Uso en teléfono
- **WHEN** se consulta una bandeja en pantalla estrecha
- **THEN** textos y botones permanecen legibles sin solaparse ni requerir desplazamiento horizontal de página
