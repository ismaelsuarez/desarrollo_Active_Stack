# Design

## Context

Motivación y capacidades: [proposal.md](proposal.md). Dependencias C-05 y C-07 archivadas; C-09 publicado en `9337f8c`. La inspección de código confirmó:

| Base observada | Consecuencia para C-15 |
|---|---|
| `application/services/notificaciones.py:DespacharNotificacion` ya reclama con SKIP LOCKED, TTL, cupos y resultado condicionado, con SMTP entre dos sesiones | Ampliar este servicio; no crear un segundo despachador |
| Su resultado actual es bool y mezcla omisión, cupo, error y pérdida de reclamación | Agregar resultado detallado interno conservando la interfaz bool de sus consumidores actuales |
| `infrastructure/db/account_models.py:NotificacionModel` no tiene ciclo ni clave de deduplicación | Migración incremental sobre `0008_turnos_core` |
| `GestionTurnos.reprogramar` llama `PlanificadorDeHitos`, que no recibe actor; `CicloTurnos` no lo llama al cancelar | Integrar un puerto transaccional de avisos de cambios por personal, sin sobrecargar el contrato de hitos de C-16 |
| `main.py` tiene lifespan vacío y no hay routers de barrido/operación | Agregar composición y adaptadores sin abrir sesiones compartidas |
| Existen purgas de intentos al escribir y SMTP con timeout 30 s, TTL 120 s, máximo 3, cupos 500/150 y alerta .8 | Reutilizar reglas, settings y pruebas actuales |

Fuentes de dominio: KB 04 §notificacion (tabla de vigencia y transiciones), KB 05 RN-31/RN-54/RN-61, KB 06 US-034/US-035, KB 08 trabajos/seguridad, KB 09 DD-13/DD-17/DD-29/DD-31, KB 11 `notificacion.gestionar` y KB 12 operación local/despliegue. No hay pregunta Alta que bloquee el alcance local; Q-23/Q-24/Q-25/Q-27 continúan abiertas para producción.

## Goals / Non-Goals

**Goals:** recuperar trabajo durable con ejecuciones acotadas, mantener garantías C-05, avisar cambios del personal atómicamente y hacer observable la operación entre procesos.

**Non-Goals:** hitos 48/24/12 h, confirmación por enlace, liberación automática, resumen de reserva y cancelación del paciente (C-16); WhatsApp (C-17), UI (C-18), elección de host/proveedor/disparador real (C-20). No nuevo worker, Redis, broker, APScheduler ni servicio externo obligatorio.

## Decisions

### 1. Un despacho durable y resultados propios

Extender `DespacharNotificacion` con una operación que devuelva un DTO de resultado (`reclamada`, resultado final y motivo técnico estable). Mantener `ejecutar(...) -> bool` como fachada compatible para BackgroundTasks y pruebas existentes. Barrido y envío inmediato deben compartir la misma implementación de reclamación, vigencia, cupos y cierre.

El resumen agrega solo transiciones confirmadas por esa ejecución: `reclamadas` cuenta tomas propias, `enviadas` éxitos propios y `reintentadas` fallos propios que vuelven a programada; `omitidas` y `fallidas` incluyen cierres propios sin envío. Una reclamación perdida puede contar como reclamada pero no como enviada/reintentada/fallida propia. Registrar pérdida sin PII. No deducir resultados consultando la fila después: otro proceso podría haberla modificado.

Se descarta reemplazar el bool por un enum directamente: rompería consumidores C-05. Un error SMTP sigue siendo resultado por fila; errores de infraestructura que impiden continuar finalizan el barrido como error, preservando trabajo durable.

### 2. Reclamar, validar y terminar sin transacción SMTP

Conservar `SELECT ... FOR UPDATE SKIP LOCKED` por fila, commit de `enviando/reclamada_en/intentos`, transporte fuera de transacción y resultado por `WHERE estado='enviando' AND reclamada_en=:propia`. Una sesión por transacción/tarea; nunca mantener la sesión del router o UoW durante SMTP.

