# Verificación local para la defensa del TPI

Preparación del 8 de noviembre de 2026. Las cifras son el resultado de esta ejecución y no reemplazan ejecutar las pruebas en cada entorno.

El equipo confirmó el 9 de noviembre que la defensa será local, sin publicación por ahora (DD-37). Usar únicamente datos ficticios y Mailpit; la configuración de proveedores y la revisión de privacidad para uso real quedan para una eventual publicación.

La auditoría del 9 de noviembre registra una ejecución posterior sobre el commit `5ab5076`: 513 pruebas de backend de unidad y API, 1.315 de integración y 248 de frontend aprobadas. Esas cifras corresponden a aquella ejecución, no a los cambios posteriores.

## Pruebas

- Backend de unidad y API: 507 aprobadas en la auditoría previa.
- Backend de integración: 1.315 aprobadas, sin fallos, con PostgreSQL 17 y Mailpit descartables, después de corregir la sincronización de dos pruebas de C-08. Cada ejecución crea y elimina su propia base.
- Frontend: 247 aprobadas en la auditoría previa; typecheck y compilación aprobados. Las pruebas de componentes pueden usar respuestas simuladas.
- Especificaciones principales: `openspec validate --specs --strict`, 41 válidas.

## Recorrido real con datos sintéticos

Con API FastAPI, frontend compilado, PostgreSQL 17 y Mailpit, se inició sesión como administrador y desde la interfaz se creó un box, se vinculó un profesional y se definió un bloque semanal. Se creó una ficha sintética; la consulta de disponibilidad devolvió 31 opciones. Se reservó un horario (`POST /api/v1/turnos`, 201) y se observó la reserva como pendiente en la agenda y en su detalle.

La reserva generó `resumen_reserva`, `solicitud_confirmacion` y `recordatorio` programados. Se ejecutó el barrido local con su secreto sintético: una notificación reclamada y enviada, sin fallos; Mailpit recibió el resumen de la reserva para el paciente ficticio. Solicitud y recordatorio quedaron programados para sus ventanas futuras: este recorrido no afirma que se hayan enviado. Swagger respondió 200 en `/docs`.

Para repetir la demostración, seguir la sección de desarrollo local del README, iniciar Mailpit con el perfil `dev`, configurar el barrido local conforme a las variables documentadas, generar credenciales de prueba y usar datos ficticios. El correo queda en Mailpit. Configurar profesional, box y horario futuros, crear una ficha, reservar desde la agenda, consultar el turno y comprobar el resumen en Mailpit. El borrador del aviso de privacidad y los datos de consultorio deben revisarse antes de cualquier uso real.

## Reproducción aislada del arranque

El 9 de noviembre se repitió una verificación equivalente en una copia temporal aislada, con la versión actual de las correcciones y secretos ficticios: se construyeron las imágenes, migración y semilla finalizaron, API, frontend y Mailpit respondieron, y se verificaron el usuario no privilegiado de la API, salud, `/`, `/reservar` y los 404 de API y de recursos. Se eliminaron los contenedores y el volumen del proyecto temporal. La comprobación se ejecutó mediante PowerShell con Docker Compose; **no se ejecutó directamente `scripts/smoke_compose.sh`** en esta máquina Windows.

Se extrajeron los archivos versionados en una carpeta temporal, con las correcciones de esta preparación copiadas encima; el extractor Windows no recreó los enlaces simbólicos de compatibilidad de `.claude/skills`. Las skills canónicas `.agents/skills` permanecieron disponibles. El script de secretos se ejecutó en un contenedor Python Linux con la copia montada; Compose usó un nombre de proyecto, puertos y volumen exclusivos. Las imágenes se construyeron, migración y semilla terminaron correctamente, API y frontend quedaron saludables y respondieron HTTP 200 el frontend, `/api/v1/health`, `/docs` y Mailpit. No se probó el script de secretos directamente en WSL; se usó el contenedor Linux como equivalente para ese paso.

## Skill y MCP

La secuencia reproducible y los enlaces a la evidencia de C-07 están en [`skills-mcp/demostracion-tpi.md`](skills-mcp/demostracion-tpi.md). Para la grabación todavía hay que mostrar una invocación visible de la skill y una consulta visible de Context7; las capturas anteriores no sustituyen esa demostración.
