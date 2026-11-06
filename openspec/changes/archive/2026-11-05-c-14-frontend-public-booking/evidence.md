# Evidencia C-14

- Línea de base (2026-11-05): 86/86 pruebas frontend y typecheck correctos antes de modificar producción.
- Mockups aprobados por el usuario; vista previa manual, sin inspección automatizada (ver `design.md`).
- Registro de skills: no se pudo refrescar porque ni `python` ni `py` están disponibles en PATH; se consultaron las skills locales ya instaladas y el índice existente.
- Tarea 2.1: red de seguridad 12/12 pruebas del cliente incluida en la suite de 86; RED: faltaba el detalle de 409; GREEN: 13/13. Triangulación: entradas inválidas, máximo, 403 de plazo y 403 genérico; RED y GREEN 17/17. Se conserva solo causa normalizada: el teléfono se obtiene del consultorio público, no del texto de error. Sin refactor posterior.
- Tarea 2.2: función nueva sin línea de base propia; RED por módulo ausente, GREEN 1/1, triangulación entre Buenos Aires y UTC y cruce de día 2/2. La consulta descarta respuestas de una selección anterior; prueba React de fecha cambiada con resolución tardía. Sin refactor posterior.
- Tareas 3.1–3.4: componentes nuevos sin baseline propio; RED por componente y ruta ausentes, GREEN; triangulación de vacío, demora inicial, 429, respuesta obsoleta, ingreso/registro, retorno sin envío automático, reserva y 403/409/red incierta, alternativas vacías y otra fecha, y bloqueo de cambios durante envío. `BookingPage.test.tsx` 15/15; rutas 7/7 y layout 1/1 en sus ejecuciones. Refactor de distribución seguido de tests verdes. Datos de selección en memoria, sin token ni persistencia.
- Tareas 4.1–4.3: RED por pantalla, ruta, confirmación, cancelación y reprogramación ausentes; GREEN incremental. Triangulación de profesional ausente, acciones no autorizadas, turno liberado, plazo 403, confirmación de cancelación, 409 con y sin alternativas, 422, fecha alternativa y envío pendiente. `AppointmentsPage.test.tsx` 11/11; enlaces de confirmación 23/23; rutas 7/7. La duración del turno se conserva en el servidor y la disponibilidad se presenta como orientativa. Refactor de acciones y bloqueo de controles seguido de tests verdes.

## Integración y entorno

- Suite final frontend: 127/127; typecheck y build correctos. `booking-integration.test.tsx` recorre selección, registro, verificación por enlace simulado, ingreso y reserva con `fetch` simulado; no se envía una reserva hasta la confirmación explícita. Las pruebas de componentes cubren errores 403/409, ausencia de alternativas, demora y resultado incierto.
- En Vite local, `/reservar` y `/mis-turnos` respondieron 200 con HTML de SPA; `/api/v1/health` llegó mediante el mismo origen al servidor HTTP simulado y devolvió `proxy-ok`. Se detuvieron ambos servidores temporales. Docker Desktop no tenía el motor disponible; no se verificó C-14 contra API ni PostgreSQL reales en esta ejecución.

## Revisión visual manual pendiente

No se abrió ni comparó ninguna pantalla de la implementación en esta ejecución. Playwright configurado busca Chrome, que no está instalado; el acceso de Computer Use a Edge no pudo determinar la URL de forma segura. No se generaron capturas, ni se verificaron consola, red o navegación de teclado en navegador. El usuario pidió explícitamente omitir esta revisión para C-14 el 2026-11-05; la tarea 5.2 registra esa excepción, no una verificación aprobada.

Con la API local y frontend activos, comparar en 390×844 y 1440×900 contra `mockups/index.html`:

1. `/reservar`: catálogos, fecha, resultados, selección y presentación de demora, vacío y 429; comprobar foco y ausencia de desborde.
2. Sin sesión: selección, enlaces a ingreso/registro y regreso sin envío automático; con paciente verificado: resumen, envío, éxito y correo sin verificar.
3. Reserva: 403, máximo 409, alternativas con otras fechas y sin resultados; error de red y doble clic.
4. `/mis-turnos`: lista vacía y con estados, profesional no disponible, acciones permitidas, teléfono fuera de plazo y turno liberado.
5. Confirmación, cancelación y reprogramación: revisión previa, éxito, error, duración distinta, 409/422 y conservación del turno anterior.
6. Enlace de confirmación con respuesta 409: opción de volver a reservar. Comprobar consola y peticiones fallidas en cada recorrido y guardar capturas de comparación.

Se recomienda configurar el navegador del harness Playwright o utilizar un navegador local accesible; registrar diferencias por prioridad y viewport después de observarlas. Los mockups aprobados son referencia, no prueba de coincidencia.
