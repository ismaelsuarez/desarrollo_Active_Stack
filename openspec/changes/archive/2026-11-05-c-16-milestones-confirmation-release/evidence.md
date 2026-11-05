# C-16 — evidencia incremental de apply

Approval: approved (2026-11-05, by user), incluyendo ventanas de envío, tokens sin cuenta y auditoría sin identidad artificial.

## Entorno y safety net

Docker Desktop Linux, contenedores temporales propios `c16-pg` (PostgreSQL17), `c16-mail` (Mailpit1.30.1), `c16-runner` (Python3.13.18), red `c16-testnet`. Dependencias congeladas `UV_PROJECT_ENVIRONMENT=/tmp/c16-venv uv sync --frozen` (39 paquetes); copia de código y pruebas en `/work`, fuentes de solo lectura `/source`. Cada invocación crea su BD UUID mediante fixtures existentes. SMTP_TEST_HOST=c16-mail, SMTP_TEST_PORT=1025, MAILPIT_API_URL=http://c16-mail:8025.

Antes de modificar producción: **391 passed in 77.03s**, suites account_models, c07_booking/reschedule/lifecycle/hitos/migration, c15_dispatch/staff_notices/sweep, c09_patient_booking/actions/reschedule y notificaciones; **75 passed in 19.61s**, core_models/cuentas/cuenta_api/auth_endpoints. Safety net total **466 pruebas verdes**, sin fallos de fuente.

Preparación: primer snapshot omitía Dockerfile y archivos raíz compose/scripts y tenía variables SMTP incorrectas; los fallos FileNotFound se corrigieron copiando los archivos reales y usando las variables de prueba correctas. El full incompleto se interrumpió (SIGINT PID86) antes de código; no se clasifican como fallos preexistentes ni evidencia de baseline exitoso.

## Ciclos incrementales

- Despacho ventanas: RED solicitud aT24 enviada indebidamente (1failed) → GREEN1. Triangulación bordes solicitudT48/T24 y recordatorioT24/T12 ±1segundo, programada/enviando vencida:19passed.
- Enlace opaco: RED cuerpo sin fragmento token (1failed+19passed) → GREEN1; hash/turno/ciclo/vencimiento y ausencia de claro en cuerpo persistido verificados después.
- Fechas operativas y recordatorio: RED10failed1passed (fecha nula y cuerpo fijo) → GREEN conjunto31passed6.91s, incluidos ventanas y token.

La tabla por tarea y trazabilidad escenario→test documentan los frentes verificados; el resultado integral de la fuente final se registra por separado.

## Evidencia consolidada de los frentes

