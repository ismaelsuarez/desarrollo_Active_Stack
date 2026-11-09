# Verificación visual de la landing

Sistema visual revisión 2. Se inspeccionaron capturas de portada con prestaciones, carga, fallo y catálogo vacío en 390 × 844 y 1440 × 900. Las imágenes de este directorio provienen de la aplicación con respuestas ficticias, no de la maqueta. Se verificó que no hay desbordamiento horizontal, que las acciones de reserva e ingreso navegan a sus rutas, que se puede avanzar con Tab y que no hubo errores inesperados de página, consola, respuestas HTTP o solicitudes de red en el escenario automatizado.

## Diferencias respecto de la maqueta

- Menor, ambos tamaños: el título tiene un contorno de foco al entrar por el manejo de foco existente; la maqueta estática no reproduce ese estado. Reproducción: abrir `/`.
- Menor, ambos tamaños: se omiten la franja de identificación de maqueta, la leyenda de ejemplos y el contacto cuando la API no devuelve datos. Los nombres y prestaciones visibles provienen de las respuestas de prueba.
- Menor, estados, ambos tamaños: carga, error y vacío se muestran dentro de la sección de prestaciones; la maqueta los presenta en láminas separadas para revisión. Ante fallo parcial se conservan los datos que sí respondieron.

Se revisaron los cuatro estados anteriores en ambos tamaños. No se probó con lector de pantalla ni se hizo un recorrido manual exhaustivo de teclado; la prueba automatizada cubre foco inicial, Tab y las acciones principales.
