# C-09 implementation evidence

## Environment and safety net

2026-11-05: PostgreSQL 17 and Mailpit v1.30.1, disposable Docker network `c09-tests` and runner `c09-test-runner` Python 3.13.18. Dependencies installed with `uv sync --frozen` into `/tmp/c09-venv` (39 locked packages). Each pytest process creates an isolated UUID database through existing fixtures.

Before production changes, executed:

```text
/tmp/c09-venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/test_c07_booking.py tests/integration/test_c07_agenda.py tests/integration/test_c07_reschedule.py tests/integration/test_c07_lifecycle.py tests/integration/test_c08_records.py tests/integration/test_c08_unlink.py tests/unit/policies tests/unit/test_reserva.py
```

Result: **488 passed in 84.42s**, no failures/skips. Task 1.1.

Registry refresh: Linux attempted, unavailable `gentle-ai`; Windows project venv refresh then succeeded (40 skills normalized), no registry diff.

## TDD cycles

- Reservation tracer: `test_verified_patient_books_for_current_record`: RED **403 versus 201**, then GREEN **1 passed in 9.25s**. Introduced role-specific payload and current-record lookup, online origin, existing transaction/history/hitos.

Further cycles and final scenario traceability are recorded as they complete. Historical C08 results are not counted as C09 validation.

| Tasks | Tests | Layer | Safety net | RED | GREEN / triangulation | Refactor |
|---|---|---|---|---|---|---|
| 1.2 | test_c09_disponibilidad.py | Unit | 488 baseline | missing import; 2 blocking cases | 4 cases | final 64 including reserva |
| 1.3 | test_c09_disponibilidad.py | Unit | 488 baseline | 11 occupancy failures | 17 cases including all states/sobreturnos | final 64 |
| 1.4 | test_c09_disponibilidad.py | Unit | 488 baseline | 3 future-start failures | 22 cases, anchors 15/20 and nonmultiple duration | final 64 |
| 1.5 | test_c09_disponibilidad.py | Unit/docs | 488 baseline | 3 horizon/order failures | final 29 unit tests; UTC/local boundary and day60/61 | final 64 |
| 2.1 | test_c09_public.py | PostgreSQL | 488 baseline | missing projection | 1 then scoped limits/config | 28 C07 repository regressions |
| 2.2 | test_c09_public.py | API/PostgreSQL | 488 baseline | 4 missing-route failures | 5 then inactive/foreign/minimal/strict cases | 57 combined final |
| 2.3 | test_c09_public.py | API/PostgreSQL | 488 baseline | 4 missing-route failures | 11 then sobreturno/cancelled/released/horizon | 57 combined final |
| 2.4 | test_c09_public_limit.py | Unit | new adapter | import error then 2 capacity failures | 3 quota/renewal/origin/capacity/pruning tests | 57 combined final |
| 2.5 | test_c09_public.py | API | 488 baseline | missing quota integration | shared routes, 429/Retry-After, untrusted forwarded header, no PII logs | 57 combined final |
| 3.1–3.2 | test_c09_patient_booking.py | API/PostgreSQL | 488 baseline | 403 vs201; unverified email201 vs403 | 12 prohibited-field cases, current link and unverified cases; 148 including ABAC | no separate refactor yet |
| 3.3 | test_c09_patient_booking.py | PostgreSQL/API | 488 baseline | third booking201 vs409 | future states and staff-created reservations, max1/max2 | 27 booking green |
| 3.4 | test_c09_patient_booking.py | PostgreSQL/concurrency | 488 baseline | characterization of implemented lock | two real backend PIDs, barrier, one201/one409; single history | 27 booking green |
| 3.5 | test_c09_patient_booking.py | API | 488 baseline | day61 and past accepted201 vs422 | day60/61, local date, 48h/47h59, staff horizon exemption/granularity | 36 booking green |
| 3.6 | test_c09_patient_booking.py | PostgreSQL/fault injection | 488 baseline | existing UoW characterized, no invented RED | history/hitos/commit failure and success, no notifications | 36 booking green |
| 5.1–5.2 | test_c09_patient_reschedule.py | API/PostgreSQL | 488 baseline | 403 vs200; day61 accepted | 45min/current ID/full cup, strict extras/null, day61/grid/24h boundary | 11 green before occupancy extension |
| 6.1 | test_c09_public.py | PostgreSQL | 488 baseline | 3 missing-method failures | ordered max3, empty, 30/45min/exclude own/horizon, bounded queries | 57 combined final |
| 6.2 creation | test_c09_patient_booking.py | API/PostgreSQL | 488 baseline | 2 conflicts lacked alternatives | 2 green (regular and sobreturno), interval-only details | pending full final |

