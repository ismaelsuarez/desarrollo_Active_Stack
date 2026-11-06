# C-13 · Mockups para revisión

Approval: approved (2026-11-06, by user)

Diseño de referencia con datos inventados para Recepción, Administrador y Profesional. Sistema visual aprobado revisión 2; nombre y logo siguen provisionales. Estos archivos no envían datos ni son la aplicación terminada.

## Pantallas y estados

Abrir [index.html](index.html) y usar los enlaces. También se pueden abrir directamente las secciones por fragmento:

- `#agenda`, `#detalle`: agenda diaria y detalle con acciones.
- `#nuevo`, `#ficha-nueva`, `#conflicto`, `#mover`, `#cancelar`: alta de ficha y turno, conflicto, movimiento y cancelación.
- `#autorizar`, `#sobreturno`, `#responder`: autorización, aviso y respuesta sin veto.
- `#pacientes`, `#ficha`, `#desvincular`, `#reactivar`: búsqueda, cuenta vinculada, desvinculación y reactivación.
- `#solicitudes`, `#resolver`: lista de todos los estados y resolución.
- `#profesional`, `#profesional-turno`, `#ficha-profesional`: vista de agenda propia y ficha sin bloque de cuenta.

Los textos de carga, vacío, errores, conflicto e incertidumbre son criterios de diseño; botones de ejemplo no operan sobre datos reales. La disponibilidad mostrada ante conflicto es orientativa, consultada aparte del 409; al crear una ficha y fallar el turno, la ficha queda creada. El usuario revisa especialmente claridad de acciones, contenido y privacidad.

Fuentes: `CHANGES.md` C-13, KB funcionalidades y flujos, deltas y diseño del cambio, `design-system/README.md`, `tokens.css` y `brand.js` revisión 2. Los datos de demostración son ficticios.

## Revisión

Abrir `index.html` local con doble clic en un navegador y revisar cada sección en escritorio y celular (o reducir el ancho de la ventana). Playwright no inició porque no encuentra Chrome configurado y Computer Use informó que el host de navegador no está disponible. No se generaron capturas ni se inspeccionó visualmente el render; esta revisión es manual. La aprobación explícita de esta revisión es necesaria antes de implementar; cualquier revisión posterior vuelve a estado pendiente.
