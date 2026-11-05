# C-15 — evidencia de apply

Approval: approved (2026-11-05, by user). Sin archivo, sync principal, commit ni push.

## Entorno y safety net

PostgreSQL 17, Mailpit y Python 3.13 temporales (`c15-pg`, `c15-mail`, `c15-runner`, red `c15-testnet`). Dependencias `uv sync --frozen`, entorno `/tmp/c15-venv`. Cada invocación de integración crea una BD UUID propia; no se usan dobles de PostgreSQL.

Baseline antes de producción: **422 passed in 83.35s**, suites `test_notificaciones`, `test_c07_booking`, `test_c07_reschedule`, `test_c07_lifecycle`, `test_c08_records`, `test_c09_patient_booking`, `test_c09_patient_actions`, `test_c09_patient_reschedule`, `test_auth_endpoints`, `test_cuenta_api`, `test_cuentas`. Configuración adicional: 26 existentes verdes. Un primer comando indicó nombre de archivo inexistente y no ejecutó pruebas; se corrigió antes del baseline. No fue fallo de comportamiento preexistente.

## Ciclos ejecutados (registro incremental)

- Resultado detallado: RED AttributeError 1 → GREEN 1. Triangulación éxito, error reintentable, agotado, bool/consultorio. Vigencia: RED solicitud de turno confirmado enviada en vez de omitida → GREEN despacho+regresión **60 passed in 13.50s**.
- Barrido: RED módulo inexistente 1 → GREEN 1; RED grupos/marca vencida 2 → GREEN 3; RED marca durable/fin viejo 2 → GREEN 5.
- Limpieza: RED módulo inexistente 2 → GREEN; limpieza+regresión cuenta/auth **13 passed in 8.74s**. Integración vacío RED no purga → GREEN; conjunto despacho/barrido/cleanup+legacy **68 passed in 11.50s**.
- Datos: RED ciclo constructor 1 → GREEN 1; RED unique 1 → GREEN 2; RED import estado 1 → GREEN 6; RED invariantes 10 → GREEN 16.
- Triggers: RED settings 6 → GREEN 8 (+26 legacy); RED HTTP404/loop timeout → GREEN 20. RED bandeja404 → GREEN 7; RED métricas404 → GREEN 26. Composición real y shutdown PG/TTL caracterizados sin inventar RED histórico. Entrega del frente **75 passed in 10.84s**.
- Avisos staff: RED reprogramación 1 → GREEN 1; RED cancelación 2 → GREEN 3; triangulación **16 passed in 7.40s** (rollback insert/historial/commit, contacto faltante, exclusión paciente, snapshots y privacidad).

## Operación y límites

Cada ejecución considera cuatro grupos de hasta 100 IDs (programadas/enviando vencidas × cuenta/turno), ordenados por vencimiento e ID. Cada ID se trata una vez, máximo 400 por ejecución; los fallos reprogramados esperan al siguiente barrido. Un atraso grande necesita varias ejecuciones y no hay promesa de drenaje ilimitado. El cupo de cuenta no desplaza todos los avisos de turnos. La cuota concurrente conserva el pequeño exceso aceptado por KB 04; no hay mutex global ni Redis obligatorio.

Entrega al menos una vez: una caída tras SMTP o transporte más lento que TTL puede repetir el correo. Las escrituras tardías se descartan por reclamación. Purga de tokens `expira_en <= ahora`; intentos `< ahora-24h` conservando igualdad, con scope por consultorio y transacciones cortas. El refresh vigente no se elimina al quitar una referencia a un refresh expirado del mismo consultorio.

La bandeja contiene sólo metadatos; no destinatario, mensaje ni error original. `barrido_estado` representa la última ejecución iniciada (no historial ilimitado), con UUID para evitar que una terminación vieja sobrescriba una posterior. Una cancelación deja el estado en curso y el correo recuperable por TTL.

## Migración y recorridos

`0009_notifications_outbox_sweep` sobre `0008_turnos_core`, aditiva, conserva todos los índices y CHECK anteriores. Desde 0008 se verificaron cuenta y turno históricos sin inferir ciclo y sin pérdida de filas. Upgrade limpio, downgrade a 0008 y reupgrade se probaron sólo en una BD desechable. Rollback de aplicación puede conservar los objetos; el downgrade de esquema elimina ciclo y metadatos nuevos y no es una restauración sin pérdida.

