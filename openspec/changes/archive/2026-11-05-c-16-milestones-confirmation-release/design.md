# Design

## Context

Motivación y alcance: [proposal.md](proposal.md). Estado consultado por CLI el 2026-11-05: C-16 no existía; C-09 y C-15 están archivados. **Approval: approved (2026-11-05, by user)**: respuesta «si» a revisión de diseño y autorización de apply con TDD estricto; incluye ventanas, tokens sin cuenta y auditoría del enlace. Governance: **ALTO** (CHANGES.md C-16). Las decisiones propuestas abajo describen el diseño aprobado, sin constituir evidencia de implementación.

Inspección realizada:

| Pieza existente | Hallazgo que condiciona el diseño |
|---|---|
| `backend/app/application/ports/hitos.py` y `use_cases/gestionar_turnos.py` | `PlanificadorDeHitos.planificar` recibe la misma unidad de trabajo; crear y reprogramar lo invocan, pero la composición usa `PlanificadorSinEfectos`. RN-29 y reinicio de ciclo/marca ya existen. |
| `application/use_cases/ciclo_turnos.py` | Confirmar/cancelar/liberar usan autorización central, actualización optimista e historial; solo cancelar programa hoy avisos del personal. |
| `infrastructure/db/avisos_turno.py` y `unidad_de_trabajo.py` | Avisos de personal con snapshot mínimo, `ON CONFLICT` por turno/tipo/canal/ciclo y sin commit/SMTP propio. |
| `application/services/notificaciones.py` | C-15 ya reclama con SKIP LOCKED, valida estado/ciclo/inicio, respeta cupos y cerca resultados por reclamación. Envía `mensaje` persistido; todavía no compone hitos ni registra fechas operativas del turno. |
| `application/use_cases/ejecutar_barrido.py` | Limpieza y cuatro grupos de hasta 100 correos; cinco conteos de resultados y UUID de ejecución. No decide liberaciones. |
| `api/v1/routers/agenda_turnos.py` y `consultar_turnos.py` | Listado de personal y paciente sin filtro sin_confirmar; respuestas ya tienen la marca. |
| `infrastructure/db/models.py`, migraciones 0002/0008/0009 | `token_usuario.ciclo` ya existe desde 0002 y la FK del turno desde 0008. `usuario_id` sigue NOT NULL. 0009 ya tiene deduplicación de notificaciones por ciclo. No repetir esas columnas. |

Fuentes: CHANGES.md §C-16; KB `05` §Confirmación/recordatorio/liberación RN-25–32/RN-60 y RN-59; `04` §turno/turno_historial/token_usuario/notificacion; `06` US-014/016/025/030–032; `07` flujos 3–6; `09` DD-17/18/29/31/32 y SU-46; `10` Q-07/Q-25/Q-27; `11` permisos de turnos. Los deltas conservan los escenarios anteriores de los requisitos modificados.

Registro local consultado: `.atl/skill-registry.md`. El refresco no pudo ejecutarse: `python`, `python3` y `py` no están en PATH y `backend/.venv/Scripts/python.exe` apunta a Python313 con acceso denegado. No se sustituyeron skills por instalaciones globales. Skills completas leídas para esta planificación: `.agents/skills/openspec-propose/SKILL.md` y `.agents/skills/alembic/SKILL.md`; las excepciones de AGENTS.md mandan: PostgreSQL real, Alembic asíncrono existente, un head y rebase, sin SQLite ni merge.

## Goals / Non-Goals

**Goals:** mantener reserva, historial, programación y omisión atómicos; separar decisiones transaccionales de SMTP; proteger ciclo y marca frente a concurrencia; completar el comportamiento por defecto 48/24/12 con parámetros del consultorio y reloj inyectado.

**Non-Goals:** preparar/envíar WhatsApp (C-17), pantallas o ruta frontend de enlace (C-14), alterar permisos de acciones de cuenta, introducir un worker/Redis, corregir funcionalidades ajenas o modificar la KB. Las omisiones son multicanal desde C-16; C-17 probará sus propias filas `preparada`.

## Decisions

### 1. Planificador transaccional y reglas temporales puras

Implementar `ProgramadorHitos` detrás del puerto existente, con puertos de repositorio ampliados en la misma UoW. Componerlo explícitamente en las rutas reales de crear/reprogramar y en cancelación/liberación; mantener posibilidad de inyectar dobles del puerto para pruebas de aplicación. No enviar correo ni confirmar transacciones desde el planificador. Alternativa descartada: programar después del commit, porque deja reservas sin comunicaciones ante una caída.

