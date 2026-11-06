# Evidencia C-13

## Aprobación

El usuario aprobó explícitamente el mockup de la revisión 2 el 2026-11-06. La revisión previa fue manual; no se generaron capturas automáticas ni se inspeccionó el render mediante navegador automatizado.

## Ciclos TDD registrados

| Tarea | Pruebas y capa | Red de seguridad | RED | GREEN y triangulación |
| --- | --- | --- | --- | --- |
| 2.1 | `backend/tests/integration/test_c13_contexto.py`, PostgreSQL/HTTP | 46/46 `test_c07_agenda.py` | Contexto inexistente (404) | 6/6 roles, ausencia, identidad y aislamiento |
| 2.2 | `test_c13_contexto.py`, `test_c07_agenda.py`, `test_c10_sobreturnos.py`, `test_c09_patient_actions.py`, PostgreSQL/HTTP | 46/46 lecturas operativas | Campo faltante, acciones de profesional y administrador con agenda, profesional inactivo | 89/89 lectura y sobreturnos; 34/34 contexto y acciones paciente; escritura revalida estado cambiado |
| 3.1 | `frontend/src/staff/AgendaPage.test.tsx`, `frontend/src/shell/routes.test.tsx`, RTL | 8/8 rutas y layout | Página y ruta inexistentes; horarios, selección y limpieza | 17/17 agenda y shell, zona, vacío/error, reintento, roles y respuesta antigua |
| 3.2 | `frontend/src/staff/StaffTurno.test.tsx`, RTL | Página nueva; 8/8 shell existente | Alta y sus controles inexistentes | Alta, ficha parcial, 409/422, incertidumbre, hora manual, búsqueda y duplicados |
| 3.3 | `frontend/src/staff/StaffTurno.test.tsx`, RTL | Página nueva; API existente cubierta por integración | Acciones y detalle inexistentes | Acciones por autorización, recarga, conflicto y movimiento; 20/20 suite de turnos |
| 3.4 | `frontend/src/staff/StaffTurno.test.tsx`, RTL | API de sobreturnos: 89/89 junto a agenda/contexto | Controles de autorización y respuesta inexistentes | Motivo, autorización, roles y rechazo sin cancelar; 20/20 suite de turnos |
| 4.1–4.3 | `frontend/src/records/` pruebas RTL | Páginas nuevas; API previa de fichas y vínculos | Búsqueda, detalle, edición y resolución inexistentes | 15/15 pruebas dirigidas informadas para roles, selección, conflicto, vínculo, motivo, enlace y sesión |

## Verificación final

- Backend dirigido: 113/113 pruebas PostgreSQL (`test_c13_contexto.py`, `test_c07_agenda.py`, `test_c09_patient_actions.py`, `test_c10_sobreturnos.py`). Alembic tiene una sola cabeza: `0011_overbooking_authorization`; C-13 no agrega migración.
- Frontend: primer intento paralelo 169/170, con tiempo de espera agotado en una prueba de agenda bajo carga; repetición final con `--maxWorkers=2` 173/173 sobre los archivos definitivos. Typecheck y build final aprobados.
- Comparación visual: manual y pendiente de ejecución. Playwright no pudo iniciar porque Chrome configurado está ausente; no se generaron capturas ni se inspeccionó el render de implementación. Guía por pantalla y viewport en `mockups/verify/README.md`.
