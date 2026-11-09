# Demostración reproducible: skill y MCP en C-07

Este documento prepara la defensa del TPI; no modifica ni reconstruye el historial archivado de C-07. El cambio original y su evidencia están en [`design.md`](../../openspec/changes/archive/2026-11-03-c-07-turnos-core/design.md) y [`tasks.md`](../../openspec/changes/archive/2026-11-03-c-07-turnos-core/tasks.md).

## Skill propia

1. Abrir el proyecto y comprobar que existe `.agents/skills/appointment-conflict-reviewer/SKILL.md`.
2. En una sesión del agente que tenga acceso a la skill, pedir: `$appointment-conflict-reviewer revisá C-07, en particular dos turnos del mismo profesional entre 10:00–10:30 y 10:30–11:00, y un tercero entre 10:15–10:45. No modifiques archivos ni uses datos reales.` Si el cliente no reconoce la invocación por nombre, indicar la ruta al `SKILL.md` y pedir que siga sus instrucciones.
3. Mostrar la revisión y contrastarla con RN-17 en `knowledge-base/05_reglas_de_negocio.md`, el intervalo semiabierto `[inicio, fin)` del modelo y los escenarios ESC-01 y ESC-02 de C-07. Los intervalos contiguos no se superponen; el tercero sí se superpone. Las demás reglas y permisos deben cumplirse por separado.
4. Explicar que la revisión de dominio identifica escenarios y riesgos; no es por sí sola una ejecución de pruebas. Mostrar los tests de concurrencia y exclusión vinculados desde `tasks.md` y el resultado de la suite de integración.

La evidencia histórica de aplicación de la skill aparece en la sección «Revisión de dominio — appointment-conflict-reviewer» del diseño archivado; las capturas disponibles y sus límites se enumeran en [`evidencias/README.md`](evidencias/README.md).

## Context7

1. Con Context7 conectado, consultar la biblioteca `SQLAlchemy` y resolver su identificador.
2. Para la versión 2.0, elegir `/sqlalchemy/sqlalchemy/rel_2_0_55` y preguntar: «¿Es seguro compartir una AsyncSession entre tareas asyncio concurrentes y qué patrón se recomienda?».
3. La consulta ejecutada durante la preparación devolvió la documentación de SQLAlchemy: una sesión asíncrona es mutable y no debe compartirse concurrentemente; se recomienda una sesión por tarea. Mostrar cómo esa decisión se relaciona con las transacciones y pruebas concurrentes descritas en el diseño de C-07.
4. Mostrar la llamada y su respuesta en el cliente, sin claves ni información de pacientes. La respuesta puede variar si cambia el índice de Context7.

La ejecución original y su aplicación a C-07 están documentadas en `design.md`; [`evidencias/context7-ejecucion.json`](evidencias/context7-ejecucion.json) contiene llamadas verificables previas. No presenta una captura de pantalla de la llamada de esta preparación: grabarla durante la defensa.

## Secuencia sugerida para el video

Mostrar primero la regla y los intervalos sintéticos, invocar la skill, consultar Context7 y señalar los vínculos al diseño, tareas y pruebas archivadas. A continuación, demostrar el sistema con la base temporal de la práctica. No usar credenciales reales ni mostrar secretos.