Calcular desde `inicio` y los parámetros del consultorio, nunca desde la hora de ejecución ni con `now()` SQL:

| Operación / estado | Solicitud | Recordatorio | Decisión T-liberación |
|---|---|---|---|
| Reserva/reprogramación pendiente con anticipación >= horas_confirmacion | Programar T-confirmación; la igualdad es elegible ahora | Programar T-recordatorio | Derivada de la fila turno |
| Confirmado por RN-29 o por personal | No programar | Solo si el hito es estrictamente futuro al planificar | No candidato |
| Reprogramar | Omitir solicitud/recordatorio programada/preparada del ciclo anterior, cualquier canal; programar nuevo ciclo | Igual | C-07 ya incrementa ciclo y limpia marca/fechas |
| Cancelar/liberar | Omitir solicitud/recordatorio programada/preparada del ciclo vigente, cualquier canal | Igual | No candidato por estado |

No crear una notificación para la decisión T-12: la fila turno y sus parámetros son durables. Usar la UNIQUE existente y `ON CONFLICT DO NOTHING` para planificación repetida. Conservar avisos de hechos consumados y reclamaciones activas: una `enviando` puede terminar; si vence se omite al recuperar por vigencia.

### 2. Ventanas de envío y discrepancia documental a revisar

**Decisión propuesta:** solicitud válida desde T-confirmación hasta antes de T-recordatorio; recordatorio desde T-recordatorio hasta antes de T-liberación. Al alcanzar el hito siguiente se omiten las programadas o reclamaciones vencidas, antes de considerar intentos/cupos. Un envío ya reclamado dentro de su ventana puede terminar después; su resultado conserva el fencing y RN-60 evalúa lo que esté efectivamente registrado al decidir.

CHANGES.md C-16 §Riesgos exige omitir hitos si el barrido llega más allá del siguiente. Sin embargo, KB `04` §Vigencia por tipo y la spec actual `notification-dispatch` definen vigencia hasta inicio, sin ese límite intermedio. Este diseño hace explícita la restricción del roadmap y los bordes inclusivos/exclusivos; **su aprobación debe confirmar esta interpretación**. No se cambia la KB ni se presenta como DD nueva. Alternativa: enviar cualquier hito hasta inicio, que puede generar una solicitud tardía en la misma ejecución que libera; no satisface el riesgo indicado por el roadmap.

En `DespacharNotificacion`, construir el recordatorio al reclamar con estado, configuración, marca y solicitud email enviada del ciclo actual. No fijar anticipadamente una advertencia al reservar: puede cambiar la elegibilidad antes del envío. Confirmados no reciben pedido de confirmar; pendientes solo reciben advertencia si RN-60 permite realmente liberar. Cuerpo y asunto excluyen DNI, obra social, notas y motivo interno (RN-54).

### 3. Token por turno/ciclo y fichas sin cuenta

**Decisión de esquema propuesta, sujeta a aprobación:** permitir `token_usuario.usuario_id` nulo exclusivamente para `confirmar_turno`. Exigir por CHECK que confirmar_turno tenga turno no nulo y ciclo positivo; los otros dos tipos conservan usuario obligatorio. Conservar FK, hash único y la columna ciclo existente. Para una ficha vinculada puede guardarse su usuario; para una sin cuenta, no inventar una cuenta ni usar al empleado creador como paciente.

Discrepancia: KB `04` enumera `usuario_id` sin declarar la excepción y el esquema actual exige NOT NULL, mientras RN-25 y las fichas sin cuenta de RN-47/US-037 requieren solicitar confirmación también a turnos tomados por Recepción. La spec principal no exige usuario no nulo expresamente; el delta `core-data-models` formaliza el nuevo contrato. Alternativa de saltar solicitudes para fichas sin cuenta reduce comportamiento esperado; atribuirlas al empleado falsea identidad.