Additional independent runs: **148 passed in 12.45s** (17 booking + 131 existing ABAC), **27 booking passed in 17.21s**, **36 booking passed in 14.68s**, **11 rescheduling passed in 10.84s**, **2 occupancy cases passed in 11.55s**. Public worker final **57 passed in 18.68s** (26 public integration, 3 limiter unit, 28 C07 repository regressions). Domain final **64 passed in 1.30s** (29 new availability, 35 reserva). These counts overlap; they are not summed as a full suite result.

Test fixture correction: the initial rescheduling RN-29 threshold used a destination one day after the original and accidentally violated the original turn's 24h action window at47h59. Corrected destination to one day before original, keeping both valid original window and requested threshold. This third failure was a fixture mistake, not a production defect. The other two RED failures (horizon and contact) drove production changes.

## Later integration and review cycles

- PATCH occupancy: **RED 1 failed / 14 passed**, missing alternatives; shared role-aware conflict wrapper → combined booking/rescheduling **53 passed in 19.44s**. Preserves every persisted field/history on rejection; fault injection covers history/hitos/commit with unchanged cycle/mark and no notifications.
- Verification policy: explicit current verification now defaults to false in `ContextoAcceso`. New pure tests **RED 1 failed / 2 passed** (omitted verification granted access), then GREEN including explicit verified/unverified. Updated former policy test to supply verified=true for its allowed creation scenario. Combined policies + C07/C09 booking/rescheduling **266 passed in 38.82s**, including staff with unverified accounts.
- Contract expectations intentionally updated: C07 patient staff-shaped POST now422; patient without current record PATCH now404. These are new C09 behavior, not pre-existing failures. Staff cases remain covered.
- Real PostgreSQL races `test_c09_races.py`: **4 passed in 11.61s**. Two patient accounts on identical/partially overlapping slots use distinct backend PIDs and a barrier, resulting one201/one409 with alternatives and one turn/history. Online creation versus unlink runs both effective orders; `pg_blocking_pids` proves waiting rather than timing sleeps. Creation before unlink commits201, unlink before creation yields403; old JWT lists200[] afterwards.
- Independent review found inactive-catalog alternatives regression: adjusted45min existing turn with deactivated prestation received[] despite free slots. **RED1 / GREEN1** then allowing inactive prestation only when preserved duration is supplied → **2 passed in 10.85s** (active/inactive catalog). Creation/public queries continue requiring active resources.
- Independent review found public date overflow: `fecha=9999-12-31` produced500 before horizon calculation. **RED1 / GREEN1**, compare local-day distance before adding a day → **31 public/limiter passed in 15.38s**.

Task5.4/6.2 API formats and duration behavior documented in README/OpenAPI. No new schema migration, real hitos notifications, Redis, frontend or JWT claims were introduced. Staff concurrent creation remains exempt from max-count; simultaneous regular/sobreturno insertion retains RN17 residual risk.

## Self-service and end-to-end closure

