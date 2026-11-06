# Evidencia de implementación C-12

## Actualización: prueba de integración en Edge

- El usuario pidió usar Playwright. `frontend/e2e/admin-keyboard.pw.ts` ejecuta la aplicación real con respuestas de API simuladas: navega el formulario de personal con Tab y lo envía con Enter; verifica también duración numérica, rechazo de `e` y recorrido Tab/Shift+Tab. Edge: **2/2 pruebas aprobadas**.
- Las pruebas de integración de `Personal.test.tsx` cubren carga, error, relectura, vacío y escritura incierta sin reintento. Suite frontend: **208/208**, typecheck y build aprobados. La tarea 5.1 queda completa; esta prueba no constituye una comparación visual completa ni inspección de todas las pantallas.
- Ejecución en este entorno Windows: iniciar `npm run dev -- --host 127.0.0.1 --port 4177 --strictPort` en una terminal y en otra ejecutar `$env:PLAYWRIGHT_EXTERNAL_SERVER='1'; npm run test:keyboard`; detener el servidor propio al terminar. El cierre automático `webServer` se quedó esperando en el entorno restringido; por eso se usó el servidor externo. Edge debe estar instalado.

## Revisión de teclado y campos numéricos

- El usuario expresó «Aprobada la integracion de teclado» después de ser informado de que la prueba automatizada de integración no se ejecutó. Se registra su aprobación, sin atribuirle la ejecución de esa prueba ni una comparación visual automatizada.
- El usuario informó que revisó por completo el teclado y que los formularios y espacios de texto funcionan bien; señaló que los campos numéricos admitían la letra «e». No se hizo una inspección automatizada independiente de la implementación.
- Corrección de enteros: red de seguridad de `Catalog.test.tsx` 6/6; RED con `1e2` y `2e2` aceptados; GREEN 8/8 incluyendo entradas enteras, tecla, pegado y atajo con Ctrl. El mockup usa la misma restricción de teclado y pegado. Se conservan las validaciones de rango existentes.
- Se agregó una prueba de integración de Personal para carga, error de lectura, actualización explícita y lista vacía, y se comprobó que una escritura incierta no se reenvía; `Personal.test.tsx` pasa 6/6. La prueba de teclado se incorporó posteriormente, como se describe arriba.

## Revisión del listado de bloqueos

- El usuario aprobó la revisión del mockup y el ajuste móvil el 2026-11-06. La aplicación distingue bloqueos vigentes y formulario de nuevo bloqueo; filtra los finalizados según la fecha y hora del navegador y conserva la consulta por alcance.
- Red de seguridad: 4/4 pruebas previas de `Bloqueos.test.tsx`. RED: falló el caso que exigía listado de vigentes y formulario identificado. GREEN: 5/5. Triangulación: caso adicional con solo bloqueos vencidos; suite frontend final 205/205, typecheck y build aprobados. CSS adapta filas y alertas para evitar desbordamiento.
- La comparación visual y la inspección automatizada de teclado de esta sección permanecen pendientes; ver checklist manual. El filtro se recalcula al volver a renderizar o consultar la lista y depende del reloj del dispositivo.
- El usuario aprobó la separación de crear bloqueo y conflicto el 2026-11-06 e indicó posteriormente que revisó el teclado y los formularios. El componente ya muestra «Crear bloqueo» antes del conflicto y «Volver a intentar» tras un 409; sus seis pruebas dirigidas pasaron.

El mockup de la revisión 2 fue aprobado por el usuario el 2026-11-06. La comparación visual de la implementación sigue pendiente; ver `mockups/verify/README.md`.

| Tarea | Archivo de pruebas / capa | Red de seguridad | RED | GREEN y triangulación |
|---|---|---|---|---|
| 1.1 | Revisión de diseño | No aplica | No aplica | Aprobación registrada en diseño y README. |
| 1.2 | `frontend/src/shell/routes.test.tsx`, integración | 13/13 rutas/layout/guard | Ruta inexistente y enlace faltante fallaron. | 15/15; administrador, otros cuatro roles, visitante y enlace de inicio. |
| 2.1 | `frontend/src/admin/Personal.test.tsx`, integración | Componente nuevo | Importación inexistente y campo 422 fallaron. | 5/5; alta, edición, desactivación, 409, 422 y fallo de red. Usuario eligió usuario y correo; comprobado nuevamente 5/5. |
| 2.2 | `frontend/src/admin/Profesionales.test.tsx`, integración | Componente nuevo | Importación inexistente. | 4/4; alta, conflicto, cuenta incompatible, box y desactivación. |
| 3.1 | `frontend/src/admin/Horarios.test.tsx`, integración | Componente nuevo | Importación inexistente. | 3/3; bloques contiguos, solapamiento, orden y fallo. |
| 3.2–3.3 | `frontend/src/admin/Bloqueos.test.tsx`, `frontend/src/api/client.test.ts`, `frontend/src/staff/AgendaPage.test.tsx`, integración | Cliente 17/17 y agenda 9/9 | Importación inexistente, 409 sin IDs y detalle sin enlace fallaron. | Bloqueos 4/4, cliente 20/20 y agenda 11/11; reintentos, validación, borrado y enlace por ID. |
| 4.1–4.2 | `frontend/src/admin/Catalog.test.tsx`, integración | Componentes nuevos | Importación inexistente; campos 422 descartados fallaron en cliente. | Catálogo 6/6 y cliente 20/20; alta, edición, desactivación, duplicado, límites, orden y errores. |
| Navegación visual | `frontend/src/admin/AdminPage.test.tsx`, integración | Componente nuevo | Faltaban enlaces a secciones. | 1/1 enlaces y destinos. |

Las pruebas de cliente y de componentes verifican que las escrituras con resultado incierto no se repitan automáticamente. No hubo una etapa de refactorización separada; se realizaron cambios pequeños y se ejecutaron las pruebas dirigidas después de cada paso.

Última ejecución completa: 208/208 pruebas frontend, typecheck y build aprobados, además de 2/2 pruebas Playwright con Edge.