Aplicar una política de vigencia por tipo tanto a programadas como a vencidas: solicitud solo pendiente, recordatorio pendiente/confirmado, ambos con turno del consultorio, ciclo igual e `inicio > ahora`; `vinculacion_rechazada` conserva su regla C-05. Avisos de hechos consumados y otros correos de cuenta no dependen de turno activo. Un ciclo desconocido no satisface la igualdad para solicitud/recordatorio.

Orden: vigencia → máximo de intentos → cupos → nueva reclamación. TTL vencido es estrictamente `reclamada_en < ahora-TTL`, preservando los bordes 119/120/121 existentes. Toda salida de enviando limpia su marca, incluso cierres sin envío. Fencing también en recuperaciones terminales.

Preservar el conteo y la alerta C-05: día calendario del consultorio, enviadas del día y enviando vigentes; cupo total 500 y cuenta 150. No agregar serialización global: KB 04 permite un pequeño exceso por reclamaciones simultáneas de filas diferentes. El contrato es al menos una vez; caída o envío más lento que TTL pueden repetir correo. El timeout SMTP permanece menor al TTL.

### 3. Ejecución finita con selección justa

`EjecutarBarrido` recibe consultorio del servidor, fábrica de sesiones, reloj, despacho y puertos de limpieza/estado. Selecciona IDs candidatos, cierra la sesión de lectura y procesa cada ID una sola vez. La reclamación del despachador sigue siendo la autoridad; la selección inicial no promete propiedad.

Usar cuatro grupos acotados: programadas/vencidas × cuenta/turno, hasta 100 IDs por grupo, ordenados por vencimiento e ID. Unir sin repetidos (máximo 400 por ejecución). Así una cuenta sin cupo o una clase de fila no desplaza todo el trabajo de turnos o recuperación; no hacer un bucle que vuelva a recoger inmediatamente un fallo reprogramado. El resto queda para la próxima ejecución. Cada envío es secuencial dentro de ese barrido; varios barridos pueden avanzar en paralelo sin mutex global. No bloquear filas durante toda la lectura del lote ni compartir AsyncSession entre tareas.

Ejecutar limpieza una vez por barrido incluso si no hay correos. Ventanas de lotes y cuotas son independientes; no prometer drenar un atraso ilimitado en un único request. Los límites internos son constantes documentadas y comprobables, no nuevas reglas de producto.

### 4. Dos adaptadores sobre el mismo caso de uso

Introducir el puerto `Planificador` para disparar una ejecución sin confundirlo con `PlanificadorDeHitos`. El adaptador HTTP y el adaptador del bucle reciben la misma composición de `EjecutarBarrido`.

- `POST /internal/barrido`: router separado, `include_in_schema=False`, sin cuerpo ni query admitidos; dependencia de autenticación compara bytes de `X-Sweep-Secret` con `secrets.compare_digest`. Si falta, no coincide o Settings no configura secreto, 403 antes de abrir trabajo. Consultorio desde `CONSULTORIO_ACTIVO_ID`. Respuesta 200 con ID y los cinco conteos; error de infraestructura devuelve 503 genérico, sin secretos ni SQL. No usar JWT como sustituto del secreto ni aceptarlo en URL.
- Settings: `SWEEP_SHARED_SECRET` opcional y sensible, sin default real; vacío deshabilita solo el disparador HTTP, no el arranque/local. `SWEEP_IN_PROCESS_ENABLED=false` por defecto, `SWEEPER_INTERVAL_SECONDS=300`, entero positivo. Mantener 3 intentos/120 s TTL/30 s SMTP ya existentes. `.env.example` solo marcadores y Compose permite habilitar el bucle local sin imponerlo en producción.
- Lifespan: con flag habilitado crear una tarea propia, ejecutar al iniciar y esperar intervalo después de cada intento. Capturar errores recuperables con logs seguros para continuar; no capturar/silenciar cancelación. En finally cancelar y esperar la tarea antes de liberar recursos. Cancelación deja las reclamaciones interrumpidas recuperables por TTL. No crear tarea cuando está deshabilitado; no usar `BackgroundTasks` para mantener el bucle permanente.

