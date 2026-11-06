# Evidencia C-18

- El usuario aprobó el mockup revisión 2 el 2026-11-06; está registrado en `design.md` y `mockups/README.md`.
- Red de seguridad previa: 66/66 pruebas de shell, sesión, API y agenda.
- Suite frontend final: 238/238 pruebas; `typecheck`, `build`, OpenSpec `--strict` y `git diff --check` aprobados. Git informó únicamente avisos de finales de línea LF/CRLF.
- Playwright con Edge y API simulada: 5/5; incluye Tab, Enter y Shift+Tab entre bandejas, vista WhatsApp, correos con fila y vacío, turnos con fila, detalle, salud y error, en 390×844 y 1440×900 donde se indica. Las verificaciones de permisos, 409, ventanas bloqueadas y resultado incierto están cubiertas por pruebas de componentes; no se afirma navegación completa con teclado en todas las pantallas.
- En pantalla de turnos y salud no se observaron errores de JavaScript ni solicitudes fallidas durante la prueba instrumentada; el estado de error de correo fue una respuesta 500 simulada de forma intencional. No se verificaron consola y red de todas las demás pantallas.
- La revisión visual se registró en `mockups/verify/README.md`; existen diferencias y estados que aún requieren inspección. Las capturas usan datos simulados y no prueban integración con una API real.

## Evidencia de TDD

| Tarea | Pruebas | Red de seguridad | RED | GREEN y triangulación | Refactor |
| --- | --- | --- | --- | --- | --- |
| 2.1 Rutas | `src/shell/routes.test.tsx` | 66/66 | Ruta inexistente | 13 casos de rutas; roles, ingreso y acceso | Sin cambios de comportamiento |
| 2.2 Bandejas | `src/notifications/NotificationsPage.test.tsx` | 66/66 | Faltaban consulta y estados | Carga, vacío, error, filtros, paginación y proyección | Agrupación visual de bandejas |
| 2.3 Acciones | `src/notifications/NotificationsPage.test.tsx` | 66/66 | Botones ausentes; doble POST reproducido | Enlace seguro, popup, marca, 409, incertidumbre y doble activación | Guarda con referencia de operación en curso |
| 2.4 Contadores | `src/notifications/Counters.test.tsx`, `Summary.test.tsx` | 66/66 | Componentes ausentes; conteo no se actualizaba | 0/99/100, carga, error y actualización | Etiquetas acotadas solo para bandejas |
| 3.1 Sin confirmar | `src/notifications/Unconfirmed.test.tsx`, `src/staff/StaffTurno.test.tsx` | 66/66 | Detalle sin acción liberar | Lista, error, retorno, permiso, éxito y conflicto de detalle | Reutilización de detalle existente |
| 3.2 Salud | `src/notifications/Health.test.tsx` | 66/66 | Panel ausente | Cuota 79/80 %, ausente/antiguo, antigüedad, cero y error | Tarjetas responsivas |
| Hora de consultorio | `src/notifications/time.test.ts` | Nueva función | Módulo ausente | UTC, Argentina y datos inválidos | Función compartida |

La evidencia RED de las tareas se registró durante su implementación; los conteos de la suite completa corresponden a la ejecución final, no a un recorrido real contra backend.
# Revisión adicional del enlace alternativo

La red de seguridad de `NotificationsPage.test.tsx` fue 11/11. Dos casos nuevos de conflicto 409 y escritura incierta fallaron primero porque el enlace alternativo seguía visible; tras limpiar el enlace al iniciar la marca manual, pasaron 13/13. Playwright Edge pasó 8/8 con API simulada; typecheck pasó. No se afirma verificación con API real ni por teclado de todas las interacciones.