- Tokens: RED NOT NULL (1) → GREEN1; RED restricciones de propósito (6) → GREEN7. Preflight de upgrade/downgrade y recorrido reversible: GREEN14 de esquema. Confirmación: RED módulo inexistente → GREEN1; actor con/sin cuenta 2 fallos → GREEN4; inválidos 6 fallos → GREEN10; estados 5 fallos → GREEN17; HTTP405 → 200. La duplicación concurrente motivó bloquear turno y luego token: GREEN28 de enlaces. El frente informó **139 passed in 51.28s** con regresión y **11 passed in 21.26s** de migraciones; son ejecuciones solapadas, no sumables.
- Planificación: RED política inexistente → GREEN1; triangulación temporal 5 fallos/3 verdes → GREEN8. RED HTTP sin hitos → GREEN; configuración propia, roles, deduplicación con dos PID y rollback: 13 pruebas PG. RED omisión ausente → GREEN29 PG, con doce combinaciones de estado/acción y tres rollback. Una implementación intermedia produjo ocho UnboundLocalError al usar actualizado antes de asignarlo; se corrigió y el conjunto unidad/PG terminó en **37 passed in 5.78s**.
- Avisos: RED resumen ausente → GREEN1; RED cancelación del paciente/liberación ausentes (2) → GREEN3; triangulación con deduplicación, nueve combinaciones sin contacto, rollback y SMTP puerto1 → reintento Mailpit1025. El conjunto planificación/avisos dio **47 passed in 8.44s**. El hecho cancelado y el resumen original permanecen tras el error SMTP.
- Lista: RED seis filas en vez de dos → GREEN1; permisos RED cuatro fallos/cuatro verdes → GREEN con matriz ABAC **103 passed in 3.62s**. Refactor de helper común de avisos y regresión del frente: **141 passed in 27.03s**. Se añadieron después, sin cambio productivo, pruebas de marca→reprogramación→decisión del nuevo ciclo y contrato booleano: lista **19 passed in 5.41s**.
- Despacho concurrente: RED token del ciclo2 emitido para notificación del ciclo1 → GREEN32 con una sola lectura del turno y ciclo tomado de la notificación. Reintentos, resultado tardío, fencing y Mailpit: **41 passed in 5.30s**. Se agregaron dos caracterizaciones de resultado SMTP contra omisión en vuelo; no se inventa RED de un interbloqueo: la omisión excluye enviando y no espera esa fila.
- RN-60: RED política inexistente → GREEN1; triangulación ocho fallos → GREEN10. Evaluador PG RED inexistente → liberación verde tras integrar repositorio de avisos; siete variantes de marca fallaron antes de implementarlas y quedaron verdes. Dos conexiones PG bloqueadas en UPDATE verifican un ganador. Triggers reales fuerzan rollback de historial/aviso. Incluye inicio, decisión obsoleta, lotes100/3/0 y cupo agotado. La integración previa al despacho tuvo RED marca ausente → conjunto **42 passed in 6.73s**, con regresión del barrido C-15.
- Recorrido de producto: test_c16_journey recorre por HTTP/PG/Mailpit confirmar/rechazar replay, liberar/reutilizar hueco y solicitud fallida→marca→confirmación manual. La regresión de vigencia C-15 se actualizó a las nuevas ventanas: cuatro RED de expectativa anterior → **48 passed in 7.41s** en el conjunto correspondiente.
- Auditoría final de cobertura: se añadieron únicamente variantes de triangulación de comportamiento existente —recordatorio con solicitud enviada en otro ciclo; emisión real con cuenta vinculada; selector RN-60 con otro consultorio, confirmado, marcado y orden temporal—. Despacho/decisiones: **73 passed in 9.15s**. No se inventa RED para estas parametrizaciones de las guardas ya implementadas.
- Regresión integral intermedia: **1655 passed, 3 failed in 239.19s**. C-09 esperaba cero comunicaciones de turno y ahora conserva exactamente seis (resumen/cancelación y dos hitos de dos ciclos omitidos); la enumeración canónica de acciones no incluía `turno.sin_confirmar_ver`; faltaba copiar al runner la KB del aviso de privacidad. Se actualizaron las dos expectativas a contratos exactos y se copió la KB real, sin cambiar producción. Verificación focal de esos tres puntos: **10 passed in 2.37s**; C-09/despacho también **45 passed in 6.19s** antes de las dos variantes finales.

Las ejecuciones focales se superponen. El resultado integral de fuente final se registra por separado, sin sumarlas. Un intento de lista se interrumpió en colección mientras faltaba copiar el nuevo router de tokens al snapshot; se repitió con composición coherente, sin clasificarlo como RED funcional.

## TDD Cycle Evidence

Safety net común: **466**. Los archivos de test están bajo backend/tests/integration/, salvo los prefijos unit/. Los grupos comparten RED cuando diseñan la misma conducta; preparación, caracterización existente y verificación no tienen RED artificial. GREEN/refactor remite a las ejecuciones concretas anteriores y al cierre integral pendiente de registrar.

