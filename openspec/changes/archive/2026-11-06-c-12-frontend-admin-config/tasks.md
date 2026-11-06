# Tareas: configuración administrativa

## 1. Diseño y acceso

- [x] 1.1 Presentar y obtener aprobación del [mockup](mockups/index.html) en revisión 2; registrar aprobación y previsualización en diseño y README antes de implementar.
- [x] 1.2 Agregar navegación y rutas protegidas; probar acceso directo de administrador, de todos los demás roles y sin sesión.

## 2. Administración de personal y estructura

- [x] 2.1 Implementar listado, alta, edición y desactivación de personal; probar roles válidos, rechazo, errores de campo y estados.
- [x] 2.2 Implementar listado/alta de boxes y gestión de profesionales y asignaciones; probar cuenta incompatible, box ocupado y desactivación conservando historial.

## 3. Disponibilidad y excepciones

- [x] 3.1 Implementar editor semanal con bloques múltiples; probar bloques contiguos, superposición, orden inválido, conservación ante error y guardado confirmado.
- [x] 3.2 Implementar listado, creación y eliminación de bloqueos globales y por profesional; probar intervalo libre y error de validación.
- [x] 3.3 Resolver conflicto 409 con lista de turnos afectados y navegación a su gestión, sin modificar automáticamente; probar reintento con conflicto persistente y después de resolver.

## 4. Catálogo y parámetros

- [x] 4.1 Implementar listado, alta, edición y desactivación de prestaciones; probar duración inválida, duplicado y éxito.
- [x] 4.2 Implementar parámetros de consultorio y reserva; probar valores válidos, límites y orden de plazos inválidos, errores de API y preservación de entradas.

## 5. Verificación transversal

- [x] 5.1 Verificar estados de carga, vacío, error, escritura incierta sin reintento automático y accesibilidad con teclado mediante pruebas de integración.
- [x] 5.2 Ejecutar pruebas frontend, typecheck y build; registrar resultados y evidencias TDD por tarea.
- [x] 5.3 Comparar cada pantalla y estado con el mockup aprobado en 390×844 y 1440×900, revisar consola, red y teclado; registrar capturas o límites y checklist manual según disponibilidad.

## Workflow follow-up

- Sincronizar especificación y archivar solo tras completar verificaciones y revisión aplicables.
