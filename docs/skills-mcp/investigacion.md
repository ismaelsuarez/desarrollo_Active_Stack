# Ficha de investigación: skill y MCP

**Proyecto:** Gestión de turnos y prevención de solapamientos · **Agente de referencia:** OpenAI Codex (CLI/IDE) · **Fuentes consultadas:** 03/11/2026 · **Estado:** investigación; pruebas locales pendientes.

> Ficha histórica de la Parte 1: sus propuestas y pendientes describen ese momento, no el estado actual. La [aplicación de la Parte 2](aplicacion.md), la [guía comprobada](context7.md) y la [revisión crítica](revision-critica.md) documentan los resultados posteriores y las diferencias respecto de esta propuesta. No usar esta ficha como constancia de instalación ni atribución definitiva de la skill creadora.

## 1. Necesidad y change

**Necesidad:** revisar repetidamente reglas de reserva, duración y disponibilidad para detectar conflictos de horarios y casos de borde. **Change:** agregar/reforzar la validación de solapamientos al crear o reprogramar turnos. Para un mismo profesional, dos intervalos `[inicio, fin)` se superponen si `inicioA < finB && finA > inicioB`; dos turnos contiguos no se superponen. También se requieren pruebas de reservas simultáneas.

**Complemento:** la *skill* identifica escenarios, ambigüedades y casos de prueba; el *MCP* permite consultar documentación técnica para implementar el change con el stack real. Ninguno reemplaza las pruebas del sistema.

## 2. Skill creadora y propuesta

**Creadora:** `skill-creator` de OpenAI (repositorio oficial `openai/skills`), compatible e incluida como skill del sistema en Codex. **Comprobación:** abrir Codex, ejecutar `/skills` e invocar `$skill-creator` (no requiere instalación adicional si aparece). **Uso:** pedirle generar una skill con nombre, activación, procedimiento y resultados definidos.

**Skill propia:** `appointment-conflict-reviewer`, guardada en `.agents/skills/appointment-conflict-reviewer/SKILL.md` desde la raíz del repositorio, con encabezado YAML `name` y `description`.

- **Activación:** revisión, implementación o pruebas de reglas de turnos y reprogramaciones.
- **Entradas:** reglas de negocio, horario y duración, profesional, recursos compartidos, código y tests disponibles.
- **Procedimiento:** revisar superposiciones totales/parciales, turnos contiguos, profesionales diferentes, cancelaciones, reprogramaciones y concurrencia; señalar condiciones ambiguas; generar casos de prueba.
- **Salida:** matriz «escenario, entrada, resultado esperado, riesgo» y recomendaciones, sin modificar turnos reales.
- **Criterios:** cobertura de límites y excepciones, expectativas verificables y coherencia con requisitos. **Prueba:** 09:00–10:00 y 09:30–10:30 para el mismo profesional deben marcarse como conflicto. Verificar detección con `/skills` e invocación `$appointment-conflict-reviewer`.

## 3. Comparación de MCP

| Criterio | Context7 (Upstash) | Filesystem (Model Context Protocol) |
|---|---|---|
| Propósito y herramientas | Consulta documentación de librerías: `resolve-library-id`, `query-docs`. | Lista, busca, lee, crea y modifica archivos locales. |
| Compatibilidad | Codex vía MCP (CLI/configuración). | Codex vía servidor local `stdio`. |
| Instalación | `npx ctx7 setup --codex` y elegir modo **MCP**; requiere Internet y Node.js/`npx`. | `npx -y @modelcontextprotocol/server-filesystem <directorio>`; Node.js **24+**; en Windows, `cmd /c npx`. |
| Acceso y credenciales | Consultas a documentación; OAuth y clave configurada por el asistente. No escribe archivos del proyecto. | Acceso de lectura **y escritura** dentro de carpetas autorizadas; permisos locales, sin cuenta externa. |
| Costos | Plan Free USD 0: 1.000 llamadas API/mes; planes pagos opcionales. | Código abierto MIT, sin licencia paga; usa recursos del equipo. |

**Elección: Context7.** Permite consultar ejemplos y documentación actualizada sobre intervalos de tiempo, persistencia o testing sin acceso de escritura a las reservas. Filesystem serviría para inspeccionar el repositorio, pero concede capacidades potencialmente destructivas. **Límite de Context7:** no lee automáticamente el código local ni verifica por sí mismo la prevención de condiciones de carrera.

## 4. Instalación, comprobación y herramienta

1. En el equipo con Codex, verificar disponibilidad de `codex` y `npx` (pendiente).
2. Ejecutar `npx ctx7 setup --codex`, seleccionar **MCP server**, completar OAuth y revisar los cambios generados en `~/.codex/config.toml` y `AGENTS.md`.
3. Ejecutar `codex mcp list`; dentro del agente consultar `/mcp` para comprobar la conexión.
4. Solicitar: «Usá Context7: ejecutá `resolve-library-id` para **date-fns** y luego `query-docs` con el ID obtenido para documentar cómo comparar intervalos horarios en JavaScript. Mostrá las herramientas utilizadas y el resultado». *Ejemplo de prueba: adaptar biblioteca y lenguaje al stack real.*
5. Confirmar que aparecen las herramientas y se devuelve documentación relevante; si falla, registrar mensaje de error, autenticación y conexión.

**Datos y límites:** usar exclusivamente citas ficticias; no enviar nombres, teléfonos, historias clínicas, secretos, tokens o bases de datos. No otorgar permisos sobre datos productivos ni incorporar credenciales al repositorio. Context7 se usará para consultas técnicas, no para crear, cambiar o cancelar turnos.

## 5. Archivos de fundación previstos y pendientes

- `docs/skills-mcp/investigacion.md`: ficha de investigación.
- `.agents/skills/appointment-conflict-reviewer/SKILL.md`: instrucciones de skill a crear.
- `AGENTS.md` (si existe): reglas de invocación y uso de Context7, previa revisión.
- Tests del módulo de turnos y `README.md`: escenarios y forma de ejecución, según la estructura existente.

**Pendiente de verificar:** agente y stack reales, existencia de archivos, generación/ejecución de la skill, conexión Context7 y evidencia de llamadas MCP. **No se afirma una instalación o prueba ya realizada.**

## Fuentes oficiales (consulta: 03/11/2026)

1. OpenAI, skills: https://learn.chatgpt.com/docs/build-skills
2. OpenAI, `skill-creator`: https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md
3. OpenAI, Codex/MCP: https://learn.chatgpt.com/docs/extend/mcp
4. Upstash, Context7/Codex: https://github.com/upstash/context7/blob/master/docs/clients/codex.mdx
5. Context7, herramientas: https://context7.com/docs/resources/all-clients
6. Context7, precios: https://context7.com/plans
7. MCP, Filesystem: https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md
