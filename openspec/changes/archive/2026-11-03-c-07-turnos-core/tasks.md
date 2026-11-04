# Tasks

Plan de implementación de C-07. Las casillas reflejan la ejecución de apply; la preparación de artefactos no se contó como implementación. Ver `proposal.md`, `design.md` y los cinco deltas de `specs/` para alcance, fuentes y criterios de aceptación.

Criterio temporal confirmado por el usuario el 2026-11-03: ausente se permite con `ahora >= inicio`, sujeto a rol, agenda y estado. No editar la KB como efecto de apply sin autorización específica. Las referencias ESC remiten a la matriz de revisión de `design.md`.

Para cada tarea que cambie comportamiento: registrar baseline de pruebas relacionadas; detenerse ante fallos preexistentes; escribir y ejecutar RED antes de producción; mínimo GREEN; TRIANGULATE con camino normal y borde/rechazo y todos los escenarios aplicables; REFACTOR con pruebas verdes. Documentar evidencia por tarea en el resumen de apply, sin marcar casillas por haber escrito solo pruebas o código. Pruebas de repositorios, restricciones y concurrencia siempre contra PostgreSQL real descartable; datos exclusivamente sintéticos y tiempo por `Reloj`.

## 1. Preparación y red de seguridad para apply

- [x] 1.1 Verificar autorización explícita de apply y estado actual del change con `openspec status --change c-07-turnos-core --json`; cargar skills locales de dominio según el registro del proyecto. Verificar que la decisión temporal confirmada y el alcance no UI siguen vigentes antes de tocar código.
- [x] 1.2 Registrar baseline desde backend con `uv run pytest -m "not integration"` y las pruebas de integración relacionadas con turno, repositorios, unidad de trabajo, ABAC y agenda; usar PostgreSQL real con TEST_DATABASE_URL según README. Verificar conteos y ausencia de fallos preexistentes; detenerse y reportar si los hay.
- [x] 1.3 Comprobar `uv run alembic heads` y la cadena actual antes de generar la revisión; verificar un único head y que la revisión nueva se apoyará en él, inicialmente `0007_agenda_config`. Si avanzó, rebasar sin editar revisiones archivadas ni crear merge.

## 2. Evolución del esquema y compatibilidad

- [x] 2.1 En RED, extender las pruebas de migración con turnos sintéticos anteriores a C-07; luego agregar en una revisión incremental los campos faltantes de turno y retirar el default SQL de tiempo heredado. Verificar upgrade conservando identificadores/intervalos, ciclo inicial 1, desconocidos históricos sin actores inventados y fechas nuevas desde la aplicación (core-data-models).
- [x] 2.2 Crear turno_historial con los campos, acciones, estados e índices de KB 04; verificar mediante integración hechos válidos, rechazo de referencia inexistente y conservación de registros anteriores al agregar uno nuevo. El repositorio solo ofrecerá inserción y lectura (RN-21).
- [x] 2.3 Añadir referencias obligatorias faltantes de turno y las FK de token_usuario.turno_id y notificacion.turno_id. Actualizar en RED el test existente que exige ausencia de FK; verificar aceptación de nulos para correos/tokens de cuenta, rechazo de referencias inexistentes y preservación de restricciones de reclamación de C-05. No añadir ciclo de notificación de C-15.
- [x] 2.4 Verificar exclusión única y operativa después de upgrade: SQLSTATE real `23P01`, nombre de restricción y expresión de rango ante inserción directa solapada. Preservar el DDL manual de C-00 y btree_gist; si requiere modificación, escribirla a mano. Confirmar SU-39 solo con ejecución satisfactoria, no por inspección del test (ESC-01/05).
- [x] 2.5 Probar upgrade desde el head previo y downgrade/upgrade en base descartable sin operaciones contra datos reales; verificar conservación de filas en upgrade, límites destructivos del downgrade y un solo head. Documentar el procedimiento y sus límites junto al cambio de migración en README, sin ejecutar restauraciones sobre un entorno con datos.

## 3. Repositorios y límite transaccional