Emitir token opaco mediante utilidades criptográficas existentes **al reclamar una solicitud que efectivamente puede enviarse**, en la primera transacción corta. Persistir hash, turno, ciclo y vencimiento igual a inicio. El claro solo vive en memoria hasta SMTP y va en `FRONTEND_BASE_URL/confirmar-turno#token=...`; no guardarlo en `notificacion.mensaje`, logs o historial. Evita propagar el patrón de cuerpos persistidos de los correos de cuenta, sin ampliar C-16 a una refactorización de C-05. Cada reintento puede emitir otro token del mismo ciclo; los anteriores siguen válidos hasta consumo, cambio de ciclo/estado o vencimiento. La purga existente elimina expirados. No hace falta un secreto nuevo, TTL configurable ni tabla nueva.

Implementar caso de uso dedicado de confirmación por enlace, sin construir un Principal artificial. Consultar por hash/tipo para resolver el consultorio; bloquear el turno y después el token en orden consistente para enlaces del mismo turno, revalidando token tras el bloqueo. Actualizar pendiente del ciclo leído, consumir token y agregar historial en una transacción. Con cuenta asociada, actor es ese usuario; sin cuenta, actor nulo y detalle mínimo `medio: enlace` y `actor: paciente_sin_cuenta`, sin confundirlo con el barrido de sistema ni inventar identidad. La precisión de auditoría de ese caso queda incluida en la revisión del diseño (KB `04` describe usuario nulo para sistema, sin detallar bearer anónimo).

Contrato: cuerpo solo `{token}`, `extra='forbid'`; éxito 200 con turno_id/estado mínimos; token inexistente/usado/vencido/tipo incorrecto/ciclo anterior devuelve 400 genérico; estado incompatible devuelve 409, y liberado indica reservar de nuevo. La sesión y CONSULTORIO_ACTIVO_ID no participan. Esta autorización bearer solo permite confirmar; ninguna cancelación/reprogramación acepta ese token. Asegurar que la ruta literal no quede capturada por rutas parametrizadas.

### 4. Decisión automática por actualización condicional

Agregar caso de uso de evaluación separado del despacho, invocado por `EjecutarBarrido` antes de tomar la lista de correos. Seleccionar hasta 100 turnos ordenados por inicio/id del consultorio, pendientes, sin marca, con hito alcanzado e inicio estrictamente futuro. No cargar ni reevaluar pendientes ya iniciados. El lote finito y la exclusión de los ya resueltos permiten continuar en barridos posteriores.

Una transacción por turno; releer el reloj justo antes de escribir. En automático verificar `EXISTS` de solicitud email `enviada` del mismo consultorio/turno/ciclo en la condición de liberación. En manual o sin esa prueba, intentar la marca. Ambas escrituras exigen consultorio, id, pendiente, marca nula, ciclo evaluado e inicio > ahora. El `UPDATE` es el reclamo: no se agrega estado intermedio ni candado global.

Solo si devuelve una fila, escribir historial de sistema (`usuario_id` nulo, acción liberar o marcar_sin_confirmar) y, al liberar, omitir hitos y programar aviso email con snapshot en esa misma transacción. Si pierde frente a otra decisión/acción, no hace efectos secundarios. Si falla historial o programación, revierte todo. La marca queda sin reintento automático en ese ciclo aunque cambie después el correo o el modo. La reprogramación es la que reinicia la evaluación (RN-32/RN-60).

No reemplazar el control optimista existente de C-07: confirmación/cancelación/reprogramación que pierde contra la decisión responde su 409 habitual. Una confirmación ganadora impide liberar; si ganó liberar, el enlace responde estado incompatible y ofrece reservar. No imponer una separación mínima entre envío y liberación (RN-60).

### 5. Despacho y avisos de hechos consumados

Extender el registro exitoso condicionado de C-15 para escribir `confirmacion_solicitada_en` o `recordatorio_enviado_en` en la misma transacción del resultado y solo si el turno sigue en el ciclo enviado. Nunca escribir esas fechas cuando se perdió la reclamación ni sobre un ciclo nuevo. RN-60 consulta la notificación enviada, no infiere envío a partir de una fecha aislada.

Extender la programación de avisos para crear resumen_reserva al reservar (incluido personal) y cancelacion_por_paciente solo cuando cancela el titular. Mantener los avisos Staff existentes. Capturar destinatario/datos mínimos del hecho al programar, deduplicar por ciclo y no reconstruir contenido desde estados posteriores. Sin email utilizable no inventar contacto ni impedir la operación: señal técnica sin PII y falta de solicitud enviada impide liberar automáticamente. Los avisos de liberación son siempre vigentes. SMTP sigue entre dos transacciones cortas; fallos no revierten el hecho ya confirmado.

