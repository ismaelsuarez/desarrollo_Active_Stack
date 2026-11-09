# Verificación visual

Revisión 2 del sistema; se comprobaron primera página, página siguiente y error con reintento a 390 × 844 y 1440 × 900, usando datos ficticios y capturas en este directorio. Se inspeccionaron las seis capturas. No hubo errores de ejecución de página ni solicitudes fallidas inesperadas en la prueba de navegador; el 503 es intencional para el estado de error.

- Diferencia menor, error, ambos tamaños: la maqueta usa fondo rosado para el mensaje; la aplicación conserva el estilo de alertas existente, con texto rojo sin fondo. Reproducción: abrir ficha y provocar fallo al avanzar.
- Diferencia menor, navegación, ambos tamaños: el número de página tiene menos separación horizontal que en la maqueta. Reproducción: abrir cualquier ficha.
- La aplicación incluye cabecera y búsqueda existentes, omitidas de la maqueta enfocada en el historial. El formato de fechas representa los datos de ejemplo de cada captura.

No se verificó con lector de pantalla. Se verificaron únicamente los tres estados y tamaños anteriores; carga transitoria y primera carga fallida se verificaron mediante pruebas de componentes, no mediante comparación visual.