- [x] 3.1 Extender la unidad de trabajo existente para turno e historial; verificar con PostgreSQL que cada uso obtiene su sesión propia, mantiene expire_on_commit=False y confirma operación e historial juntos. Probar cierre de recursos al terminar y reversión ante error del cuerpo, flush y commit (core-data-models; diseño §1/4).
- [x] 3.2 Reutilizar la traducción selectiva de exclusión a HorarioOcupado y cubrir el cierre transaccional antes del éxito HTTP. Verificar que un solapamiento llega como error de dominio, otra violación de integridad no se transforma en horario ocupado y la sesión fallida se revierte/cierra sin persistencia parcial (ESC-01/14).
- [x] 3.3 Agregar actualización del mismo turno con las condiciones de estado/ciclo/horario descritas en diseño; verificar actualización exitosa y cero filas por lectura obsoleta como conflicto 409, sin historial parcial. No fijar ganador, reintentos ni prioridad para carreras adicionales sin contrato (RN-37; KB 11).

## 4. Creación y validaciones de reserva

- [x] 4.1 Integrar Principal, RBAC y acceso.autorizar en la creación por Recepción/Administrador; verificar rol permitido/denegado, recurso de otro consultorio como inexistente y ausencia de consultorio_id provisto por cliente. No abrir la reserva pública de C-09 (appointment-booking; RN-55).
- [x] 4.2 Implementar validación pura de intervalo completo en un único bloque, grilla anclada y excepciones globales/propias; probar bordes válidos, inicio 09:07, fin fuera de bloque, pausa, bloqueo parcial/total y zona equivalente. Verificar unidades y persistencia/API sin cambios ante rechazo (ESC-06; RN-14/RN-64).
- [x] 4.3 Integrar duración de catálogo y ajuste del personal; probar catálogo 30/60, ajuste 45 con grilla 15, rechazo de ajuste 20/cero/negativo, y catálogo 20 sin redondeo. Verificar fin calculado y conservación de turnos existentes tras cambiar el catálogo (ESC-07; RN-13/RN-15/RN-64).
- [x] 4.4 Asignar estado inicial y trazabilidad mediante Reloj: probar 47:59 h, 48 h y 48:01 h, confirmación manual y ficha sin cuenta. Verificar pendiente/confirmado según RN-23/RN-29 y que el historial distinga confirmación por persona de asignación temporal (ESC-09/13).
- [x] 4.5 Verificar creación por personal a 61 días y tercer turno activo del paciente sin aplicar límites de C-09; mantener las validaciones de horario y solapamiento. Cubrir éxito y rechazo por horario inválido para demostrar que la excepción de límites no omite otras reglas (ESC-13; RN-64 e).
- [x] 4.6 Probar con PostgreSQL regulares en coincidencia exacta, parciales por ambos extremos, contención en ambas direcciones y contigüidad; incluir todos los estados que ocupan/liberan y controles de otro profesional/consultorio. Verificar filas e historial finales y rechazo aplicativo de regular sobre sobreturno activo preparado por fixture (ESC-01/02/03/05; RN-17/RN-22).
- [x] 4.7 Forzar dos reservas regulares concurrentes con sesiones/conexiones independientes y sincronización antes de escribir; permitir el commit del ganador mientras la otra escritura espera. Verificar exactamente un turno con su historial, un conflicto y controles sin conflicto donde ambas persisten; no usar sleeps ni compartir AsyncSession (ESC-04; RN-24).
- [x] 4.8 Exponer POST /api/v1/turnos con entrada estricta y respuesta mínima; verificar éxito, 422 para extras/fin/consultorio_id, 404 para referencias ajenas, y una carrera de dos solicitudes autorizadas con un éxito y un 409. Documentar payload, respuestas y restricción de alta por personal en OpenAPI/README junto con estas pruebas.

## 5. Reprogramación, transiciones e historial