Datos/avisos/recorrido y regresión C07/C09: **187 passed in 37.30s**; esquema final **19 passed in 11.95s**. Dos recorridos Mailpit reales: staff → error SMTP puerto 1 → programada/intento 1 → SMTP puerto 1025 → dos correos enviados (staff y cuenta C05) → repetición cero → bandeja e indicadores; ambos tipos de cambio, sin datos clínicos ni tipos C16 (**2 passed in 5.16s**).

Concurrencia final: **6 passed in 4.26s**. Tres PID de PostgreSQL distintos, dos barridos más inmediato, bloqueo NOWAIT tomado durante SMTP, DTO de resultado tardío exitoso/fallido descartado, interrupción durable y recuperación, resumen que no atribuye resultado ajeno y lotes 100/3/0 con cupo de cuenta agotado. Se corrigió la barrera de un test: el despacho inmediato puede perder legítimamente su única fila, por lo que se exigen tres conexiones reclamantes y al menos dos transportes simultáneos; no se cambió producción para ese ajuste.

Cierre de lifespan: RED engine propio no dispuesto → GREEN **17 passed in 8.48s**; cancelar/esperar antes de dispose y conservar fábricas externas. La regresión conjunta inicial C15 capturó ese test mientras estaba en RED: 143 verdes/1 rojo. Se volvió a verificar después del cambio, sin ocultar el ciclo.

## TDD Cycle Evidence

Rutas abreviadas: los tests `test_c15_*.py` están en `backend/tests/integration/`, salvo settings/lifespan en `backend/tests/unit/`. Las verificaciones de comportamiento preexistente y los recorridos de composición se consignan como caracterización; no se inventa un RED histórico. Safety net **422** salvo configuración, con **26** pruebas adicionales existentes. GREEN/refactor incluye las suites conjuntas registradas arriba y el cierre integral.

