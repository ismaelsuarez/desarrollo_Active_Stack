# Parte 2 — Aplicación de Skills y MCP

> Informe histórico previo a la implementación. C-07 se completó y archivó después; el estado actual figura en [CHANGES.md](../../CHANGES.md).

**Proyecto odontológico · 03/11/2026.** Resultado: skill integrada, Context7 ejecutado y C-07 planificado, sin implementar ni archivar. La [guía reproducible](context7.md), la [revisión crítica](revision-critica.md) y el [índice de evidencias](evidencias/README.md) amplían este informe breve.

## Creación e integración

Se invocó `skill-creator` para crear [appointment-conflict-reviewer](../../.agents/skills/appointment-conflict-reviewer/SKILL.md). Las capturas [invocación](evidencias/incvocacion_skill-creator.png), [pedido de creación](evidencias/creacion-skill.png) y [resultado](evidencias/Skill-creada.png) muestran el proceso. La última informa aprobación de `quick_validate.py`; no se conserva su salida completa. `skills-lock.json` registra una instalación de `skill-creator` desde Anthropic; la ficha inicial mencionaba la alternativa de OpenAI, por lo que no se atribuye la copia ejecutada solo por su nombre.

La skill revisa intervalos, agenda, estados, permisos y concurrencia; clasifica escenarios permitidos, rechazados o ambiguos y exige referencias RN/US/DD/SU/Q. No modifica turnos, artefactos ni datos reales. Se integró mediante una fila de rol y una sección idéntica en `AGENTS.md` y `CLAUDE.md`; el registro local generado incluye su ruta canónica. No se regeneró la fundación.

La aplicación a C-07 identificó contigüidad, superposición y dos reservas simultáneas, además de límites temporales y atomicidad. Las capturas [escenarios](<evidencias/escenarios A, B y C con sus reglas.png>) y [recomendaciones](evidencias/skill-resultado.png) son revisión documental, no resultados de tests.

## Ejecución real de Context7

Se ejecutaron las herramientas MCP reales `mcp__context7__resolve_library_id` y `mcp__context7__query_docs`. La [nueva comprobación guardada](evidencias/context7-ejecucion.json) conserva argumentos y respuestas públicas: resolución de SQLAlchemy, consulta a `/websites/sqlalchemy_en_20_orm` y consulta a `/websites/sqlalchemy_en`.

Las fuentes oficiales de SQLAlchemy 2.0 respaldaron una sesión asíncrona por tarea, el manejo de transacciones/rollback y la exclusión PostgreSQL con `&&`, predicado y `btree_gist`. Aplicadas a C-07: sesiones independientes evitan compartir estado, pero la garantía de una sola reserva regular depende de la exclusión; el prechequeo de disponibilidad no basta.

<div style="break-after: page; page-break-after: always;"></div>

## Resultados y revisión crítica

C-07 contiene propuesta, diseño, cinco deltas y **36 tareas pendientes** con verificaciones TDD, PostgreSQL real y concurrencia controlada. La [validación estricta capturada](evidencias/openspec-validacion.json) pasó sin observaciones; registra **0/36 implementadas**. `CHANGES.md` conserva `[ ]`.

| Problema real | Antes y después comprobables |
| --- | --- |
| `gentle-ai` fuera de PATH | La memoria histórica registra `WinError 2`; ahora se localiza el ejecutable y responde 4.3.1. No consta el paso intermedio que lo corrigió. |
| Codificación del registro | PowerShell por defecto muestra `odontolÃ³gicos`; UTF-8 explícito muestra `odontológicos` sobre los mismos bytes válidos. Se corrigió la lectura, no se reescribió el archivo. |
| Ausente en la hora exacta | RN-44/US-028 admitían `>`; KB 11 explicita `>=`. Tras consultar al usuario, C-07 adoptó `>=` y agregó el caso exacto. La KB permanece sin editar. |

Las fuentes, líneas y comparación detallada están en [revisión crítica](revision-critica.md). La confirmación resolvió el criterio de C-07; **persiste una diferencia de redacción en la KB**, pendiente de autorización para sincronizarla.

## Alcance y entrega pendiente

El aporte verificable es preparar contratos, riesgos y pruebas futuras. No se ejecutaron tests de aplicación de C-07 ni se confirmó SU-39 mediante integración en esta entrega. La carrera residual regular/sobreturno continúa documentada. Context7 no resuelve reglas de negocio ni sustituye pruebas; la skill tampoco aprueba decisiones humanas.

Se añadieron documentación, enlaces y comprobaciones textuales reales, preservando las cinco capturas originales. El [inventario](revision-critica.md#inventario-del-diff) enumera archivos y motivos, incluidos los cambios previos de la skill y C-07. No aparecen cambios de backend/frontend/KB/configuración de OpenSpec; `skills-lock.json` corresponde a la instalación previa de la creadora y debe revisarse al seleccionar la entrega.

Pendientes: captura de la configuración MCP con valores ocultos y de una llamada visible en el cliente; evidencia original del error de PATH y del paso que lo resolvió; reproducción en equipo limpio y revisión de paginación al exportar este Markdown. No se inventaron esas evidencias ni se incluyeron secretos.