| Tarea | Test File | Layer | Safety Net | RED | GREEN / TRIANGULATE | REFACTOR |
|---|---|---|---|---|---|---|
| 1.1 | suites afectadas | Baseline | 466 | N/A preparación | 391 + 75 ejecutadas antes de producción | N/A |
| 1.2 | test_c16_token_schema.py | PostgreSQL | 466 | NOT NULL; seis restricciones | 14 de esquema: con/sin cuenta, propósito, FK, hash | Verde |
| 1.3 | test_c16_token_schema.py | Alembic/PG | 466 | Preflight y recorrido fallaban antes de revisión0010 | Upgrade/downgrade/upgrade, legado incompatible, conservación y head único | Verde |
| 2.1 | unit/test_c16_planning.py | Unidad | 466 | Módulo ausente; cinco variantes temporales | 8 casos, igualdad48,30,24,10 y configuración propia | Verde |
| 2.2 | test_c16_planning.py | UoW/PG | 466 | HTTP no programaba hitos | Dos PID, repetición, rollback de reserva/reprogramación | Verde |
| 2.3 | test_c16_planning.py | HTTP/PG | 466 | Reserva real sin hitos | Personal/paciente por cuatro anticipaciones, cero intentos al programar | Verde |
| 2.4 | test_c16_planning.py | HTTP/PG | 466 | Hitos anteriores conservados | 12 combinaciones estado/acción, dos canales, tres rollback | Verde |
| 2.5 | test_c16_planning.py / pending | HTTP/PG | 466 | Omisión anterior; reinicio C-07 caracterizado | Limpieza marca/fechas, rollback y evaluación del ciclo nuevo | Verde |
| 3.1 | test_c16_dispatch.py | PG/reloj | 466 | Solicitud enviada a T24 | Bordes ±1segundo, programada/vencida, cupos/intentos | Verde |
| 3.2 | test_c16_dispatch.py / journey | PG/SMTP | 466 | Cuerpo sin fragmento token | Hash/turno/ciclo/expiración, sin claro persistido, con/sin cuenta | Verde |
| 3.3 | test_c16_dispatch.py / confirm_link | PG concurrente | 466 | Enlace ausente; consumo inválido no rechazado | Dos enlaces mismo ciclo, TTL, vencimiento y reloj tras lock | Verde |
| 3.4 | test_c16_dispatch.py | PG/contenido | 466 | Texto fijo y fechas ausentes | Manual, falta de envío, marca, confirmado, otro ciclo y advertencia automática | Verde |
| 3.5 | test_c16_dispatch.py | PG concurrente | 466 | Fecha nula; token mezclaba ciclos | Solicitud/recordatorio × ciclo/reclamación; snapshot único | Verde |
| 3.6 | test_c16_dispatch.py / notices | PG/Mailpit | 466 | Componentes de texto/enlace anteriores | Fecha local y datos sintéticos sensibles fuera de cuerpo/logs | Verde |
| 4.1 | test_c16_confirm_link.py | Aplicación/PG | 466 | Módulo y auditoría ausentes | Cuatro variantes cuenta/consultorio, actor y consumo atómicos | Verde |
| 4.2 | test_c16_confirm_link.py | Aplicación/PG | 466 | Seis variantes inválidas aceptadas | Inexistente, usado, igualdad/pasado, tipo y ciclo | Verde |
| 4.3 | test_c16_confirm_link.py | PG/rollback | 466 | Cinco estados incompatibles aceptados | 409 y triggers de historial/consumo sin efectos parciales | Verde |
| 4.4 | test_c16_confirm_link.py | HTTP/OpenAPI | 466 | HTTP405 | 200 sin sesión, 422 extras, 400 genérico y alcance limitado | Verde |
| 4.5 | test_c16_confirm_link.py | PG concurrente | 466 | Confirmación duplicada | Mismo/distinto token, PID distintos y carreras con personal | Verde |
| 5.1 | unit/test_c16_decision.py | Unidad | 466 | Módulo ausente; ocho variantes | 10 casos de modo, estado, marca y borde con otro parámetro | Verde |
| 5.2 | test_c16_decisions.py | PG/reloj | 466 | Evaluador ausente | Selección ordenada,100/3/0, ajenos, confirmados, marcados e iniciados excluidos | Verde |
| 5.3 | test_c16_decisions.py / journey | PG/SMTP | 466 | Evaluador/aviso ausentes | Liberación e historial/aviso juntos; triggers; hueco reutilizable | Verde |
| 5.4 | test_c16_decisions.py | PG | 466 | Siete variantes sin marca | Manual/estados/ciclo, envío posterior no reabre decisión | Verde |
| 5.5 | test_c16_decisions.py | PG concurrente | 466 | Conducta nueva bajo RED del evaluador | Dos UPDATE esperando lock; un ganador, un historial/aviso | Verde |
| 5.6 | test_c16_decisions.py | PG concurrente | 466 | Conducta nueva bajo RED del evaluador | Estado/ciclo/marca obsoletos, UPDATE en espera e inicio alcanzado | Verde |
| 5.7 | test_c16_decisions.py / c15_triggers | Barrido/PG | 466 | Barrido no marcaba | Antes de despacho, cupo durable, lote y composición compartida | Verde |
| 6.1 | test_c16_notices.py | HTTP/PG | 466 | Tres avisos ausentes | Ambos reservantes, tipo según actor y deduplicación | Verde |
| 6.2 | test_c16_notices.py / c15_dispatch | PG/SMTP | 466 | Resumen ausente | Snapshot original, tres rollback, vigencia de hechos consumados | Verde |
| 6.3 | test_c16_notices.py | PG/Mailpit | 466 | RED anteriores de avisos | Nueve casos sin contacto; SMTP fallido/reintento sin revertir hecho | Verde |
| 7.1 | test_c16_pending.py | HTTP/PG | 466 | Seis filas en vez de dos | Estado/marca/consultorio/orden, incluye pendiente iniciado | Verde |
| 7.2 | test_c16_pending.py | HTTP/aplicación | 466 | Cuatro rechazos faltantes | Cinco roles, tres rechazos directos, cuatro false/ausente | Verde |
| 7.3 | test_c16_pending.py | HTTP/PG | 466 | Filtro nuevo bajo RED anterior | Cuatro acciones existentes, marca limpia y ciclo reevaluado | Verde |
| 8.1 | test_c16_journey.py / c15_triggers | HTTP/PG/SMTP | 466 | N/A integración de componentes probados | Tres recorridos y disparadores con composición real común | Verificación |
| 8.2 | suite backend | Integral | 466 | N/A verificación | 1661 passed in 242.38s, cero fallos/omisiones; fuente final comparada antes/después | Verificado |
| 8.3 | evidence.md / CLI | Validación | 466 | N/A documentación | 35 tareas y 62 escenarios relacionados abajo; validación estricta sin issues y diff limpio | Verificado |