| Tarea | Test File | Layer | Safety Net | RED | GREEN / TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| 1.1 | suites afectadas | Integración | 422 | N/A preparación | Aprobación registrada y baseline ejecutado | N/A |
| 1.2 | test_c15_schema.py / staff_notices | PG | 422 | ciclo TypeError; unique ausente | NULL, variantes, dos PID | Verde |
| 1.3 | test_c15_schema.py | PG | 422 | import y 10 invariantes | UUID, estados, fechas, conteos, dos consultorios | Verde |
| 1.4 | test_c15_schema.py | Alembic/PG | 422 | migración creada por RED anteriores | limpio/legado/downgrade/reupgrade, índices/CHECK | Verde |
| 2.1 | test_c15_dispatch.py / concurrency | PG | 422 | AttributeError | resultados, cuota, omisión, retry, agotado, pérdida | Verde |
| 2.2 | test_c15_dispatch.py | PG | 422 | solicitud confirmada enviada | 22 combinaciones + NULL/ajeno, cuenta previa | Verde |
| 2.3 | test_c15_dispatch.py | PG | 422 | caracterización | cinco tipos × programada/vencida | Verde |
| 2.4 | test_c15_dispatch.py / test_notificaciones.py | PG | 422 | vigencia nueva RED anterior | vigencia/max/cupo, TTL119/120/121, medianoche | Verde |
| 2.5 | test_c15_concurrency.py / test_notificaciones.py | PG concurrente | 422 | caracterización | PID distintos, SMTP sin TX, caída/late éxito/error | Verde |
| 3.1 | test_c15_sweep.py | PG | 422 | método inexistente | cuatro grupos, 100/grupo, orden/futuros | Verde |
| 3.2 | test_c15_sweep.py / concurrency | PG | 422 | import y conteo fallida incorrecto | lote mixto, vacío, retry único, resultado ajeno | Verde |
| 3.3 | test_c15_sweep.py / concurrency | PG | 422 | marca None, dos casos | éxito/error/cancelación y fin fuera de orden | Verde |
| 3.4 | test_c15_concurrency.py | PG concurrente | 422 | caracterización | dos barridos + inmediato, tres PID, sin Redis | Verde |
| 3.5 | test_c15_sweep.py / concurrency | PG | 422 | selección limitada RED anterior | atraso 3h, lotes100/3/0, cuenta no desplaza turno | Verde |
| 4.1 | unit/test_c15_settings.py | Unidad | 26 | seis campos/flags | defaults, intervalos, secreto, timeout | 34 combinadas |
| 4.2 | test_c15_triggers.py | API/PG | 422 | 404 | ausente/incorrecto/vacío, query/body | Verde |
| 4.3 | test_c15_triggers.py | API/PG | 422 | 404 | 200, 503 seguro, OpenAPI oculto | Verde |
| 4.4 | unit/test_c15_lifespan.py / triggers | Unidad/PG | 422 | timeout | retry tras error, mismo objeto real | Verde |
| 4.5 | lifespan / test_c15_shutdown.py | Unidad/PG | 422 | engine no dispuesto | cancelar/await/dispose propio, externo, TTL119/121 | 17 verdes |
| 5.1 | test_c15_cleanup.py | PG | 422 | módulo ausente | menor/igual/mayor, ajenos, FK, repetición | Verde |
| 5.2 | test_c15_cleanup.py / limites/auth | PG | 422 | módulo ausente | 24h menos/igual/más, purga al escribir | 13 combinadas |
| 5.3 | test_c15_cleanup.py | PG | 422 | vacío no purga | vacío/error, trigger real rollback, dominio conservado | 4 finales |
| 6.1 | test_c15_staff_notices.py | PG/UoW | 422 | aviso ausente | dos PID, dedup, rollback, FK real no ocultada | Verde |
| 6.2 | test_c15_staff_notices.py | API/PG | 422 | NoResultFound | ambos roles, nuevo ciclo, tres fallos/rollback | Verde |
| 6.3 | test_c15_staff_notices.py | API/PG | 422 | dos cancelaciones sin aviso | ambos roles, ciclo, paciente excluido, rollback | Verde |
| 6.4 | staff_notices / test_c15_journey.py | PG/SMTP | 422 | RED de avisos | snapshots de dos cambios, dos tipos, PII excluida | Verde |
| 6.5 | mismos | PG/SMTP | 422 | caracterización | None/vacío × acciones, sin cuenta, fallo SMTP | Verde |
| 7.1 | test_c15_operations.py | API/PG | 422 | 404 | filtro, orden, página, vacío, proyección | Verde |
| 7.2 | test_c15_operations.py | API/PG | 422 | ruta ausente | roles ambas rutas, 401/403, aislamiento | Verde |
| 7.3 | test_c15_operations.py | API/PG | 422 | 404 | día local, claims, futuro, umbral .8 | Verde |
| 7.4 | operations / sweep | API/PG | 422 | 404/marca ausente | durable, sin estado, error/en curso/éxito, UUID | Verde |
| 8.1 | test_c15_journey.py | API/PG/SMTP | 422 | RED componentes anteriores | dos recorridos y cuenta coexistiendo | 2 verdes |
| 8.2 | suite backend | Integral | anteriores | N/A verificación | Resultado final al pie | Verificación |
| 8.3 | CLI / esta evidencia | Validación | anteriores | N/A documentación | 37 escenarios trazados, strict/diff | Verificación |
| 8.4 | CLI / CHANGES / Engram | Cierre apply | anteriores | N/A estado | all_done y cleanup temporal al finalizar | N/A |

## Trazabilidad de los 37 escenarios

Cada fila identifica el escenario del delta y la prueba observable correspondiente; parametrizaciones cubren sus variantes.