Additional safety net for readings/actions: **140 passed in 39.04s**. `test_c09_patient_actions.py`: list RED403→GREEN1; detail/history RED403→GREEN3; actions RED8 absent fields→GREEN11; confirmation RED2→GREEN13; cancellation RED3→GREEN16; JWT/rollback/window-configuration triangulation →22. Final **162 passed in47.95s** (22 actions +140 C07); postrefactor **86 passed in30.12s** (22 actions +29 availability +35 reserva).

`test_c09_journey.py` + races final **5 passed in16.13s** with actual SMTP/Mailpit. Public consult → registration → verification mail → login → reserve → list → confirm → reschedule → cancel; one turn, four history entries, one C05 message and no C16 notification. Unverified login403, anonymous401, foreign detail404 and no private values in captured logs.

Full-suite runner uses `/tmp/c09-final`, a disposable copy of the project excluding git/node_modules/venvs/cache; only copied root shell scripts are normalized to LF, matching Linux checkout. Working-tree scripts are unchanged. Two post-copy changes were checked explicitly: `CicloTurnos` extracts an identical phone string to a local variable (no behavior change); action test fixture explicitly sets email_verificado=true. Both final source files were tested by the **86-test postrefactor run**, separately from the full copied snapshot. No final-source full-suite claim is inferred from the copy alone.

## Per-task TDD evidence

Files below are under `backend/tests/` unless documentary. Baseline488 refers to the actual pre-production PostgreSQL run above; U140 is the additional action baseline. Characterization rows introduce no new production code and do not invent a historical RED.

| Task | Test file / artifact | Layer | Safety net | RED | GREEN / triangulation | Refactor |
|---|---|---|---|---|---|---|
| 1.1 | C07/C08/policies baseline command | PG/unit | 488/488 | N/A baseline | 488 | N/A |
| 1.2 | unit/test_c09_disponibilidad.py | Unit | new/488 | import, exceptions2 | 30/60min, blocks/pauses | 64 green |
| 1.3 | same | Unit | 488 | occupancy11 | regular/sobreturno, states/edges | 64 green |
| 1.4 | same | Unit | 488 | future3 | anchors15/20,20min/future | 64 green |
| 1.5 | same + README | Unit/docs | 488 | horizon/order3 | day60/61,localUTC,no mutation | 64 green |
| 2.1 | integration/test_c09_public.py | PG | 488 | missing projection | config/scope/interval/N+1 | 57 green |
| 2.2 | same | API/PG | 488 | routes4 | active/inactive/minimal/foreign | 57 green |
| 2.3 | same | API/PG | 488 | availability404 | exceptions,states,empty,query,dates | 31 public/limiter green |
| 2.4 | unit/test_c09_public_limit.py | Unit | new | import,capacity2 | quota/window/origin/pruning | 3 green |
| 2.5 | integration/test_c09_public.py + README/OpenAPI | API/docs | 488 | quota200vs429 | sharedroutes/XFF/privacy | 31 green |
| 3.1 | integration/test_c09_patient_booking.py | API/PG | 488 | 403vs201 | 12 forbidden cases,both schemas | 266 combined green |
| 3.2 | same + unit/policies/test_c09_verified_booking.py | API/unit | 488 | unverified201;default allowed | no link,unverified,verified/default | 266 green |
| 3.3 | integration/test_c09_patient_booking.py | PG/API | 488 | third201vs409 | max1/2,states,staff,past | 53 combined green |
| 3.4 | same | PG concurrency | 488 | characterization of locked3.3 | two PIDs/barrier,last cup | 27 booking green |
| 3.5 | same | API | 488 | day61/past201 | day60/61,grid,48h/47h59,staff | 36 booking green |
| 3.6 | same | PG fault injection | 488 | existing UoW characterized | history/hitos/commit/no effects | 36 green |
| 4.1 | integration/test_c09_patient_actions.py | API/PG | U140 | list403 | past/future/scoped/no link | 86 postrefactor green |
| 4.2 | same | API/PG | U140 | detail/history403 | own/foreign/JWT old | 86 green |
| 4.3 | same | API/PG | U140 | missing fields8 | states/windows/staff unchanged | 86 green |
| 4.4 | same | API/PG | U140 | confirmation2 | own/foreign/final/rollback | 86 green |
| 4.5 | same | API/PG | U140 | cancellation3 | exact24h/phone/final/rollback | 86 green |
| 4.6 | README/OpenAPI + same | Docs/API | U140 | documentary N/A | current link/JWT/logs | reviewed |
| 5.1 | integration/test_c09_patient_reschedule.py | API/PG | 488 | patch403 | null extras,own/foreign,window | 53 combined green |
| 5.2 | same | PG/API | 488 | day61 accepted | 45min/full cup/grid/own exclusion/conflict | 53 green |
| 5.3 | same | PG fault injection | 488 | existing lifecycle characterized | cycle/mark/48h/hitos/history/commit | 53 green |
| 5.4 | README/OpenAPI + C07 reschedule | Docs/API | 488 | documentary N/A | staff regressions/request examples | 266 combined green |
| 6.1 | integration/test_c09_public.py | PG | 488 | missing method3 | order3/empty/30/45/exclude/horizon | 57 green |
| 6.2 | booking/reschedule files | API/PG | 488 | alternatives missing2+1 | regular/sobreturno/45min/no max mix | 53 green; inactive2 green |
| 6.3 | integration/test_c09_races.py | PG concurrency | 488 | characterization | identical/partial,2accounts/PIDs | 5 combined green |
| 6.4 | same | PG concurrency | 488 | list403 during4.1 development | both orders,pg_blocking_pids,JWT | 5 green |
| 7.1 | integration/test_c09_journey.py | API/PG/SMTP | 488 | confirm403 during4.4 development | full journey + denial edges | 5 green |
| 7.2 | full-suite command | Backend all | above | no fabricated RED | final results below | see snapshot note |
| 7.3 | CLI/this file/git diff | Docs/CLI | above | N/A | strict issues[],traceability,whitespace | reviewed |