## Trazabilidad de los 62 escenarios

Los nombres de escenario se conservan literalmente de los seis deltas. Cada referencia usa archivo::función; las parametrizaciones son parte de la función indicada. Prefijos de archivo, todos en backend/tests/integration/:

- P = test_c16_planning.py; N = test_c16_notices.py; A = test_c16_pending.py.
- D = test_c16_dispatch.py; E = test_c16_decisions.py; L = test_c16_confirm_link.py.
- S = test_c16_token_schema.py; J = test_c16_journey.py.
- U = backend/tests/unit/test_c16_decision.py.
- Referencias C-07/C-15 y notificaciones conservan su nombre completo en la tabla.

| # | Delta | Escenario | Pruebas concretas |
|---|---|---|---|
| 1 | appointment-confirmation | Reserva normal y borde de confirmación | P::test_staff_booking_programs_both_milestones_in_current_cycle; P::test_real_booking_observes_exact_birth_thresholds |
| 2 | appointment-confirmation | Reserva tardía y recordatorio futuro | P::test_real_booking_observes_exact_birth_thresholds (30h); unit/test_c16_planning.py::test_initial_confirmation_and_elapsed_milestones |
| 3 | appointment-confirmation | Hitos ya alcanzados al nacer | P::test_real_booking_observes_exact_birth_thresholds (24h/10h); unit/test_c16_planning.py::test_initial_confirmation_and_elapsed_milestones |
| 4 | appointment-confirmation | Rollback e idempotencia | P::test_planning_failure_rolls_back_turn_history_and_notifications; P::test_repeated_and_concurrent_planning_is_deduplicated |
| 5 | appointment-confirmation | Enlace válido con o sin cuenta | L::test_valid_link_without_account_confirms_consumes_and_audits_atomically; L::test_http_invalid_link_and_limited_scope_do_not_change_turn |
| 6 | appointment-confirmation | Consultorio del token | L::test_http_link_works_without_session_using_token_clinic; L::test_http_link_rejects_extra_fields_without_echoing_secrets |
| 7 | appointment-confirmation | Token inválido o de otro propósito | L::test_invalid_link_is_generic_and_keeps_turn_token_and_history; L::test_http_invalid_link_and_limited_scope_do_not_change_turn |
| 8 | appointment-confirmation | Liberado o estado incompatible | L::test_incompatible_state_returns_conflict_without_consuming_link |
| 9 | appointment-confirmation | Consumo simultáneo y fallo de historial | L::test_concurrent_links_confirm_once_with_distinct_postgres_connections; L::test_failure_rolls_back_state_token_and_audit |
| 10 | appointment-confirmation | Solicitud enviada y almacenamiento | D::test_solicitud_emite_enlace_en_memoria_y_guarda_solo_hash; D::test_mailpit_fecha_local_contenido_minimo_y_no_secretos_persistidos |
| 11 | appointment-confirmation | Reintento y vencimiento | D::test_reintento_emite_dos_tokens_del_mismo_ciclo_sin_invalidar; L::test_invalid_link_is_generic_and_keeps_turn_token_and_history; L::test_link_rechecks_clock_after_waiting_for_turn_lock |
| 12 | appointment-confirmation | Pendiente elegible en automático | D::test_recordatorio_solo_advierte_si_rn60_permite (automatico/enviada/sin marca); J::test_reserva_hitos_y_resolucion_con_mailpit (liberar) |
| 13 | appointment-confirmation | Solicitud no enviada o modo manual | D::test_recordatorio_solo_advierte_si_rn60_permite; variantes explícitas manual/ausente/fallida/programada/enviando/omitida/marca/otro_ciclo. |
| 14 | appointment-confirmation | Confirmado y privacidad | D::test_recordatorio_solo_advierte_si_rn60_permite (confirmado); D::test_mailpit_fecha_local_contenido_minimo_y_no_secretos_persistidos; J::test_reserva_hitos_y_resolucion_con_mailpit (confirmar) |
| 15 | appointment-confirmation | Borde exacto y antes del hito | U::test_rn60_libera_pendiente_con_solicitud_enviada_al_hito; U::test_rn60_triangula_guarda_temporal_marca_y_modo; E::test_iniciados_y_anterior_al_hito_no_se_seleccionan |
| 16 | appointment-confirmation | Confirmado nunca se libera | U::test_rn60_triangula_guarda_temporal_marca_y_modo; J::test_reserva_hitos_y_resolucion_con_mailpit (confirmar) |
| 17 | appointment-confirmation | Fallo de historial o aviso | E::test_error_de_efectos_revierte_liberacion_completa (triggers turno_historial/notificacion) |
| 18 | appointment-confirmation | Manual y fallos de solicitud | E::test_sin_prueba_envio_marca_una_vez_por_ciclo |
| 19 | appointment-confirmation | Envío posterior a la marca | E::test_sin_prueba_envio_marca_una_vez_por_ciclo (repetición tras enviada) |
| 20 | appointment-confirmation | Reprogramación reinicia decisión | A::test_rescheduled_marked_turn_reenters_decision_in_new_cycle; P::test_reschedule_clears_cycle_mark_and_delivery_dates |
| 21 | appointment-confirmation | Dos barridos simultáneos | E::test_dos_evaluaciones_bloqueadas_producen_un_solo_efecto (liberar/marcar) |
| 22 | appointment-confirmation | Cambio concurrente del turno | E::test_update_esperando_cambio_concurrente_pierde_sin_historial; E::test_decision_obsoleta_no_toca_cambio_concurrente |
| 23 | appointment-confirmation | Inicio exacto y pasado | E::test_iniciados_y_anterior_al_hito_no_se_seleccionan (0h/-1h) |
| 24 | appointment-confirmation | Inicio alcanzado entre selección y escritura | E::test_inicio_entre_seleccion_y_decision_impide_efectos (solicitud enviada/no enviada) |
| 25 | appointment-lifecycle | Turno marcado vuelve al ciclo normal | test_c07_reschedule.py::test_reschedule_exact_confirmation_threshold_resets_mark_once; P::test_reschedule_clears_cycle_mark_and_delivery_dates |
| 26 | appointment-lifecycle | Destino a menos de 48 horas | test_c07_reschedule.py::test_reschedule_exact_confirmation_threshold_resets_mark_once (2879min) |
| 27 | appointment-lifecycle | Destino exactamente a 48 horas | test_c07_reschedule.py::test_reschedule_exact_confirmation_threshold_resets_mark_once (2880min) |
| 28 | appointment-lifecycle | Omisión por tipo y ciclo | P::test_change_omits_only_scheduled_milestones_of_appropriate_cycle (reprogramar, cuatro estados y dos canales) |
| 29 | appointment-lifecycle | Fallo de la nueva planificación | P::test_planning_failure_rolls_back_turn_history_and_notifications (reprogramar); P::test_omission_failure_rolls_back_change |
| 30 | appointment-lifecycle | Cancelar o liberar con hitos pendientes | P::test_change_omits_only_scheduled_milestones_of_appropriate_cycle (cancelar/liberar); N::test_patient_cancellation_and_release_create_corresponding_notice |
| 31 | appointment-lifecycle | Reclamación en vuelo y error transaccional | P::test_change_omits_only_scheduled_milestones_of_appropriate_cycle (enviando); P::test_omission_failure_rolls_back_change; D::test_resultado_smtp_y_omision_en_vuelo_no_interbloquean |
| 32 | appointment-agenda | Filtrado por marca estado y consultorio | A::test_list_filters_mark_state_and_clinic_in_chronological_order |
| 33 | appointment-agenda | Resolución y reinicio | A::test_existing_actions_resolve_dedicated_list; A::test_rescheduled_marked_turn_reenters_decision_in_new_cycle |
| 34 | appointment-agenda | Roles sin acceso al filtro | A::test_only_reception_and_admin_can_request_filter; A::test_application_policy_also_rejects_filter_without_router |
| 35 | appointment-agenda | Compatibilidad de lectura existente | A::test_false_and_absent_filter_preserve_previous_role_scope |
| 36 | core-data-models | Creación de token de usuario con turno_id nulo | S::test_token_with_account_preserves_its_purpose; test_core_models.py::test_tokens_y_refresh_tokens |
| 37 | core-data-models | Registro de refresh token para usuario | test_core_models.py::test_tokens_y_refresh_tokens; test_auth_endpoints.py::test_flujo_completo_login_me_refresh_logout |
| 38 | core-data-models | Referencia de turno inexistente | S::test_confirmation_token_keeps_fk_and_hash_uniqueness |
| 39 | core-data-models | Confirmación de ficha sin cuenta | S::test_confirmation_token_without_account_keeps_turn_and_cycle |
| 40 | core-data-models | Restricciones según propósito | S::test_confirmation_token_requires_a_turn; S::test_token_with_account_preserves_its_purpose |
| 41 | notification-dispatch | Reclamación vigente | test_notificaciones.py::test_reclamacion_se_reenvia_solo_si_es_mas_vieja_que_ttl (119/120segundos) |
| 42 | notification-dispatch | Reclamación vencida elegible | test_notificaciones.py::test_reclamacion_se_reenvia_solo_si_es_mas_vieja_que_ttl (121segundos); D::test_ventanas_bordes_solicitud_y_recordatorio (vencida) |
| 43 | notification-dispatch | Reclamación agotada | test_notificaciones.py::test_intentos_agotados_no_vuelven_a_enviar; test_c15_dispatch.py::test_vigencia_e_intentos_se_resuelven_antes_del_cupo |
| 44 | notification-dispatch | Rechazo de vinculación no vigente | test_notificaciones.py::test_rechazo_no_verificado_se_omite_antes_de_intentos; test_notificaciones.py::test_rechazo_requiere_verificacion_de_cuenta_del_consultorio |
| 45 | notification-dispatch | Solicitud vigente y confirmada | test_c15_dispatch.py::test_vigencia_portipo_en_primera_toma_y_recuperacion; D::test_ventanas_bordes_solicitud_y_recordatorio |
| 46 | notification-dispatch | Recordatorio y bordes temporales | D::test_ventanas_bordes_solicitud_y_recordatorio; test_c15_dispatch.py::test_vigencia_portipo_en_primera_toma_y_recuperacion |
| 47 | notification-dispatch | Cambio de ciclo o turno sin vigencia | test_c15_dispatch.py::test_vigencia_portipo_en_primera_toma_y_recuperacion; test_c15_dispatch.py::test_recordatorio_sin_turno_propio_es_omitido |
| 48 | notification-dispatch | Avisos de hechos consumados | test_c15_dispatch.py::test_avisos_hechos_consumados_sin_exigir_turno_activo (cinco tipos × dos estados de reclamación) |
| 49 | notification-dispatch | Tope no bloquea resolución sin envío | test_c15_dispatch.py::test_vigencia_e_intentos_se_resuelven_antes_del_cupo; D::test_vencimiento_se_resuelve_antes_de_cupos_e_intentos |
| 50 | notification-dispatch | Barrido retrasado hasta el hito siguiente | D::test_solicitud_se_omite_al_alcanzar_siguiente_hito; D::test_ventanas_bordes_solicitud_y_recordatorio; E::test_barrido_tardio_marca_y_omite_hitos_antes_del_despacho |
| 51 | notification-dispatch | Resultado exitoso del ciclo actual | D::test_registra_fecha_operativa_del_ciclo_enviado (dos tipos) |
| 52 | notification-dispatch | Resultado tardío tras reprogramación o pérdida de reclamación | D::test_resultado_tardio_no_contamina_fechas_nuevas (dos tipos × dos carreras); D::test_solicitud_vieja_no_emite_token_del_ciclo_nuevo_entre_lecturas |
| 53 | notification-dispatch | Resumen independiente de cambios posteriores | N::test_booking_creates_one_minimal_snapshot_even_after_rescheduling; N::test_failed_smtp_preserves_fact_then_mailpit_receives_original_snapshot |
| 54 | notification-dispatch | Cancelación por paciente y distinción del personal | N::test_patient_cancellation_and_release_create_corresponding_notice; test_c15_staff_notices.py::test_patient_change_does_not_create_staff_notice; test_c15_staff_notices.py::test_staff_cancellation_saves_notice_for_current_cycle |
| 55 | notification-dispatch | Fallo de programación y ausencia de contacto | N::test_notice_insert_failure_reverts_fact_and_history; N::test_missing_contact_keeps_fact_and_logs_no_patient_details |
| 56 | notification-dispatch | Contenido mínimo y fallo de transporte | N::test_booking_creates_one_minimal_snapshot_even_after_rescheduling; N::test_failed_smtp_preserves_fact_then_mailpit_receives_original_snapshot |
| 57 | notification-sweep | Pendientes tras suspensión | test_c15_sweep.py::test_barrido_despacha_atraso_y_conserva_futuro; E::test_barrido_tardio_marca_y_omite_hitos_antes_del_despacho |
| 58 | notification-sweep | Fallo de una entrega y resumen | test_c15_sweep.py::test_lote_mixto_y_reintento_una_vez_por_ejecucion |
| 59 | notification-sweep | Lote finito sin inanición por cupo de cuenta | test_c15_sweep.py::test_cuatro_grupos_acotados_y_futuros_ajenos_excluidos; test_notificaciones.py::test_cupo_cuenta_reserva_capacidad_para_turnos |
| 60 | notification-sweep | Hitos y decisión tras retraso prolongado | E::test_barrido_tardio_marca_y_omite_hitos_antes_del_despacho; E::test_rn60_libera_y_confirma_historial_aviso_juntos |
| 61 | notification-sweep | Disparadores comparten decisiones y límites | test_c15_triggers.py::test_http_and_lifespan_use_same_real_composition; E::test_seleccion_por_lotes_100_3_0_sin_reevaluar_resueltos |
| 62 | notification-sweep | Cuota agotada no bloquea decisiones | E::test_cupo_agotado_no_frena_liberacion_y_aviso_queda_durable |