- [x] 5.1 Implementar reprogramación atómica sobre la misma fila, conservando duración ajustada y permitiendo ajuste explícito autorizado. Verificar identificador estable, movimiento sin conflicto consigo mismo y destino contra regular/sobreturno con 409 y original intacto, incluidos ciclo, marca e historial (ESC-08; RN-37/RN-64).
- [x] 5.2 Integrar reinicio del ciclo en reprogramación: probar marca previa, incremento único y destinos a 47:59 h, 48 h y 48:01 h. Verificar estado derivado, marca nula y motivo de RN-29 en historia; en fallo conservar todos los valores previos (ESC-09; RN-29/RN-32).
- [x] 5.3 Implementar cancelación con motivo por personal y confirmación manual de pendiente; verificar actor/fecha/estados, hueco liberado tras cancelar y rechazo 403 de confirmación de liberado o cancelación de estado no modificable, sin historia adicional (ESC-10; RN-19/RN-21/RN-30/RN-36).
- [x] 5.4 Implementar liberación manual según modo/marca: verificar éxito en modo manual sin marca y automático con marca, rechazo 403 en automático sin marca y en estado no pendiente, junto con actor/fecha e historial atómicos (ESC-10; RN-60).
- [x] 5.5 Integrar atendido/ausente con la política temporal confirmada ahora >= inicio; probar para Profesional propio, Recepción y Administrador a inicio menos un segundo, exactamente inicio e inicio más un segundo, en pendiente y confirmado. Verificar 403 antes, éxito exacto/después y estado/historial juntos; denegar rol, agenda o estado inválidos (ESC-11; criterio confirmado en design.md).
- [x] 5.6 Implementar corrección ausente a atendido por Recepción/Administrador, distinguiendo accion corregir; verificar éxito con historia anterior intacta, rechazo del Profesional y estado atendido inmutable ante mover/cancelar/corregir de nuevo (RN-18/RN-19/RN-21).
- [x] 5.7 Preparar el puerto de planificación de hitos de C-07 y su implementación sin efectos, conservando el límite transaccional para C-15/C-16; verificar invocación en crear/reprogramar y rollback ante una falla controlada del colaborador. No implementar SMTP, omisión de hitos, barrido ni WhatsApp; documentar este contrato y sus límites junto al puerto.
- [x] 5.8 Exponer PATCH y las acciones POST de turno, incluida corrección mediante atendido; verificar entrada estricta, políticas centralizadas, errores 403/404/409/422 aplicables y fallo de historial que revierte la operación. Documentar rutas, corrección y criterio >= en OpenAPI/README (appointment-lifecycle; ESC-10/11/14).

## 6. Lecturas autorizadas e integración de agenda

- [x] 6.1 Corregir el rechazo ABAC de turno ajeno por identificador a 404, manteniendo agenda ajena del mismo consultorio en 403; probar consulta y operaciones de turno con política pura y API, sin ampliar permisos de rol o titularidad (delta attribute-based-access-control; ESC-12).
- [x] 6.2 Agregar listado/detalle/historial de turnos con repositorios acotados; verificar Recepción/Administrador en su consultorio, Profesional solo en su agenda, recurso ajeno 404 y lista sin fugas entre consultorios. Cubrir historial existente y vacío (appointment-agenda).
- [x] 6.3 Agregar agenda por profesional y fecha local, ordenada por inicio; verificar día local frente a UTC, datos mínimos de paciente/prestación/estado y marca de sobreturno con fixture. Probar propia permitida, colega 403 y profesional de otro consultorio 404 (US-026; appointment-agenda).
- [x] 6.4 Agregar GET /pacientes/{id}/turnos y el adaptador de búsqueda por agenda previsto para C-08; verificar ficha sin cuenta con turnos pasados/futuros, denegación 404 fuera de alcance y Profesional limitado a sus turnos. No crear ni editar fichas de C-08.
- [x] 6.5 Integrar y probar el bloqueo de C-06 contra turnos C-07: con afectados devuelve lista y conserva bloqueo sin guardar y turnos intactos; sin afectados permite guardarlo. Probar alcance global/propio y documentar el comportamiento; no prometer resolver carreras simultáneas con altas sin decisión adicional (ESC-15; RN-16).
- [x] 6.6 Verificar minimización de respuestas y logs de todas las lecturas y rechazos: sin DNI, contacto, obra social ni cuenta innecesarios; comprobar ausencia de rutas de escritura/borrado de historial. Documentar filtros de acceso y campos operativos junto con las lecturas (RN-54/RN-58; appointment-agenda).

## 7. Verificación de integración del change

