# Tareas

## 1. Aprobación visual

- [x] 1.1 Presentar y obtener aprobación explícita del [mockup](mockups/index.html) con sistema revisión 2; registrar aprobación y capturas o revisión manual en diseño y README.

## 2. Contexto y políticas operativas

- [x] 2.1 Implementar contexto de agenda propia con TDD y PostgreSQL real; verificar profesional, administrador con/sin agenda, rol denegado y aislamiento de consultorio.
- [x] 2.2 Ampliar lecturas operativas con acciones calculadas por políticas y reloj; verificar roles, estados, reloj, concurrencia, compatibilidad paciente y aislamiento en pruebas de integración.

## 3. Agenda y gestión de turnos

- [x] 3.1 Implementar navegación por rol, agenda diaria y selección de profesional/fecha con pruebas de rutas, permisos, zona, vacío y respuesta obsoleta.
- [x] 3.2 Implementar alta, movimiento y alternativas orientativas con pruebas de 409, 422, carga, error y envío incierto sin repetición; incluir creación de ficha y recuperación de resultado parcial.
- [x] 3.3 Implementar acciones del ciclo y sus formularios con pruebas por rol, estado y recarga tras éxito o conflicto.
- [x] 3.4 Implementar autorización explícita y respuesta de sobreturno con pruebas de motivo, permisos, aviso y rechazo sin cancelación.

## 4. Fichas y vinculación

- [x] 4.1 Implementar búsqueda paginada, detalle, edición e historial con pruebas de permisos y privacidad de cuenta para Profesional.
- [x] 4.2 Implementar solicitudes pendientes/resueltas, vinculación y rechazo con pruebas de ficha elegida, cuenta no verificada, conflicto y actualización.
- [x] 4.3 Implementar desvinculación y reactivación con pruebas de motivo obligatorio, ocultación por rol y 409 recuperable.

## 5. Verificación integral

- [x] 5.1 Ejecutar pruebas relevantes backend con PostgreSQL, frontend, typecheck y build; registrar resultados, migraciones y limitaciones en evidencia.
- [x] 5.2 Comparar cada pantalla y estado implementado con los [mockups aprobados](mockups/index.html) en 390×844 y 1440×900; revisar consola/red y accesibilidad de teclado o registrar [lista manual y límites](mockups/verify/README.md) sin afirmar verificación no realizada.

## Workflow follow-up

- Sincronizar especificaciones y archivar una vez satisfechas las verificaciones.