## Verificación integral y estado de cierre

El full final se ejecuta sobre una fuente congelada. Antes de esa ejecución, la comparación **byte a byte de 272 archivos Python** de app/tests/alembic entre fuente y runner no mostró diferencias. El primer intento integral encontró dos fallos de infraestructura por CRLF en la copia Linux de scripts/dev_secrets.sh; se corrigió únicamente esa copia a LF, se detuvo el proceso de pruebas anterior y se reinició. La copia Linux del script y la fuente normalizada canónicamente a LF tienen el mismo SHA256: `360215588f840c4bce929ae2de656b641eb458256af1891600e9f0ef2058d3ec`. No se presenta el intento interrumpido como suite aprobada ni como fallo de producto. El intento intermedio completo de 1655 aprobadas/3 fallidas se describe arriba; después de cerrar sus tres causas y las variantes adicionales auditadas, se preparó nuevamente el snapshot final coherente.

Comando integral en `/work`: `/tmp/c16-venv/bin/python -m pytest -q`, con TEST_DATABASE_URL de PostgreSQL temporal propio y las tres variables SMTP de la sección Entorno. **Resultado final: 1661 passed in 242.38s (0:04:02), cero fallos y cero omisiones.** Ningún código o prueba cambió después del inicio de esa ejecución.