La opción de un worker separado viola DD-13. Un candado de proceso/global impediría concurrencia válida y no resolvería la exclusividad entre instancias.

### 5. Limpieza de credenciales e intentos

Reutilizar lógica de `PurgarIntentosRegistro` y `PurgarIntentosIngreso`, preservando sus usos al escribir. Agregar purga acotada por consultorio de token_usuario y refresh_token con `expira_en <= ahora`; para intentos usar `< ahora-24h` y conservar igualdad. Cada limpieza se confirma en su propia transacción corta, sin commits escondidos dentro de una UoW de turno. No borrar cuentas, refresh vigentes, turnos, historial ni notificaciones. Probar cascadas/FKs y aislamiento con datos sintéticos en PostgreSQL; esta purga no amplía el circuito de derechos de datos C-21.

### 6. Avisos staff separados de hitos

Agregar puerto `ProgramadorAvisosDeTurno` y repositorio de notificaciones a la UoW. Recibe explícitamente Principal/acción y datos mínimos del hecho; lo invocan reprogramación en `GestionTurnos` y cancelación en `CicloTurnos`, antes del commit. No inferir autor por el texto de la acción compartida con pacientes. El planificador de hitos existente sigue independiente para C-16.

El adaptador usa la sesión de la UoW, nunca hace commit ni SMTP. Compone cuerpo con nombre, horario del hecho en zona local, profesional, consultorio y acción; lo captura en `mensaje` para no reconstruir desde un turno cambiado posteriormente. Destinatario: email de la ficha del paciente del consultorio, sin exigir usuario vinculado ni correo de cuenta verificado para un aviso del personal. Sin email utilizable, no crear fila ni fallar la operación; registrar solo evento técnico con IDs autorizados y sin contacto.

Programar `cancelacion_por_personal` con ciclo vigente o `reprogramacion_por_personal` con nuevo ciclo, `programada_para=ahora`, estado programada. El barrido realiza la entrega durable posterior. Inserción `ON CONFLICT` por la clave exacta como no-op idempotente, sin ocultar otros errores de integridad. Fallo real de inserción revierte turno/historial/aviso; fallo SMTP posterior no revierte el hecho. No programar correos de paciente o hitos de C-16 anticipadamente.

### 7. Operación durable y autorización central

`GET /api/v1/notificaciones`: query `estado` opcional de enum, `limit` 1..100 default 50, `offset` no negativo; orden estable por ID descendente. `GET /api/v1/notificaciones/indicadores`: cantidades, antigüedades en segundos no negativos, cuenta diaria y cupos/alerta, último barrido. Ambos usan autenticación normal, `requiere_rol(Recepcion, Administrador)` y acción central `NOTIFICACION_GESTIONAR`; consultorio desde Principal. Ausencia de sesión 401, otros roles 403, entrada inválida 422.

Proyección: ID, turno_id, tipo, canal, estado, intentos, programada_para/reclamada_en/enviada_en; sin destinatario, cuerpo, enlace/token, ultimo_error original ni datos clínicos. No hay acciones de reenvío manual ni UI en C-15. Antigüedad de programada desde programada_para y enviando desde reclamada_en; sin filas devuelve null. Cantidad enviando incluye vigentes y vencidas, mientras el uso de cuota excluye vencidas.

Persistir una fila `barrido_estado` por consultorio (FK/PK), con UUID de ejecución, iniciado_en, finalizado_en opcional, estado `en_curso/exitoso/error` y cinco conteos. Al iniciar, un upsert breve solo reemplaza una marca no posterior; al terminar actualizar por el UUID propio. Si una ejecución vieja perdió esa marca, descarta solo la actualización de observabilidad. Esto conserva el último barrido iniciado entre procesos, sin retener un historial ilimitado ni serializar el procesamiento. Una caída puede dejar en_curso con antigüedad visible. Errores solo como estado técnico, nunca texto original. Esta fila es metadato operativo, no auditoría de accesos C-21.

## Risks / Trade-offs

