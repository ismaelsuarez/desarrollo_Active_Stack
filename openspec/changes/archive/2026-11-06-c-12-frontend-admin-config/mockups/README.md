# Mockups C-12

Approval: approved (2026-11-06, by user). Se aprobaron las acciones corregidas de creación y conflicto.

Abrir `index.html` en un navegador. El índice permite navegar por personal, alta, profesionales y boxes, horarios, bloqueos y conflicto, prestaciones, parámetros y estados de carga, vacío, error, resultado incierto y acceso denegado. Los datos son ficticios y los controles son ilustrativos; no guardan cambios.

En Bloqueos se muestra una lista ficticia y el acceso a Nuevo bloqueo. «Crear bloqueo (ejemplo)» muestra un estado de conflicto separado; allí «Volver a intentar» ilustra la acción posterior a resolver los turnos afectados. «Ver turno en agenda» conduce a un detalle simulado. Los controles no guardan ni consultan datos reales.

El usuario informó que la navegación por teclado funciona bien por el momento; no especificó todas las pantallas o estados probados. La revisión integral de teclado y la inspección visual de la implementación siguen pendientes.

Fuentes: `design-system/` revisión 2 aprobada, `CHANGES.md` C-12, KB 06 US-006 y US-008 a US-012 y spec del cambio. Inspeccionar a 390×844 y 1440×900, incluidos navegación, formularios y conflicto de turnos. Capturas, si disponibles: `previews/`.

Preview: manual (2026-11-06). Playwright MCP no pudo abrir el navegador porque el Chrome configurado no está instalado. No se generaron capturas ni se inspeccionó el render automáticamente. Abrí `index.html`, revisá cada sección y usá las herramientas del navegador para alternar entre 390×844 y 1440×900.

La revisión móvil de bloqueos ajusta cabeceras, paneles, filas, formularios y botones tras el reporte de textos superpuestos. Se volvió a intentar Playwright y el navegador configurado sigue ausente; el usuario revisó el resultado e indicó «perfecto». No se generaron capturas automatizadas.