| Delta | Escenario | Pruebas |
|---|---|---|
| dispatch | Reclamación vigente | test_notificaciones: reclamacion_reenvia 119/120; shutdown |
| dispatch | Reclamación vencida elegible | test_notificaciones: 121; concurrency late_result |
| dispatch | Reclamación agotada | dispatch resultados_compatibles / vigencia_e_intentos |
| dispatch | Rechazo de vinculación no vigente | sweep lote_mixto; test_notificaciones rechazo |
| dispatch | Solicitud vigente y confirmada | dispatch vigencia_portipo |
| dispatch | Recordatorio y bordes temporales | dispatch vigencia_portipo ±1/0 |
| dispatch | Cambio de ciclo o turno sin vigencia | dispatch vigencia_portipo + sin_turno_propio |
| dispatch | Avisos de hechos consumados | dispatch avisos_hechos_consumados (10 casos) |
| dispatch | Tope no bloquea resolución sin envío | dispatch vigencia_e_intentos_se_resuelven_antes_del_cupo |
| dispatch | Repetición y carrera de programación | staff exact_duplicate_programming dos PID |
| dispatch | Nuevos ciclos y correos sin turno | schema nullable y other_cycle_type_or_channel |
| dispatch | Cancelación y reprogramación por personal | staff saves_notice ambos tipos/roles |
| dispatch | Fallo de programación o transporte | staff notice_failure; journey retry SMTP real |
| dispatch | Paciente y contacto ausente | staff patient_change / missing_contact |
| dispatch | Contenido y privacidad | staff snapshot; journey Mailpit + logs |
| dispatch | Aviso de reprogramación | staff reschedule_notice_keeps_snapshot_after_later_change |
| sweep | Pendientes tras suspensión | sweep despacha_atraso_y_conserva_futuro |
| sweep | Fallo de una entrega y resumen | sweep lote_mixto_y_reintento |
| sweep | Lote finito sin inanición por cupo de cuenta | sweep cuatro_grupos; concurrency quota batches |
| sweep | Dos barridos y despacho inmediato | concurrency two_sweeps_and_immediate |
| sweep | Caída y resultado tardío | concurrency expired_claim_late_result; shutdown |
| sweep | Secreto válido | triggers configured_secret y journey |
| sweep | Credencial ausente o incorrecta | triggers missing/wrong/unconfigured |
| sweep | Documentación y entrada ajena | triggers hides_openapi / query_and_body |
| sweep | Activación y recuperación | lifespan enabled y recoverable_failure |
| sweep | Desactivación y cierre | lifespan disabled/dispose; shutdown |
| sweep | Configuración inválida | settings interval_must_be_positive y timeout_guard |
| sweep | Borde de vencimiento y retención | cleanup tokens_expirados_y_retencion |
| sweep | Repetición y aislamiento | mismo + refresh_expirado_referenciado |
| operations | Fallidas del consultorio | operations failed_inbox minimal projection |
| operations | Roles y aislamiento | operations role_matrix y other_consultorio |
| operations | Consulta inválida o sin sesión | operations invalid_queries / role_matrix |
| operations | Estados y cuota del día | operations metrics_use_local_day_live_claims |
| operations | Umbral y vacío | operations metrics_alert y empty_metrics |
| operations | Reinicio de la API | operations latest_execution_is_durable |
| operations | Finalización fuera de orden | sweep fin_viejo_no_sustituye_barrido_posterior |
| operations | Interrupción o error | sweep ultimo_barrido_error; concurrency cancelled_sweep |

## Revisión y regresión final

Revisión independiente de sólo lectura, sin defectos bloqueantes confirmados: límites transaccionales de SMTP, orden de vigencia/cupo, fencing, limpieza por consultorio, secreto previo a trabajo, cancelación y dispose ordenado, proyección operativa. No sustituye las pruebas.

La primera suite integral sobre snapshot Linux (sólo scripts `.sh` convertidos CRLF→LF) dio **1449 passed / 5 failed in 199.74s**. Los cinco fallos correspondían exclusivamente a expectativas históricas que fijaban el head `0008` en cuatro archivos. Se ejecutó RED focal y se actualizaron al head `0009` y a la columna ciclo ya presente en head; las suites afectadas pasaron **30/30 in 29.30s**. No se modificó producción después del snapshot. La segunda suite integral, con esos cuatro tests actualizados, dio **1454 passed in 232.84s**, sin fallos ni skips. Comparación de todos los `.py` de aplicación, migraciones y tests contra el repositorio: `differences: []`.

Comando final (dentro de `c15-runner`, cwd `/tmp/c15-final/backend`): `/tmp/c15-venv/bin/python -m pytest -q`, con `TEST_DATABASE_URL` PostgreSQL temporal, `SMTP_TEST_HOST=c15-mail`, `SMTP_TEST_PORT=1025`, `MAILPIT_API_URL=http://c15-mail:8025`. El entorno respeta `uv.lock` y las pruebas no usan datos ni servicios publicados.

Alembic: único head `0009_notifications_outbox_sweep`. OpenSpec strict del change: `valid: true`, `issues: []`. `git diff --check`: exit 0. Sin nuevas dependencias ni hitos C16; únicamente backend/infra/documentación del alcance aprobado.

Retirados los tres contenedores temporales (`c15-runner`, `c15-mail`, `c15-pg`), sus volúmenes anónimos y `c15-testnet` tras verificar los IDs creados por esta ejecución. No se tocaron otros servicios. `CHANGES.md` conserva `[ ]` implementado, pendiente de archivo. No se sincronizaron specs principales ni se hizo commit o push.
