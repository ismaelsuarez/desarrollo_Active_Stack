# Context7 MCP: configuración reproducible en Codex

Guía del TP, consultada el 03/11/2026. No modifica configuraciones de la máquina. Distingue el procedimiento para otro equipo de lo comprobado en esta sesión.

## Requisitos y registro del servidor

Para la conexión HTTP: Codex con soporte MCP, acceso HTTPS a Context7 y una credencial propia gestionada fuera del repositorio. El servidor remoto evita instalar un proceso Node local. La documentación de [Context7 para Codex](https://context7.com/docs/clients/codex) explica ambas modalidades.

Ruta elegida para reproducir: agregar el servidor remoto a la configuración de usuario `%USERPROFILE%\.codex\config.toml` en Windows (`~/.codex/config.toml` en otros sistemas). Conservar el contenido existente; agregar o ajustar solo esta tabla, sin duplicarla:

```toml
[mcp_servers.context7]
url = "https://mcp.context7.com/mcp"
bearer_token_env_var = "CONTEXT7_API_KEY"
```

La variable contiene la clave obtenida en la cuenta propia de Context7; este ejemplo solo registra su nombre. Provisionarla mediante el entorno o gestor de secretos antes de iniciar Codex. No copiar su valor a TOML, comandos guardados, capturas, logs ni Git. La [referencia oficial de Codex MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) documenta `url`, `bearer_token_env_var`, configuración de usuario y configuración por proyecto confiable (`.codex/config.toml`). Este proyecto no necesita agregar ese archivo local.

Con la CLI disponible, comprobar el registro y las opciones de esa versión:

```powershell
codex mcp list
codex mcp --help
```

Estos comandos son instrucciones para reproducir; **no se ejecutaron aquí**, porque `codex` no está en el PATH de esta shell. La tabla TOML anterior permite registrar el servidor sin depender de esos comandos. En Codex Desktop puede revisarse la conexión en sus ajustes MCP y abrir un hilo nuevo con las herramientas disponibles.

Alternativa documentada por el proveedor: `npx ctx7 setup --codex`, elegir **MCP**. Ese instalador requiere Node.js 22.13 o posterior y puede escribir configuración, reglas y una skill: revisar sus cambios antes de usarlo sobre esta fundación. No se ejecutó en esta entrega. Véanse [instalación oficial](https://github.com/upstash/context7#installation) y [guía del cliente](https://context7.com/docs/clients/codex). No hace falta instalar paquetes globales para la ruta HTTP anterior.

## Comprobación y uso efectivo

1. Comprobar el servidor configurado y habilitado en el cliente. Esto solo verifica configuración; no basta para demostrar una consulta.
2. Abrir una sesión con acceso a las herramientas MCP y solicitar:

   > Usá Context7 MCP: resolvé SQLAlchemy 2.0 y consultá su documentación oficial sobre una AsyncSession por tarea concurrente, transacciones y rollback. Indicá la herramienta real, el ID elegido y las fuentes. No implementes código ni envíes información del consultorio.

3. Exigir primero `resolve-library-id`, luego `query-docs` con el ID devuelto y una pregunta concreta. En este runtime sus nombres son `mcp__context7__resolve_library_id` y `mcp__context7__query_docs`; los nombres del protocolo se documentan en [MCP Clients](https://context7.com/docs/resources/all-clients#mcp-tools).
4. Confirmar que no hay error y que aparecen fuentes oficiales de la versión pedida. Conservar argumentos y respuesta sin credenciales. Si falla, registrar el mensaje y corregir conexión/autenticación; no presentar una búsqueda web como ejecución MCP.

**Resultado comprobado:** la configuración de usuario tiene una sección Context7 HTTP con el endpoint oficial; no existe `.codex/config.toml` en el proyecto. Se verificó su estructura sin exportar credenciales. Las llamadas reales funcionan; la [evidencia JSON](evidencias/context7-ejecucion.json) registra una resolución de SQLAlchemy y dos consultas con fuentes `docs.sqlalchemy.org/en/20/`. El [diagnóstico de entorno](evidencias/verificacion-entorno.txt) registra Node 24.19.0, npm 11.17.0 y ausencia de Codex CLI en PATH.

No se reinstaló ni cambió Context7 durante esta documentación. El ejemplo por variable de entorno es una configuración recomendada para reproducir, **no una afirmación sobre cómo guarda credenciales la configuración existente**. Una reproducción completa en un equipo limpio y su captura siguen pendientes. Context7 aporta documentación técnica: no evalúa RN, no ejecuta reservas ni demuestra ausencia de carreras en PostgreSQL.