Conservar los cinco campos de `ResumenBarrido` y metadatos de C-15: conteos de correo, no decisiones de turno. El aviso recién creado se puede despachar en la misma ejecución si entra en su lote; de otro modo queda durable para la siguiente. Cupos completos no bloquean decisiones ni omisiones que no envían.

### 6. Lista sin confirmar y compatibilidad

Agregar filtro booleano `sin_confirmar` (false por defecto) a la consulta existente. Cuando es true, la dependencia de autorización y las políticas de aplicación limitan a Recepción/Administrador; el repositorio filtra consultorio + pendiente + marca no nula y conserva orden inicio/id. No filtrar por futuro adicional: un pendiente ya marcado sigue necesitando resolución del personal después de su inicio. Sin filtro se conserva exactamente alcance/DTO del personal y del paciente.

No duplicar acciones de resolución: confirmar/cancelar/liberar/reprogramar usan C-07/C-09. Su resultado sale del filtro por estado o por marca nula. No exponer contacto, DNI, obra social ni cuenta en la lista.

## Risks / Trade-offs

- [Caída entre SMTP y resultado] → conservar entrega al menos una vez y fencing C-15. Un correo puede repetirse y un SMTP tardío puede llegar tras perder vigencia; el token del ciclo anterior nunca confirma el nuevo.
- [Modelos/KB y roadmap discrepan] → revisión humana explícita de decisiones 2 y 3 y actor sin cuenta, sin modificar KB silenciosamente.
- [Un token bearer enviado al contacto de la ficha confirma sin contraseña] → alcance confirmar únicamente y un solo uso; Q-07 es Media y rige RN-30. No resolver el supuesto mediante acceso de cuenta artificial.
- [Cuota, SMTP fallido o disparador tardío] → RN-60 conserva el turno marcado para Recepción. Q-25/Q-27/SU-38 quedan para despliegue C-20; la validación usa bucle local y Mailpit.
- [Historia anterior a C-16 no tiene hitos programados] → no hacer backfill automático ni atribuir envíos históricos. Turnos pendientes existentes se marcan si llegan al hito sin solicitud enviada; reservas/reprogramaciones nuevas usan el planificador. Un backfill sería alcance aparte.
- [Bajar esquema con tokens de confirmación sin cuenta vigentes] → preflight de downgrade rechaza sin mutar datos; esperar vencimiento/purga o gestionar una invalidación explícita revisada antes de volver al NOT NULL anterior.
- [Entorno Python local inaccesible] → ejecutar apply/TDD en el runner Linux disponible y PostgreSQL/Mailpit reales; no se ejecutaron pruebas de producción en esta fase de planificación.

## Migration Plan

1. Tras aprobación, capturar safety net antes de editar código. Verificar head real; autorar revisión `0010` descendiente del head vigente (`0009_notifications_outbox_sweep` observado), sin tocar 0002 ni agregar ciclo duplicado.
2. La revisión relaja solo usuario_id y agrega CHECK por propósito. Preservar filas existentes; detectar y reportar cualquier confirmar_turno histórico incompatible antes del CHECK, sin rellenar actores/ciclos desconocidos. Preparar fixture de migración con tokens de cuenta previos, verificar hash y asociaciones intactos.
3. Aplicar `alembic upgrade head`, probar flujo con/sin cuenta y control de restricciones en PostgreSQL. Probar downgrade/upgrade en esquema compatible y preflight de incompatibles sin cambios parciales. Conservar un head y exclusión anti-solapamiento.
4. Verificar composición real de routers y ambos disparadores, recorrido por Mailpit y suites existentes de C-05/C-07/C-09/C-15. Documentar comandos, conteos, RED/GREEN/triangulación y trazabilidad escenario→test en evidencia del change.
5. Rollback de aplicación conserva comunicaciones durables. Downgrade de esquema solo después del preflight compatible anterior; no borrar tokens, turnos o historial para forzarlo. No archivo, sync de specs principales, commit o push en esta fase.

## UI Mockups

- Decision: no (no UI), 2026-11-05.
- Alcance backend/API y texto de correo, sin pantalla, componente, estilo ni interacción web implementada. El enlace se valida por API/Mailpit; la pantalla de consumo corresponde a C-14.
- Approval: no aplica a mockups. Aprobación del diseño/backend: **approved (2026-11-05, by user)**.