## Scenario traceability (31/31)

Test names below identify actual behavioral tests, including parametrized cases; no assertion-only proxy is used.

| Delta / scenario | Test |
|---|---|
| public-availability / Catálogo sin sesión | public: test_public_catalogues_are_minimal_without_session_and_scoped |
| public / Aislamiento y entradas estrictas | public: test_public_catalogues_reject_tenant_query_and_hide_inactive |
| public / Bloque, excepción y turnos | public: test_availability_excludes_real_booking_and_global_block_and_has_minimal_intervals; disponibilidad: test_excluye_excepciones_totales_o_parciales_pero_admite_contiguidad |
| public / Duración y pausa | disponibilidad: test_prestacion_larga_no_se_parte_entre_bloques_ni_cruza_la_pausa |
| public / Sobreturnos y estados sin ocupación | public: test_availability_observes_overbooking_and_released_states |
| public / Recurso inválido o día sin atención | public: test_public_reference_visibility_and_empty_days |
| public / Granularidad configurable | disponibilidad: test_grilla_anclada_y_duracion_no_multiplo_sin_redondeo |
| public / Último día y zona | disponibilidad: test_horizonte_incluye_el_ultimo_dia_local; test_fecha_horizonte_se_calcula_en_zona_local_cerca_de_medianoche_utc |
| public / Hoy y prestación no múltiplo | disponibilidad: test_hoy_ofrece_solo_inicios_estrictamente_futuros; test_grilla_anclada_y_duracion_no_multiplo_sin_redondeo |
| public / Cuota y recuperación | public: test_four_routes_share_origin_quota_ignore_untrusted_forwarded_and_renew |
| public / Otro origen y datos mínimos | public: same quota test; test_public_logs_and_responses_do_not_echo_private_query_or_account |
| patient-appointment-management / Registro con ficha o vinculación posterior | booking: test_verified_patient_books_for_current_record; test_online_initial_state_exact_threshold; journey full verification |
| patient / Correo sin verificar o cuenta sin ficha | booking: test_patient_requires_current_record_and_verified_email |
| patient / Último día y máximo configurable | booking: test_online_horizon_uses_local_date; test_third_future_booking_exceeds_configured_maximum |
| patient / Estados y liberación de cupo | booking: test_only_future_active_states_use_limit_including_staff; actions: test_cancelar_propietario_respeta_ventana_exacta_y_telefono |
| patient / Dos reservas y un cupo | booking: test_two_real_connections_cannot_consume_last_place_twice |
| patient / Grilla y personal | booking: test_online_rejects_off_grid_start; test_staff_retains_horizon_exemption_but_not_grid |
| patient / Titular actual y turno ajeno | actions: test_lista_propia_incluye_pasados_y_futuros_sin_otro_consultorio; test_detalle_historial_propios_y_ajenos_resuelven_vinculo_actual |
| patient / JWT anterior a desvincular | actions: test_jwt_previo_a_desvincular_no_da_lecturas_ni_acciones; races: test_online_booking_and_unlink_serialize_on_patient_row |
| patient / Cancelación en límite y fuera de plazo | actions: test_cancelar_propietario_respeta_ventana_exacta_y_telefono |
| patient / Confirmación y estados finales | actions: test_titular_confirma_pendiente_y_guarda_historial; test_confirmacion_propia_rechaza_ajeno_y_estado_liberado; test_cancelar_ajeno_no_revela_telefono_y_final_no_modifica |
| patient / Ajuste previo y cupo lleno | reschedule: test_patient_reschedules_adjusted_duration_without_extra_place |
| patient / Destino inválido u ocupado | reschedule: test_patient_patch_horizon_grid_and_unchanged_on_rejection; test_occupied_patch_preserves_every_original_field_and_offers_45min |
| patient / Dos cuentas y mismo hueco | races: test_two_accounts_compete_for_one_slot_with_real_connections |
| patient / Sobreturno o agenda llena | booking: test_occupied_online_booking_offers_private_alternatives; public: test_alternatives_empty_at_horizon_or_no_open_blocks |
| patient / Reserva y reprogramación exitosas | booking: test_online_creation_integration_is_atomic_without_notifications; reschedule: test_patient_reschedules_adjusted_duration_without_extra_place |
| patient / Fallo de integración | booking: same fault-injection test; reschedule: test_online_patch_rolls_back_complete_cycle |
| appointment-booking / Consultorio enviado por cliente | C07 booking: test_booking_rejects_fields_owned_by_server |
| booking / Recurso ajeno | C07 booking: test_booking_hides_foreign_and_missing_references |
| booking / Entrada mínima online | booking: test_verified_patient_books_for_current_record |
| booking / Campos reservados al personal o al servidor | booking: test_patient_cannot_send_staff_or_server_fields; C07 staff regressions |

## Final verification

Executed full backend suite in the disposable Linux copy:

```text
docker exec -w /tmp/c09-final/backend c09-test-runner /tmp/c09-venv/bin/python -m pytest -q -p no:cacheprovider
```

**1308 passed in 340.29s (0:05:40), no failures or skips.** Includes all unit, infrastructure, PostgreSQL integration, SMTP/Mailpit, C07/C08 regressions and C09 behavior. Final source's two post-snapshot edits have the separate86/86 postrefactor evidence documented above; counts overlap and are not added.

`alembic heads` → `0008_turnos_core (head)`; `python scripts/check_single_head.py` → `Heads: 0008_turnos_core`. No new migrations.

Final `openspec validate c-09-availability-public-booking --strict --json`: valid=true, issues=[]. `git diff --check`: exit0; Git emits only line-ending conversion notices for Windows files. All31 spec scenarios mapped above. Tasks33/33 complete, pending human review of closure; no archive, main-spec synchronization, commit or push.
