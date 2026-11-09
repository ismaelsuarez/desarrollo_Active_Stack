# Verificación visual del panel de equipo

Revisión del sistema visual: 2. Se inspeccionaron Inicio, Mi cuenta, Agenda, Pacientes, Solicitudes, Notificaciones, Estado operativo, Configuración y Ausentismo a 390 × 844 y 1440 × 900, además del menú móvil abierto. Las capturas se generaron con respuestas ficticias y se guardan en este directorio. La agenda incluye un turno de ejemplo; las otras bandejas usan estados vacíos o datos de ejemplo.

Las pruebas automáticas recorrieron las nueve rutas como administrador, comprobaron ausencia de desbordamiento horizontal y errores inesperados de página, consola y red, y verificaron navegación móvil y Volver desde Agenda. Otras pruebas cubren roles y foco con teclado. No se verificaron visualmente los formularios de edición, todos los estados de carga/error, ni todos los roles; no se probó con lector de pantalla ni se realizó un recorrido manual exhaustivo de teclado.

## Diferencias frente al mockup aprobado

- **Mayor — Estado operativo, ambos tamaños:** el mockup separa el aviso y tres métricas en tarjetas independientes; la implementación conserva un panel con cuatro indicadores, incluido el detalle de cuota. Reproducción: abrir Estado operativo con datos cargados.
- **Mayor — Notificaciones, ambos tamaños:** el mockup integra pestañas dentro del panel de bandeja; la implementación las mantiene encima del panel e incluye el enlace Sin confirmar. Reproducción: abrir Notificaciones.
- **Menor — Agenda, ambos tamaños:** el mockup presenta hora, paciente y estado como elementos separados con distintivo; la aplicación conserva el texto completo del turno en una línea y la acción Ver turno. Reproducción: seleccionar un profesional con turnos.
- **Menor — Solicitudes, ambos tamaños:** los filtros y búsqueda comparten panel, pero se distribuyen en dos filas y conservan los controles de paginación de fichas que el mockup simplifica. Reproducción: abrir Solicitudes.
- **Menor — Navegación y cabecera, ambos tamaños:** la cabecera muestra indicadores de recepción en lugar del indicador de sesión del mockup y no incluye el pie ilustrativo; el contorno en el título refleja el foco accesible existente. Reproducción: abrir cualquier pantalla.
- **Menor — Pacientes y Ausentismo, ambos tamaños:** los estados vacíos usan texto sin el icono decorativo de la maqueta; los resultados y formularios conservan las acciones existentes. Reproducción: consultar sin resultados.
- **Menor — Configuración, ambos tamaños:** la aplicación muestra todas las secciones y campos reales, mientras que la maqueta presenta solo una selección representativa. Reproducción: abrir Configuración y desplazarse.