La comparación byte a byte de los **272 archivos Python** app/tests/alembic antes y después del full devolvió `differences: []`. Cabeza Alembic única: `0010_confirmation_tokens`, descendiente de 0009. Validación estricta del change: `valid: true, issues: []`; `git diff --check` sin errores. El checklist se cierra por CLI en 35/35; archivo/sync de specs principales, commit y push no se ejecutan en esta fase.

Límites conservados: entrega de correo al menos una vez; no hay backfill de hitos históricos ni frontend de consumo del enlace (C-14). El downgrade de 0010 aborta antes de mutar si existen tokens sin cuenta, en vez de destruirlos para satisfacer NOT NULL. No se incorporaron servicios, dependencias o secretos nuevos.

Limpieza completada tras verificar los IDs completos creados en esta sesión: runner `496ceceb…`, Mailpit `939ee241…`, PostgreSQL `63f0eaa0…` (incluido su volumen anónimo propio), red `3a0074a5…`. El bind `/source` era de solo lectura y no se eliminó ningún archivo del workspace. `docker ps -a` posterior conserva únicamente los dos contenedores ajenos detenidos que existían al empezar.

## Cierre y archivo (2026-11-05)

Tras la orden del usuario de archivar, commitear y publicar, se sincronizaron seis capacidades con 12 requisitos añadidos y 4 modificados. Se verificaron los 16 bloques contra sus deltas, los títulos y propósitos existentes, todos los escenarios anteriores y el contenido no mencionado. La nueva `appointment-confirmation` conserva literalmente el propósito del delta. Las 30 especificaciones principales validan; la advertencia de longitud de un requisito de `local-environment` es previa y ajena a C-16. El change validó en modo estricto sin issues.

