# Evidencias de Skills y MCP

Las cinco PNG ya estaban en el workspace y se inspeccionaron sin modificarlas. Los JSON/TXT indicados son comprobaciones nuevas, no capturas ni logs reconstruidos. No incluyen credenciales ni pacientes reales.

| Evidencia | Qué permite comprobar | Límite |
| --- | --- | --- |
| [incvocacion_skill-creator.png](incvocacion_skill-creator.png) | Invocación visible de `$skill-creator` en Codex. | No identifica la ruta exacta de la copia resuelta. Se conserva el nombre original. |
| [creacion-skill.png](creacion-skill.png) | Pedido, alcance y procedimiento de creación de la skill. | No demuestra la terminación del proceso. |
| [Skill-creada.png](Skill-creada.png) | Resultado que informa creación, validación aprobada y límites. | Es resumen del agente; falta salida completa del validador. |
| [escenarios A, B y C con sus reglas.png](<escenarios A, B y C con sus reglas.png>) | Escenarios B/C y pruebas propuestas A/B/C con reglas. | Captura parcial; no muestra toda la matriz ni ejecución de tests. |
| [skill-resultado.png](skill-resultado.png) | Riesgos y aportes de la revisión a specs/propuesta/diseño/tareas. | Explicita ausencia de validación de implementación. |
| [context7-ejecucion.json](context7-ejecucion.json) | Llamadas reales del servidor MCP: argumentos, resolución y documentación oficial de SQLAlchemy. | Es una comprobación posterior; no captura las primeras llamadas de la conversación. |
| [verificacion-entorno.txt](verificacion-entorno.txt) | Gentle AI disponible, contraste de decodificación, estructura MCP sin valores secretos y ausencia de Codex CLI en PATH. | No demuestra una instalación en equipo limpio ni el paso que reparó PATH. |
| [gentle-ai-antecedente.json](gentle-ai-antecedente.json) | Exportación identificada del registro histórico de Engram #110 con WinError 2. | No es el log ni la captura original de terminal. |
| [openspec-validacion.json](openspec-validacion.json) | Resultado estricto válido y 0/36 tareas implementadas. | Valida documentos, no reservas concurrentes. |
| [git-auditoria.txt](git-auditoria.txt) | Estado y alcance del diff observado al documentar la entrega. | Instantánea; no sustituye revisar Git antes de un commit. |

Pendientes visuales: configuración Context7 con secretos ocultos y llamada visible en el cliente. Pendientes históricos: salida original del fallo de Gentle AI, resolución del PATH, ruta resuelta de la creadora y confirmación original del criterio temporal. La confirmación está trazada en el diseño de C-07. No se fabricaron imágenes para completar esas ausencias.