- [x] 7.1 Ejecutar desde backend `uv run pytest -m "not integration"` y `uv run pytest -m integration` con PostgreSQL real descartable y servicios de prueba existentes requeridos por la suite; verificar ausencia de fallos u omisiones no justificadas y conservar la evidencia del ciclo TDD por tarea. No atribuir ejecución a esta preparación documental.
- [x] 7.2 Verificar `uv run alembic heads`, upgrade limpio y upgrade con fixtures de legado, y comprobar extremo único, exclusión y FK tras todas las modificaciones. Contrastar resultados con core-data-models y los escenarios ESC-01 a ESC-15, sin datos reales.
- [x] 7.3 Revisar trazabilidad de cada escenario de los cinco deltas a las pruebas entregadas, OpenAPI y documentación de su grupo; repetir validación estricta con `openspec validate c-07-turnos-core --strict --no-interactive` y comprobar que no se incluyeron UI, endpoints ni servicios de changes futuros. Reportar diferencias y riesgos residuales antes de cualquier solicitud de cierre.

Archivar el change, sincronizar specs principales y marcar C-07 finalizado no forman parte del alcance de apply autorizado.

## Evidencia del ciclo TDD

Ejecución sobre una copia Linux descartable del checkout de Windows, con scripts en LF conforme a `.gitattributes`; PostgreSQL 17 y Mailpit reales, datos sintéticos. Los conteos siguientes corresponden a grupos de ejecución compartidos por varias tareas; no son pruebas exclusivas por fila. U = unidad; I = integración con PostgreSQL; API = HTTP contra la aplicación y PostgreSQL. No se atribuye RED a verificaciones de comportamiento ya existente sin cambios productivos.

Baseline inicial: 272 U y 41 I. Se autorizó corregir las fixtures de agenda, personal y prestaciones para inyectar `get_reloj`; antes emitían JWT con reloj fijo y los validaban con el reloj real. RED: 6 fallos de agenda y 10 de personal/prestaciones; GREEN: 6 y 11 respectivamente. La primera suite completa detectó el mismo defecto en la fixture de configuración de consultorio: 544 I verdes y 14 fallos 401; con la misma reparación autorizada, ese archivo pasó 26/26 y la suite completa 558/558. No se cambió auth de producción. Los fallos de bash/CRLF de Windows se resolvieron sólo en la copia Linux.

