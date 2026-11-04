# Revisión crítica y alcance de la entrega

> Revisión histórica previa a la implementación de C-07. Sus referencias enlazan ahora al archivo; el cierre posterior consta en [CHANGES.md](../../CHANGES.md).

Comprobaciones del 03/11/2026. Se distingue un antecedente histórico, una reproducción actual y una decisión humana. No se alteraron la KB, la fundación, los hooks globales ni código de C-07 para producir este informe.

## 1. Gentle AI: ausencia anterior y disponibilidad actual

**Antes:** la [exportación de Engram #110](evidencias/gentle-ai-antecedente.json), correspondiente a la integración de la skill, registra `Cannot execute gentle-ai [WinError 2]` al ejecutar el refresco y la ausencia de ejecutable en PATH. Es un registro histórico de sesión, **no la captura original ni una nueva ejecución del error**.

**Después comprobado:** `Get-Command gentle-ai` encuentra `%USERPROFILE%\go\bin\gentle-ai.exe` y `gentle-ai --version` devuelve `gentle-ai 4.3.1`; véase [salida actual](evidencias/verificacion-entorno.txt). `.atl/skill-registry.md`, línea 23, contiene la entrada canónica de la skill.

**Causa y límite:** [refresh.py](../../.agents/skills/skill-registry/scripts/refresh.py), líneas 18–25, ejecuta `gentle-ai` por nombre y convierte el error del sistema en `RefreshError`: depende del PATH del proceso. La disponibilidad está resuelta en esta shell; no consta quién instaló el binario o cambió PATH entre sesiones. Ese paso y la salida original del fallo quedan pendientes de evidencia. No se instaló Gentle AI ni se ejecutó su refresco durante esta revisión; no se atribuye al TP una reparación no registrada.

## 2. Registro: problema de lectura, no corrupción demostrada

**Antes reproducido:** `Get-Content .atl/skill-registry.md` en Windows PowerShell muestra `odontolÃ³gicos` y `diseÃ±ar` en la descripción de la skill.

**Después reproducido sobre el mismo archivo:**

```powershell
Get-Content -Encoding UTF8 .atl/skill-registry.md
```

Muestra `odontológicos` y `diseñar`; el decodificador UTF-8 estricto acepta sus bytes. Las dos salidas están juntas en [verificacion-entorno.txt](evidencias/verificacion-entorno.txt). No se reescribió el registro para obtener el resultado: se explicitó la codificación al leer.

Fuente adicional: [refresh.py](../../.agents/skills/skill-registry/scripts/refresh.py), línea 94, genera bytes con `.encode()`; el diff del índice agrega solo la fila de la skill y el de la caché cambia el fingerprint. No hay en el diff una reparación de encoding del generador. Su `subprocess.run(..., text=True)` de línea 22 no fija encoding; es un riesgo de portabilidad a comprobar, **no un fallo adicional demostrado**. No se regeneró el índice para documentarlo.

## 3. RN-44, US-028 y ausencia al inicio

| Fuente exacta | Texto relevante | Lectura |
| --- | --- | --- |
| [KB 05](../../knowledge-base/05_reglas_de_negocio.md), línea 103, RN-44 | «una vez que pasó su hora de inicio» | Admite lectura estricta `>` |
| [KB 06](../../knowledge-base/06_funcionalidades.md), línea 374, US-028 | «Solo en turnos propios y una vez pasada la hora de inicio.» | Admite lectura estricta `>` |
| [KB 11](../../knowledge-base/11_politicas_de_acceso_abac.md), líneas 27 y 62 | «solo desde la hora de inicio»; `ahora >= turno.inicio (para atendido y ausente)` | Explicita `>=` |
| [KB 07](../../knowledge-base/07_flujos_principales.md), línea 305, flujo 8 | «A4 (hora de inicio alcanzada)» | Respalda `>=` |
| [KB 09](../../knowledge-base/09_decisiones_y_supuestos.md), línea 33, DD-04 | Remite el detalle de las políticas a KB 11 | Refuerza el contrato operativo, sin reemplazar expresamente RN-44 |

DD-18 (KB 09, línea 135) define la liberación automática; DD-32 (línea 235) el estado al reservar con poca anticipación. Ninguna decide la igualdad para ausente. La spec ABAC principal y el código existentes usan `>=`; su coincidencia era evidencia técnica, no autorización para resolver por sí sola una contradicción de dominio.

**Antes:** igualdad clasificada como ambigua en la revisión y pendiente en C-07. La captura [skill-resultado.png](evidencias/skill-resultado.png) exige resolver el instante exacto antes de aceptarlo. La preparación se detuvo antes de cerrar tareas.

**Decisión y después:** el usuario confirmó «si» a adoptar `ahora >= inicio` manteniendo la KB sin modificaciones. La confirmación está registrada en [design.md](../../openspec/changes/archive/2026-11-03-c-07-turnos-core/design.md), líneas 146–156; [lifecycle](../../openspec/changes/archive/2026-11-03-c-07-turnos-core/specs/appointment-lifecycle/spec.md), línea 90, agrega el escenario exacto; [tasks.md](../../openspec/changes/archive/2026-11-03-c-07-turnos-core/tasks.md), tarea 5.5, exige probar antes/exacto/después con Reloj. Al redactar este informe, `CHANGES.md` conservaba `[ ]` y referenciaba el criterio confirmado.

Para un inicio 10:00: 09:59:59 se rechaza; 10:00:00 y 10:00:01 se permiten si estado, rol y agenda habilitan la acción. No se inventó período de tolerancia ni nueva DD. **El criterio de C-07 está resuelto; la coherencia textual de la KB no está completamente resuelta.** Sin autorización para editarla, RN-44/US-028 conservan su redacción; sincronizarlas es un pendiente documental, no una decisión temporal todavía abierta para C-07. La captura o exportación original de la confirmación sigue pendiente; el artefacto registra su trazabilidad.

## 4. Límites de la evidencia y correcciones respecto de la investigación

- [investigacion.md](investigacion.md) es una propuesta de Parte 1. Su afirmación de skill-creator de OpenAI no identifica por sí sola qué copia resolvió la invocación. El [lock local](../../skills-lock.json) registra `anthropics/skills`; las capturas muestran la invocación genérica y el resultado. No atribuir una procedencia exacta sin registro de resolución del cliente.
- Las cinco PNG fueron abiertas e inspeccionadas. La captura `escenarios A, B y C con sus reglas.png` muestra B/C y pruebas propuestas A/B/C; no es una captura completa de los tres escenarios ni prueba ejecutada.
- Las nuevas evidencias JSON/TXT proceden de herramientas reales de esta sesión. No son capturas de pantalla ni reconstrucciones de las primeras ejecuciones. La configuración de Context7 solo se exportó como comprobaciones estructurales, nunca como contenido con credenciales.
- La [validación OpenSpec](evidencias/openspec-validacion.json) es válida sin issues y con 0/36 tareas hechas. No prueba SQLSTATE, ausencia de carreras ni comportamiento API. `SU-39` y las pruebas futuras conservan esa limitación; la carrera residual con sobreturnos sigue documentada.
- No se ejecutó `codex mcp list` en esta shell porque `codex` no está en PATH. Las herramientas Context7 sí funcionan en la sesión del agente. La guía distingue esas comprobaciones y no presenta la instalación de un equipo limpio como ya realizada.

## Inventario del diff

Se revisaron `git status`, `git diff` completo de los archivos ya versionados y las rutas nuevas. `git diff` solo no muestra archivos sin seguimiento. La [instantánea de auditoría](evidencias/git-auditoria.txt) complementa el estado; no se hizo stage, commit ni limpieza.

### Archivos creados o modificados en esta entrega documental

| Archivo | Cambio y motivo |
| --- | --- |
| `README.md` | Enlaza informe, configuración, revisión e índice de evidencias. |
| `docs/skills-mcp/investigacion.md` | Agrega aviso histórico y enlaces; conserva el texto original de la Parte 1. |
| `docs/skills-mcp/aplicacion.md` | Informe breve de aplicación, resultados y límites, dividido en dos bloques de página. |
| `docs/skills-mcp/context7.md` | Requisitos, registro HTTP sin secretos, ubicación, comprobación y uso real. |
| `docs/skills-mcp/revision-critica.md` | Fuentes, antes/después, discrepancia de KB, inventario y pendientes. |
| `docs/skills-mcp/evidencias/README.md` | Identifica alcance y limitaciones de cada evidencia. |
| `docs/skills-mcp/evidencias/context7-ejecucion.json` | Registro nuevo de resolución y dos consultas MCP reales, con argumentos y respuestas públicas. |
| `docs/skills-mcp/evidencias/verificacion-entorno.txt` | Salida real de PATH, versiones, estructura MCP, lectura UTF-8 e igualdad AGENTS/CLAUDE. |
| `docs/skills-mcp/evidencias/gentle-ai-antecedente.json` | Exporta la memoria histórica #110 identificando su procedencia y límites. |
| `docs/skills-mcp/evidencias/openspec-validacion.json` | Conserva validación estricta y conteo de tareas obtenidos de la CLI. |
| `docs/skills-mcp/evidencias/git-auditoria.txt` | Instantánea del estado y alcance de los cambios observados. |

### Cambios previos que ya estaban en el workspace

| Archivos | Motivo observado / relación con el TP |
| --- | --- |
| `.agents/skills/appointment-conflict-reviewer/SKILL.md` | Skill propia nueva, relacionada con el TP; no editada en esta entrega documental. |
| `AGENTS.md`, `CLAUDE.md` | Misma fila y sección de integración de la skill; contenido idéntico verificado. |
| `.atl/skill-registry.md`, `.atl/.skill-registry.cache.json` | Nueva fila generada y fingerprint distinto; no refrescados aquí. |
| `CHANGES.md` | Referencia a C-07 preparado, criterio confirmado y checkbox sin marcar. |
| `openspec/changes/c-07-turnos-core/.openspec.yaml` | Metadata creada previamente con la CLI. |
| `openspec/changes/c-07-turnos-core/proposal.md`, `design.md`, `tasks.md` | Planificación previa; no alterada para este informe. |
| `openspec/changes/c-07-turnos-core/specs/appointment-booking/spec.md`, `appointment-lifecycle/spec.md`, `appointment-agenda/spec.md`, `core-data-models/spec.md`, `attribute-based-access-control/spec.md` | Cinco deltas previos que fundamentan las tareas; todos bajo el mismo directorio specs. |
| Cinco PNG de `docs/skills-mcp/evidencias/` | Evidencias aportadas previamente, inspeccionadas y conservadas con sus nombres. |
| `skills-lock.json` | Instalación previa de skill-creator desde Anthropic: auxiliar del TP, no cambio de C-07 ni requisito del servidor Context7. Revisar su inclusión al seleccionar el commit. |

**Cambios ajenos:** no se encontraron diferencias versionadas de backend, frontend, KB, configuración de OpenSpec, scripts del registro ni estado de fundación. El lock de instalación y la caché son cambios instrumentales previos que deben revisarse, no modificaciones realizadas por esta documentación. `node_modules/` de OpenSpec es una instalación local ignorada, fuera del diff. No se afirma que la máquina completa esté libre de otros cambios.

## Pendientes para la entrega

1. Si la consigna exige evidencia visual del MCP: capturar ajustes con credenciales ocultas y una llamada visible; los JSON aportados prueban ejecución textual, no esa interfaz.
2. Obtener la salida original de `WinError 2` y el paso que hizo disponible Gentle AI; no recrearlo artificialmente como evidencia histórica.
3. Reproducir la configuración en un cliente/equipo limpio; aquí se verificó la integración ya existente. No hace falta hacerlo sobre datos reales.
4. Si se autoriza, sincronizar la redacción de RN-44 y US-028 con el criterio confirmado. No hacerlo automáticamente.
5. Al exportar el informe Markdown, comprobar que respeta dos páginas. Seleccionar y versionar los archivos del TP tras revisar el inventario; no se realizó commit ni push.