Con la sincronización completada y verificada, `openspec archive c-16-milestones-confirmation-release --skip-specs --yes --json` archivó el change como `2026-11-05-c-16-milestones-confirmation-release`; `--skip-specs` evitó reaplicar la sincronización inline ya terminada. La lista de changes activos quedó vacía y CHANGES.md marca C-16 completo. Este cierre modifica sólo documentación y specs; conserva la evidencia de ejecución y no vuelve a ejecutar pruebas de producción sin cambios de fuente.

La unidad de commit incluye el comportamiento C-16, su migración, pruebas y documentación. Su frontera de rollback es C-16 completo: revertir ese commit devuelve la aplicación y las specs a C-15; el esquema requiere además el preflight documentado antes de bajar 0010. No se exporta memoria al repositorio porque `.engram/` no existe ni está versionada.

La comprobación del índice (`git diff --cached --check`), que también examina archivos nuevos, detectó una línea vacía adicional al final de `backend/app/infrastructure/db/confirmacion_turno.py`. Se retiró únicamente ese espacio final después del full; el contenido no blanco es idéntico y no cambió lógica ni prueba. La comprobación posterior del índice quedó sin errores. Los 272 archivos idénticos documentados arriba corresponden a la fuente exacta ejecutada durante el full, antes de este ajuste de formato.