| Tarea | Archivo de prueba o comprobación | Capa | Safety Net | RED ejecutado | GREEN | TRIANGULATE | REFACTOR |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1.1 | OpenSpec status/instructions, skills locales | Preparación | Estado CLI | N/A | Autorización y alcance verificados | No UI; umbral confirmado | N/A |
| 1.2 | Suite existente y fixtures de API | U/I | 272 U + 41 I | Fallos previos de reloj reproducidos | Baseline 313 verdes tras fixes autorizados | Fixtures de personal/prestaciones 11 verdes | Sin auth productiva |
| 1.3 | `alembic heads` | Migraciones | Head previo | N/A | `0007_agenda_config` único antes de revisión | Cadena incremental conservada | Sin merge |
| 2.1 | `test_c07_migration.py` | I | 27 migración/account | Columna y atributos operativos inexistentes | Grupo final 103 verdes | Dos estados de legado, SQL y ORM | Verde |
| 2.2 | `test_c07_migration.py`, `test_c07_repositories.py` | I | 27 existentes | Modelo inexistente; hechos inválidos aceptados | Grupo esquema 103 verdes | FK, acciones, estados, índices y append | Verde |
| 2.3 | `test_c07_migration.py`, `test_account_models.py` | I | 27 existentes | Nuevas pruebas FK aceptaban referencias inválidas | Grupo esquema 103 verdes | Nulos/válidas/inválidas y restricciones previas | Verde; desviación indicada abajo |
| 2.4 | `test_c07_migration.py`, `test_migracion.py` | I | Exclusión C-00 existente | Verificación existente, sin recrear DDL | Grupo esquema 103 verdes | `23P01`, nombre, rango `[)`, única exclusión y filas | DDL preservado |
| 2.5 | Pruebas de migraciones y single head | I/U | 27 existentes | Regresión de nombres de checks en downgrade | Grupo esquema 103 verdes | Upgrade legado, roundtrip y abortos por huérfanos | Corregida y verde |
| 3.1 | `test_c07_transaction.py`, `test_c07_repositories.py` | I | UoW existente | Commit cerraba sin rollback explícito; historial inexistente | 13 verdes | Cuerpo, flush, commit, éxito, cierre y sesiones propias | Puertos declarados; verde |
| 3.2 | `test_c07_repository_updates.py`, `test_c07_booking.py` | I/API | 13 transacción | Exclusión de update/commit sin traducir | Repo 22 + dos errores tardíos API verdes | Otra FK conserva error de integridad; cero persistencia parcial | Verde |
| 3.3 | `test_c07_repository_updates.py`, `test_c07_reschedule.py` | I/API | 13 transacción | Métodos inexistentes | Repo 22 verdes | Cinco atributos obsoletos; HTTP 409 sin historia | Verde |
| 4.1 | `test_c07_booking.py` | API | Baseline 313 | Endpoint 404; referencia ajena aceptada/500 | Grupo alta 47 verdes | Roles, Principal, extras y referencias 404 | Verde |
| 4.2 | `test_reserva.py`, `test_c07_booking.py` | U/API | 88 políticas | Módulo inexistente; API aceptaba horarios inválidos | 22 intervalos U; grupo API 31 verdes | Bordes, pausa, grilla, bloqueos, zona equivalente; rechazo sin filas | Verde |
| 4.3 | Mismos archivos | U/API | 22 intervalos | Función ausente; ajuste 45 rechazado | Grupo API 38 verdes | 30/60, ajuste 45, rechazos 20/0/-1, catálogo 20 y cambio posterior | Verde |
| 4.4 | Mismos archivos | U/API | Grupo API 38 | Confirmación manual no aceptada | Grupo API 42 verdes | 47:59/48/48:01, ficha sin cuenta y motivos distintos | Verde |
| 4.5 | `test_c07_booking.py` | API | Grupo API 42 | Comportamiento existente, sin código nuevo | Grupo API 44 verdes | Tercer activo a 61 días y rechazo por grilla | Sin cambios productivos |
| 4.6 | `test_c07_conflicts.py` | API/I | Grupo API 44 | 21 fallos: conflictos 500 y sobreturno aceptado | Grupo conflictos 36 verdes | Cinco intersecciones × seis estados, contiguos y controles | Verde |
| 4.7 | `test_c07_conflicts.py` | API/I | Matriz anterior | Garantía de exclusión existente | Tres carreras/control verdes | Barrera antes de escribir; dos sesiones/PID; un ganador o dos controles | Sin sleeps |
| 4.8 | `test_c07_booking.py`, `test_c07_conflicts.py` | API | Grupos alta/conflictos | Contrato OpenAPI sin errores documentados | Grupo conjunto 81 verdes antes de checks tardíos | Payload estricto, respuestas mínimas, carrera 201/409 | README/OpenAPI; verde |
| 5.1 | `test_c07_reschedule.py` | API/I | Alta y repos verdes | PATCH 405 | Grupo PATCH 32 verdes | Misma fila, duración, sí mismo, regular/sobreturno y rollback exacto | Verde |
| 5.2 | Mismo archivo | API/I | Tres PATCH verdes | Implementado con primer RED PATCH | Grupo PATCH 32 verdes | Marca/ciclo, tres bordes temporales y fallo intacto | Verde |
| 5.3 | `test_c07_lifecycle.py` | API/I | 42 altas | Confirmar/cancelar 404 | Grupo ciclo 94 verdes | Actor/fecha/motivo, finales 403 y hueco libre | Verde |
| 5.4 | Mismo archivo | API/I | 18 ciclo | Cinco casos liberar 404 | Grupo ciclo 94 verdes | Manual sin marca, auto con marca, rechazos y atomicidad | Verde |
| 5.5 | Mismo archivo, `test_matriz_abac.py` | U/API | 23 ciclo | Ausente/atendido 404 | Grupo ciclo 94 verdes | 36 combinaciones de rol/acción/estado/instante; permisos restantes | Verde |
| 5.6 | `test_c07_lifecycle.py`, `test_c07_reschedule.py` | API/I | 60 ciclo | Corrección de personal recibía 403 | Grupo ciclo 94 verdes | Historia previa intacta; profesional/repetición/cancelar/mover atendido denegados | Verde |
| 5.7 | `test_c07_hitos.py` | API/I | PATCH/alta verdes | Inyección e invocaciones inexistentes | Tres verdes | Crear/mover, misma transacción invisible antes de commit, rollback de colaborador | Adaptador sin efectos |
| 5.8 | Pruebas de lifecycle/reschedule/hitos | API/I | Grupos anteriores | Cinco conflictos stale 500; OpenAPI PATCH incompleto | Grupo mutadores 125 verdes; PATCH con overflow 32 verdes | 403/404/409/422, extras y cinco fallos de historia; overflow POST/PATCH | README/OpenAPI; verde |
| 6.1 | `test_acceso_coordinador.py`, `test_matriz_abac.py`, API C-07 | U/API | 88 políticas | Turno ajeno devolvía 403 | 129 ABAC + lecturas/acciones verdes | Turno ajeno 404; agenda ajena 403, sin ampliar roles | Verde |
| 6.2 | `test_c07_agenda.py` | API/I | 43 lecturas/alta/health | GET 404/405; histórico inactivo 404 en review | Grupo histórico 123 verdes | Vacío/múltiple, roles, aislamiento e inactivos | Verde |
| 6.3 | Mismo archivo | API/I | Lecturas anteriores | Agenda 404; perfil inactivo histórico 404 | Grupo histórico 123 verdes | Día local/UTC, orden, sobreturno, colega 403 y externo 404 | Verde |
| 6.4 | Mismo archivo | API/I | 29 lecturas | Ficha-turnos 404 | Grupo histórico 123 verdes | Sin cuenta, pasado/futuro, ficha compartida, sin agenda y vacío | Verde |
| 6.5 | Mismo archivo | API/I | Lecturas anteriores | Comportamiento C-06 existente | Grupo lecturas 41 verdes | Global/propio: afectados 409 sin guardar/cambiar; libre 201 | C-06 sin cambios |
| 6.6 | Mismo archivo | API/I | Lecturas anteriores | Verificación del filtrado existente | Grupo histórico 123 verdes | Cinco lecturas, sentinelas privados, logs y métodos de historia 405 | Centralización de rechazo; verde |
| 7.1 | Suite backend completa | U/I | Grupos anteriores | Fixture antigua: 14 respuestas 401, mismo defecto de reloj | **348 U (5.86 s) + 558 I (118.74 s), 906 en total** | Cero fallos u omisiones; PostgreSQL 17 y Mailpit reales | Fixture corregida sin auth productiva; verde |
| 7.2 | Migraciones/head/exclusión/FK | I/U | Grupo esquema | N/A: verificación | Head único `0008_turnos_core`; script single head aprobado | Limpio/legado/roundtrip, exclusión y FK cubiertos en 103 verdes y en la suite completa | Verificado |
| 7.3 | Matriz ESC, OpenAPI, documentación, OpenSpec strict | Revisión | Grupos anteriores | N/A: verificación | OpenSpec strict válido; diff check limpio | ESC-01 a ESC-15, cinco deltas, OpenAPI/README y alcance sin UI ni servicios futuros | Revisión independiente y riesgos documentados |