- [Correo duplicado tras caída o envío lento] → Contrato al menos una vez, TTL mayor al timeout y resultado condicionado; no afirmar exactly-once.
- [Cupo superado levemente por concurrencia] → Comportamiento aceptado en KB 04/DD-17; mantener alerta .8 y conteo antes de reclamar, sin candado global.
- [Lote acotado demora un atraso grande] → Cuatro grupos con avance independiente; métricas muestran antigüedad y próximos barridos continúan.
- [Metadata del último barrido interrumpido] → Mantener estado/antigüedad observable; el barrido siguiente reemplaza la marca, sin bloquear trabajo.
- [Publicación sin SMTP/host/disparador] → Q-23/Q-24/Q-25/Q-27 continúan abiertas; demostrar con Mailpit local, resolver antes de correo real/C-20.
- [Purgar una credencial válida o mandar datos sensibles] → Governance requiere revisión explícita del diseño antes de apply; TDD de bordes/rollback, pruebas de contenido recibido y logs sin PII.

## Migration Plan

1. Crear revisión `0009_notifications_outbox_sweep` con down_revision `0008_turnos_core` (rebasar si cambia el único head antes de apply). Añadir `notificacion.ciclo INTEGER NULL` y `UNIQUE(turno_id,tipo,canal,ciclo)`, manteniendo índices y CHECK de reclamación existentes.
2. No inferir ciclos históricos: correos de cuenta permanecen con NULL. Las filas previas de turno, si existen, conservan NULL y todos sus datos; una solicitud/recordatorio sin ciclo conocido no pasa la validación de vigencia. C-05/C-07/C-09 no programaban filas de turno en producción. Las nuevas escrituras de turno sí exigen ciclo explícito. No borrar ni renumerar filas legadas para satisfacer UNIQUE.
3. Crear `barrido_estado` con PK/FK consultorio e invariantes de estado/fechas y conteos no negativos. No cambiar `turno_historial`.
4. Verificar upgrade desde base vacía y desde 0008 con cuenta histórica y filas de turno sintéticas: cuenta con múltiples NULL permitida, filas nuevas iguales rechazadas/deduplicadas y ciclo/canal distinto permitido. Revisar SQL y cabeza única. No `create_all`, merge de heads ni SQLite.
5. Rollback de app: desactivar bucle/disparador y volver a la versión anterior conservando tablas/columna aditivas. Downgrade de esquema solo en BD desechable o tras revisión/backup: elimina los objetos nuevos y pierde sus metadatos/ciclo; no prometer rollback de datos sin pérdida. No ejecutar rollback sobre un entorno real como parte de apply.

## Validation

TDD estricto por tarea con baseline previo: reutilizar `tests/integration/test_notificaciones.py` y suites C-03/C-05/C-07/C-08/C-09 afectadas. Reloj inyectado, PostgreSQL real con sesiones/conexiones diferentes y barreras/eventos observables; SMTP Mailpit para recorridos, transporte controlado para fallo/lentitud. Cubrir cada escenario de los tres deltas y al menos dos casos por comportamiento. Ejecutar full backend al integrar y documentar RED auténticos; lo que ya existe se caracteriza sin inventar un RED histórico.

Referencias actuales consultadas mediante Context7 (2026-11-05): [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/), [excluir OpenAPI](https://fastapi.tiangolo.com/advanced/path-operation-advanced-configuration/), [sesión por tarea de SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#session-faq-threadsafe). Las decisiones de dominio proceden de la KB; la skill sql-job-queue solo aporta su referencia de entrega al menos una vez.

## UI Mockups

- Decision: no (no UI), 2026-11-05.
- C-15 expone APIs y operación backend; las pantallas pertenecen a C-18. No revisa ni cambia la política visual del proyecto.

## Revisión antes de apply

Approval: approved (2026-11-05, by user). Revisar especialmente el secreto del disparador, la purga por vencimiento/retención, los avisos sin contacto, la metadata durable y el contrato al menos una vez. La propuesta no autoriza escribir producción: requiere una nueva instrucción de apply después de presentar estos artefactos.