Desviación de orden en 2.3: los nuevos tests de referencias estuvieron en RED antes de agregar las FK; el test antiguo que exigía ausencia de FK se actualizó después. No se atribuye un RED previo a ese test antiguo. La revisión independiente detectó RN-15/US-008 (lecturas de referencias inactivas), corregido con RED y 123 verdes, y un desbordamiento de intervalo (cuatro POST/PATCH respondían 500), corregido a 422 sin inventar un máximo de negocio y con 32 PATCH verdes.

## Trazabilidad de escenarios y deltas

Los nombres siguientes apuntan a pruebas de comportamiento ejecutadas; los parámetros cubren las variantes descritas en `design.md`. Los cinco deltas se mantienen en este change: no se sincronizaron las specs principales ni se archivó C-07.

| Escenario | Pruebas principales | Contrato comprobado |
| --- | --- | --- |
| ESC-01 | `test_c07_conflicts.py::test_overlap_matrix_preserves_rows_and_history_on_rejection`; `test_c07_migration.py::test_exclusion_unica_preserva_rango_y_codigo_real_despues_de_upgrade` | Coincidencia, parciales y contenciones; 409/`23P01` sin persistencia parcial. |
| ESC-02 | `test_c07_conflicts.py::test_adjacent_intervals_do_not_overlap` | Contigüidad en ambos extremos de `[)`. |
| ESC-03 | `test_c07_conflicts.py::test_concurrent_requests_use_independent_sessions_and_commit_one_winner_without_partial_history`; pruebas C-00 de exclusión | Controles de profesional y consultorio; dos reservas compatibles persisten. |
| ESC-04 | Mismo test de concurrencia | Barrera antes de escritura, sesiones/conexiones distintas, un 201 y un 409, un turno e historial. |
| ESC-05 | Matriz de `test_c07_conflicts.py` y prueba de exclusión de migración | Cuatro estados ocupan; cancelado/liberado dejan reservar; sobreturno existente no admite regular encima. |
| ESC-06 | `test_reserva.py`; `test_whole_interval_fits_one_block_and_anchored_grid`; `test_global_and_own_blocks_reject_partial_and_full_intersection` | Bloque completo, grilla, pausas, excepciones y zona; rechazo 422 sin turno ni historia. |
| ESC-07 | `test_catalog_duration_and_staff_adjustment_without_rounding` | Catálogo 30/60/20, ajuste 45 y rechazos, cambio posterior del catálogo conserva el intervalo. |
| ESC-08 | `test_reschedule_keeps_id_and_adjusted_duration_and_restarts_cycle`; `test_failed_reschedule_preserves_every_original_value_and_history` | Misma fila, duración conservada/ajustada, sí mismo, destino regular/sobreturno y rollback exacto. |
| ESC-09 | `test_initial_state_uses_exact_clock_threshold_and_distinguishes_manual_confirmation`; `test_reschedule_exact_confirmation_threshold_resets_mark_once` | 47:59/48/48:01, motivo temporal/manual, ciclo y marca. |
| ESC-10 | `test_c07_lifecycle.py` | Confirmar, cancelar, liberar; modo/marca/estado, actor/fecha/hueco e historia atómica. |
| ESC-11 | Matriz temporal de `test_c07_lifecycle.py` y `test_matriz_abac.py` | 36 combinaciones de tres roles, dos acciones, dos estados y antes/exacto/después; permisos restantes. |
| ESC-12 | Pruebas ABAC y `test_c07_agenda.py`/`test_c07_lifecycle.py` | Turno ajeno por id 404; agenda de colega 403; otro consultorio 404. |
| ESC-13 | `test_staff_creates_turn_for_unlinked_patient_with_atomic_history`; `test_staff_can_book_third_active_turn_at_61_days_but_still_requires_valid_grid` | Ficha sin cuenta, tercer activo y 61 días, conservando horario y solapamiento. |
| ESC-14 | `test_c07_repositories.py`; `test_failed_reschedule_preserves_every_original_value_and_history`; fallos de historia en cinco acciones | Rollback de estado/intervalo/ciclo/marca/historia, errores de cuerpo/flush/commit y del colaborador. |
| ESC-15 | `test_c07_agenda.py::test_bloqueos_c06_informan_afectados_sin_guardar_y_admiten_hueco_libre` | Bloqueo global/propio: afectados 409 sin guardar ni cambiar turnos; hueco libre 201. |

| Delta | Cobertura y documentación |
| --- | --- |
| `appointment-booking` | `test_reserva.py`, `test_c07_booking.py`, `test_c07_conflicts.py`; POST documentado en OpenAPI y README. |
| `core-data-models` | `test_c07_migration.py`, `test_c07_transaction.py`, `test_c07_repositories.py`, `test_c07_repository_updates.py`; migración incremental, FK, historial, tiempos y atomicidad, procedimiento y límites en README. |
| `appointment-lifecycle` | `test_c07_reschedule.py`, `test_c07_lifecycle.py`, `test_c07_hitos.py`; PATCH y cinco acciones documentados, corrección diferenciada y umbral `>=`. |
| `attribute-based-access-control` | `test_acceso_coordinador.py`, `test_matriz_abac.py` y API de lecturas/acciones; ningún permiso nuevo para roles o titularidad. |
| `appointment-agenda` | `test_c07_agenda.py`; cinco rutas GET documentadas, fecha local, fichas sin cuenta, historial inmutable por interfaz, minimización, aislamiento e históricos tras desactivar referencias. |

Revisión de alcance: sin UI, reserva pública, alta de sobreturnos, CRUD de fichas, SMTP de turnos, barrido, WhatsApp ni despliegue nuevos. El puerto de hitos de C-07 permanece sin efectos. Riesgos conservados: carrera regular/sobreturno y alta/bloqueo simultáneos; downgrade destructivo de los campos e historial nuevos, probado sólo en bases descartables. No se resolvieron nuevos contratos de ganador/reintento entre operaciones simultáneas sobre el mismo turno.
