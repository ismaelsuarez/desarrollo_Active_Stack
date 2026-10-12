# Auditoría adversarial de la base del proyecto

Fecha: 2026-10-09. Objetivo: commit `44d3cdc` (rama `docs/skills-usage-notes`). Método: dos jueces independientes, a ciegas y de solo lectura, con el mismo alcance y criterios. No hay código de aplicación todavía; se auditaron los artefactos de planificación.

Alcance: `knowledge-base/` (13 archivos), `CHANGES.md`, `AGENTS.md` y `CLAUDE.md`, `openspec/changes/c-01-foundation-setup/`, `discovery/exploracion-tecnica.md`, `discovery/evaluacion-skills.md`, `README.md` y el estado del orquestador.

Estado: rondas 1 y 2 aplicadas el 2026-10-11, sin commitear y rejuzgadas (ver "Rejuicio acotado de la ronda 1" y "Rejuicio acotado de la ronda 2"). RK-01 a RK-11 corregidos en la ronda 3 y rejuzgados (ver "Rejuicio acotado de la ronda 3"). RL-01 a RL-10 corregidos en la ronda 4 y rejuzgados (ver "Rejuicio acotado de la ronda 4"). RM-01 a RM-04 corregidos en la ronda 5 y rejuzgados; R5-01 y R5-02 corregidos en la ronda 6 y rejuzgados: un juez sin hallazgos y el otro con una sugerencia preexistente (R6-01). JD-06 a JD-31 y las sugerencias originales siguen sin corregir. El responsable autorizó las rondas que hagan falta. La etapa de implementación sigue en pausa.

## Cómo leer el libro

- **Confirmado severo**: los dos jueces lo reportan como crítico.
- **Severidad dividida**: los dos jueces ven el mismo defecto; uno lo califica crítico y el otro advertencia.
- **Sospecha severa**: un solo juez lo califica crítico.
- **Confirmado**: los dos jueces lo reportan, sin calificarlo crítico.
- **Un juez**: lo reporta uno solo.

Los hechos externos usados por los jueces (bloqueo de cookies de terceros en Safari, cómputo mínimo de Neon, rechazo de `sslmode` por asyncpg, feriado del 2026-10-12) no se verificaron contra fuentes primarias.

## Confirmado severo

| ID | Hallazgo | Ubicación |
|----|----------|-----------|
| JD-01 | El candado del barrido se contradice entre archivos. La regla dura 9 prohíbe los candados de sesión y exige `pg_try_advisory_xact_lock` o `SKIP LOCKED`, pero la KB 08, 09 y 12 y C-15 siguen especificando `pg_try_advisory_lock`, que es de sesión y no funciona en el pooler de Neon. Además, un candado de transacción dura lo que dura la transacción, y C-15 pide transacciones cortas por fila: el test "dos barridos simultáneos, solo uno procesa" no se puede cumplir como está escrito. | `CHANGES.md:507,515`; `knowledge-base/08:127`; `09:99,275`; `12:34,255`; `AGENTS.md:125` |

## Severidad dividida

| ID | Hallazgo | Ubicación |
|----|----------|-----------|
| JD-02 | La regla dura 1 exige leer `consultorio_id` solo del `Principal` del token, pero login, registro, verificación, recuperación, confirmación por enlace y todo `/publico/*` no tienen token. Los usuarios son únicos por `(consultorio_id, nombre_usuario)`, así que el login necesita un consultorio y ningún documento define de dónde sale. Bloquea el diseño de C-03, C-05 y C-09. | `AGENTS.md:117`; `knowledge-base/04:213`; `03:60-71`; `CHANGES.md:21,243,381` |
| JD-03 | La liberación automática selecciona los turnos solo por estado `pendiente` y por tiempo. No exige que la solicitud de confirmación se haya enviado. Si el correo falla, está bloqueado o el barrido se retrasa, se liberan turnos de pacientes que nunca fueron avisados, y también turnos cuyo horario ya pasó. | `knowledge-base/05:74,76,78`; `07:181,209`; `CHANGES.md:544` |

## Sospecha severa

| ID | Hallazgo | Ubicación |
|----|----------|-----------|
| JD-04 | El registro de un paciente cuyo DNI ya cargó Recepción no tiene comportamiento implementable: `UNIQUE (consultorio_id, dni)` impide la segunda ficha y RN-49 prohíbe vincular automáticamente. Es el caso normal de los pacientes que el consultorio ya conoce. Q-05 es de prioridad Alta y los changes la declaran "no frena". El otro juez reporta el mismo punto como oráculo de pertenencia y bloqueo del DNI de un tercero. | `knowledge-base/04:277-278`; `05:108`; `07:50,79`; `CHANGES.md:287,368` |

## Confirmado (los dos jueces)

| ID | Hallazgo | Ubicación |
|----|----------|-----------|
| JD-05 | La idempotencia del despacho de notificaciones no tiene mecanismo: el enum de `notificacion.estado` no tiene un estado intermedio y no se define a qué estado pasa la fila al reclamarla. Marcar antes del envío pierde correos; marcar después los duplica. | `CHANGES.md:293,296,537`; `knowledge-base/04:350` |
| JD-06 | Orden de migraciones imposible: `token_usuario` (C-02) y `notificacion` (C-05) tienen `turno_id` hacia `turno`, que recién se crea en C-07. Ningún change dice quién agrega esa clave foránea. | `CHANGES.md:220,293,338`; `knowledge-base/04:221,350` |
| JD-07 | `turno_es_modificable` solo es falsa para `atendido`, `cancelado` y `liberado`, así que un turno `ausente` se puede cancelar o reprogramar. Contradice RN-19 y falsea el indicador de ausentismo. C-04 no lo prueba. | `knowledge-base/11:46-47,114-115`; `05:63,84`; `CHANGES.md:272` |
| JD-08 | Las preguntas de prioridad Alta no tienen puerta de bloqueo: `AGENTS.md` dice resolverlas antes del change que bloquean y `CHANGES.md` las deja "a fijar en el diseño" (Q-03, Q-04, Q-05, Q-06). Q-26, Q-27 y Q-29 están en prioridad Media aunque bloquean C-01, el barrido y el stack completo. | `AGENTS.md:50`; `CHANGES.md:368,389,544`; `knowledge-base/10:56,57,59` |
| JD-09 | El barrido cada 5 minutos mantiene activo el cómputo de Neon, que se suspende a los 5 minutos. Con las 100 CU-h del plan gratuito la cuota podría agotarse a mitad de mes. No hay plan alternativo. | `knowledge-base/10:57`; `12:42,58`; `CHANGES.md:518,537` |
| JD-10 | La cookie de renovación con `SameSite=None` entre dominios distintos es de terceros y muchos navegadores móviles la bloquean. La alternativa de dominio común contradice el presupuesto cero. No se evaluó un proxy del mismo origen. | `knowledge-base/12:224`; `09:282`; `CHANGES.md:254,486` |
| JD-11 | Una sola `DATABASE_URL` para la app, Alembic y el respaldo. Lo verificado dice que migraciones y `pg_dump` van por la URL directa de Neon. La regla dura 10 nombra `NullPool` como alternativa suficiente y la fuente exige además nombres de sentencia únicos. | `knowledge-base/08:168`; `discovery/evaluacion-skills.md:48-49`; `openspec/.../design.md:48`; `AGENTS.md:126` |
| JD-12 | La revocación de sesiones solo alcanza a los refresh tokens. El access token sigue válido hasta vencer y su duración está "a definir": un usuario desactivado conserva acceso. | `CHANGES.md:243-246`; `knowledge-base/05:30`; `08:173` |
| JD-13 | El endpoint `POST /turnos/{id}/sobreturno` es ambiguo: el turno solapado se rechazó con 409 y no existe `{id}`. No se define el cuerpo. | `CHANGES.md:403`; `knowledge-base/07:240-255`; `04:335` |
| JD-14 | Credenciales de la base en C-01: `DATABASE_URL` es sensible pero llega por `env_file`, la contraseña queda duplicada con el secreto `postgres_password`, y `migrate` exige `JWT_SECRET_KEY` solo porque `Settings` lo pide. | `openspec/.../specs/local-environment/spec.md:66-80`; `design.md:39,48`; `knowledge-base/12:105-111` |
| JD-15 | La spec de logging exige ocultar cinco variables sensibles y el diseño solo conoce dos en C-01. El escenario de `SMTP_PASSWORD` no puede pasar. | `openspec/.../specs/structured-logging/spec.md:37`; `design.md:39,42` |
| JD-16 | La viabilidad del plan está sobrestimada: cinco días de trabajo desde un viernes, changes muy grandes por sesión, y 10 de 20 changes con gobernanza crítica o alta que exige aprobación humana no contada. La frase "deja margen" no tiene cálculo. | `CHANGES.md:26,145,149-166,228,253,274,298,347` |
| JD-17 | El disparador externo se evalúa solo por su intervalo mínimo. No se consideran las demoras ni la desactivación tras 60 días sin actividad de GitHub Actions. C-16 promete precisión de 5 minutos. | `knowledge-base/09:351`; `discovery/evaluacion-skills.md:50`; `CHANGES.md:537,622` |
| JD-18 | Ley 25.326: el registro público recolecta DNI, contacto y obra social sin aviso de privacidad ni consentimiento, y hay campos libres que pueden contener datos de salud. El checklist de publicación no tiene punto legal. | `knowledge-base/05:123`; `06:23-28`; `10:47`; `12:274-286` |
| JD-19 | Nombres de endpoint incoherentes: la confirmación por enlace tiene dos rutas distintas, y la salud figura como `/health` en el Compose de la KB 12 y como `/api/v1/health` en C-01. | `knowledge-base/03:71`; `CHANGES.md:538`; `12:130`; `openspec/.../design.md:33` |
| JD-20 | DD-01 fija Redis para lo asincrónico como restricción y el plan lo elimina junto con el proceso persistente. Solo se sostiene si la cátedra no exige el stack completo (Q-29, prioridad Media, sin responsable ni fecha). | `knowledge-base/09:12-16`; `AGENTS.md:12-24`; `10:59` |

## Un juez

| ID | Hallazgo | Ubicación |
|----|----------|-----------|
| JD-21 | La regla dura 11 exige rechazar campos no declarados y el test de C-03 exige que el `consultorio_id` enviado por el cliente se ignore. Son comportamientos opuestos. | `AGENTS.md:127`; `CHANGES.md:251` |
| JD-22 | RN-26 advierte la liberación en el recordatorio de 24 horas, y RN-29 dice que un turno reservado con menos de 48 horas no se libera. El paciente recibe una advertencia que nunca se cumple. | `knowledge-base/05:73,76`; `06:400` |
| JD-23 | El token de confirmación no está atado al ciclo de confirmación: un enlace anterior a una reprogramación puede confirmar el horario nuevo. | `CHANGES.md:533,538`; `knowledge-base/04:221`; `05:79` |
| JD-24 | El tope diario de 500 correos es compartido entre correos de cuenta y recordatorios, sin prioridad ni límite por origen. Un tercero puede agotarlo desde el registro público. | `CHANGES.md:294-296`; `knowledge-base/12:211` |
| JD-25 | El tipo de clave primaria queda abierto (`bigint` o UUID) aunque lo necesita la primera migración de C-02 y las rutas exponen identificadores. | `knowledge-base/04:184`; `02:99` |
| JD-26 | La unicidad de correo y usuario distingue mayúsculas, y el correo está duplicado en `usuario` y `paciente` sin regla de sincronización. | `knowledge-base/04:212-213,277` |
| JD-27 | Un rol por usuario y correo único impiden que el dueño del consultorio sea administrador y profesional a la vez. | `knowledge-base/04:212-213`; `09:160-164`; `10:44` |
| JD-28 | Fuga de existencia de cuentas en el login y bloqueo por cuenta sin origen: cualquiera puede bloquear al administrador. | `knowledge-base/07:103`; `05:34`; `CHANGES.md:245,247` |
| JD-29 | La configuración de C-01 falla en modo abierto: `APP_ENV` es `development` por defecto y `JWT_SECRET_KEY` no tiene longitud mínima. | `openspec/.../specs/runtime-configuration/spec.md:23,49-53` |
| JD-30 | El comportamiento principal de C-01 (`docker compose up` con `migrate` y `api` saludables) solo se verifica a mano. | `openspec/.../tasks.md:41-46` |
| JD-31 | La regla dura 2 prohíbe código sin test previo y C-01 marca tareas con código real como estructurales, sin excepción respaldada en `AGENTS.md`. | `AGENTS.md:118`; `openspec/.../tasks.md:3,29-30` |

## Sugerencias

- La tarea 8.2 de C-01 trata `README.md` como archivo nuevo y ya existe uno en `main`.
- "Si el plazo aprieta" afirma que ninguna opción toca las reglas de negocio, pero las opciones 4, 5 y 6 dejan sin cumplir RN-05, RN-40 y RN-52 a RN-54.
- Los códigos HTTP de rechazo de la KB 11 no coinciden con C-04, y el `Principal` no trae `profesional_id` ni `paciente_id`.
- RN-37 dice "reservar el nuevo horario antes de liberar el anterior" y "conservar el mismo turno": falta decidir si es una fila o dos.
- Huecos de integridad: `es_sobreturno` excluye la fila de la restricción sin exigir autorización, las claves foráneas no incluyen `consultorio_id`, los parámetros de horas no tienen restricción de orden.
- Enums nativos frente a `TEXT` con `CHECK`, y falta `naming_convention` de Alembic en C-02.
- Dos fuentes para la zona horaria, y el reloj simulado no controla los `now()` de SQL.
- Los enlaces de correo llevan el token en la query.
- La regla dura 12 cita SU-04, que es una suposición no confirmada. La regla 8 pide rebasar la migración y la skill de Alembic pide `alembic merge`.
- El estado del orquestador lista como recomendadas skills que la evaluación descartó.
- Decisiones de C-01 con riesgo posterior: `postgres:17-alpine` usa musl y Neon glibc, no hay archivo de bloqueo de dependencias de Python, el `downgrade` elimina la extensión.

## Decisiones del responsable (2026-10-11)

| ID | Decisión |
|----|----------|
| JD-01, JD-05 | Reclamo por fila: `SELECT ... FOR UPDATE SKIP LOCKED`, estado intermedio `enviando` con hora de reclamo, envío SMTP fuera de la transacción y reclamo de los vencidos. Entrega "al menos una vez". |
| JD-02 | En los flujos sin token, el servidor resuelve el consultorio activo desde su configuración. Los flujos por enlace lo toman de la fila del token. El cliente nunca lo envía. |
| JD-03 | La liberación automática exige que la solicitud de confirmación del ciclo actual esté `enviada` y que el turno no haya empezado. En otro caso queda "sin confirmar" para Recepción. |
| JD-04 | Cuenta con vínculo pendiente: no se crea una segunda ficha; Recepción vincula o rechaza. Resuelve Q-05. |

## Rejuicio acotado de la ronda 1

Fecha: 2026-10-11. Objetivo: el libro más el delta de correcciones sobre `44d3cdc` (14 archivos, 235 inserciones y 131 eliminaciones, sin commitear; sha256 del diff `778ff9d434d00069…`). Los dos jueces leyeron el delta completo. Ninguno reportó un hallazgo crítico. JD-01, JD-02, JD-03 y JD-05 quedan corregidos; JD-04 queda corregido con una fuga residual (RJ-03).

Hallazgos sobre el delta, ninguno corregido todavía:

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| RJ-01 | Los dos | Advertencia | El reclamo no tiene marca de vigencia: el resultado se escribe condicionado solo por estado. Si un envío tarda más que `NOTIFICATION_CLAIM_TTL_SECONDS` y otro barrido reclama la fila, el primero puede pisar el resultado del segundo. El reclamo de una fila `enviando` vencida tampoco revalida que el turno siga vigente. | `knowledge-base/04:372-387` |
| RJ-02 | Los dos | Advertencia | `marcado_sin_confirmar_en` no se limpia al reprogramar. Un turno marcado y luego reprogramado queda excluido de la liberación automática en su ciclo nuevo y sigue en la lista de Recepción. | `knowledge-base/07:192-193`; `05` RN-32 |
| RJ-03 | Los dos | Advertencia | La respuesta idéntica del registro no evita la fuga: quien se registra con el DNI de otra persona y verifica su propio correo distingue por el 403 al reservar si ese DNI ya era paciente. DD-19 lo admite como riesgo residual, pero RN-62, US-001 y C-05 lo presentan como resuelto. | `knowledge-base/05:113`; `07:88`; `09` DD-19 |
| RJ-04 | Los dos | Advertencia | Una solicitud `rechazada` es final y `UNIQUE (usuario_id)` impide otra: la cuenta queda sin ficha, sin poder reservar y sin camino de recuperación. | `knowledge-base/04:294-307`; `CHANGES.md` C-08 |
| RJ-05 | Los dos | Advertencia | RN-59 dice que todo `/publico/*` toma el consultorio de la configuración, pero la confirmación por enlace de C-16 es `POST /api/v1/publico/confirmar-turno` y debe tomarlo de la fila del token. La KB 03 nombra la misma ruta `POST /turnos/confirmar-por-enlace` (ver JD-19). | `CHANGES.md:540`; `knowledge-base/03:55`; `05` RN-59 |
| RJ-06 | Los dos | Advertencia | C-02 siembra el consultorio con el valor de `CONSULTORIO_ACTIVO_ID`, pero la variable la agrega C-03, que depende de C-02. Un juez agrega que C-03 pide probar verificación y restablecimiento, que se construyen en C-05. | `CHANGES.md:225,240-262` |
| RJ-07 | Los dos | Advertencia / sugerencia | La tabla de transiciones de `notificacion` no define el diferimiento por tope diario de correos: tras el reclamo, volver a `programada` solo existe por fallo y consume `intentos`. | `knowledge-base/04:375-387`; `CHANGES.md:298` |
| RJ-08 | Los dos | Sugerencia | `README.md` y `knowledge-base/README.md` siguen diciendo "RN-01 a RN-58". | `README.md:134`; `knowledge-base/README.md:13` |
| RJ-09 | Los dos | Sugerencia | Los indicadores operativos no miran las filas en `enviando`. | `CHANGES.md:515`; `knowledge-base/12` |
| RJ-10 | Un juez | Advertencia | El trabajo sobre `turno` (liberar, marcar y escribir el historial) no tiene reclamo. Marcar no es una transición de estado, así que dos barridos simultáneos pueden escribir dos filas de historial para el mismo turno. | `knowledge-base/07:192-193`; `08:121` |
| RJ-11 | Un juez | Sugerencia | La condición ABAC de `turno.liberar` pasó de "modo manual" a "marca sin confirmar": en modo manual Recepción ya no puede liberar antes de la marca, y un turno ya empezado recibe la marca y la acción de liberar. Nadie decidió ese cambio. | `knowledge-base/11:120` |
| RJ-12 | Un juez | Sugerencia | El recordatorio de 24 horas (RN-26) sigue advirtiendo una liberación que, con RN-60, puede no ocurrir. Relacionado con JD-22. | `knowledge-base/05:76` |
| RJ-13 | Un juez | Sugerencia | "Dos registros simultáneos con el mismo DNI nuevo" no es implementable en una sola transacción: la violación de `UNIQUE` la aborta. Falta indicar un punto de guardado o `ON CONFLICT DO NOTHING`. | `knowledge-base/07:87` |

Los jueces no cargaron las dos skills de referencia que se les pasaron; aplicaron los criterios desde el enunciado.

## Decisiones del responsable sobre el rejuicio (2026-10-11)

| ID | Decisión |
|----|----------|
| RJ-03 | Se acepta el riesgo residual y se acota: límite de registros por origen, estado visible solo con correo verificado y registro de cada solicitud. Los documentos no afirman que el registro no revela nada. |
| RJ-04 | Lo resuelve Recepción: correo al paciente al rechazar, y Recepción puede después vincular la cuenta a la ficha correcta o crearle una ficha. El paciente no reintenta solo. |
| Rondas | Sin tope de rondas de corrección y rejuicio para esta auditoría. |

Resueltos por el orquestador como consecuencia de lo decidido, informados al responsable: ruta única `POST /turnos/confirmar-por-enlace` (RJ-05), `CONSULTORIO_ACTIVO_ID` la agrega C-02 (RJ-06) y condición de `turno.liberar` (RJ-11).

## Rejuicio acotado de la ronda 2

Fecha: 2026-10-11. Objetivo: el libro más el delta de la ronda 2 (del estado posterior a la ronda 1 al árbol de trabajo; sha256 del diff `cb2a62f2f1eba85c…`). Los dos jueces leyeron el delta completo. Ninguno reportó un hallazgo crítico. Los dos dan por resueltos de forma coherente RJ-02, RJ-05, RJ-08, RJ-09, RJ-10, RJ-11, RJ-12 y RJ-13; RJ-01 y RJ-07 quedan resueltos en el diseño con los defectos RK-01, RK-02 y RK-08; RJ-03, RJ-04 y RJ-06 quedan parciales (RK-03 a RK-06).

Hallazgos sobre el delta de la ronda 2, ninguno corregido todavía:

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| RK-01 | Los dos | Advertencia | El `CHECK ((estado = 'enviando') = (reclamada_en IS NOT NULL))` choca con tres transiciones que salen de `enviando` (a `fallida` por fallo, a `omitida` y a `fallida` por reclamo vencido): la tabla no dice que limpien `reclamada_en`. | `knowledge-base/04:379,390-392` |
| RK-02 | Los dos | Advertencia | La validación de vigencia "turno cancelado, liberado o de otro ciclo: `omitida`" está escrita para todos los tipos de notificación. Leída así, los avisos de liberación y de cancelación o reprogramación por el personal, que existen justamente porque el turno ya cambió, nunca se envían. | `knowledge-base/04:386-387,391`; `05:124`; `CHANGES.md:296,510` |
| RK-03 | Los dos | Advertencia | RJ-04 parcial: "la cuenta nunca queda sin camino de recuperación" no se cumple si la ficha correcta ya tiene otra cuenta o está inactiva. Vincular responde 409, `POST /pacientes` responde 409 por DNI duplicado, y no existe desvincular ni reactivar. Un vínculo equivocado es final y expone la ficha. | `knowledge-base/04:303-305`; `05:113-117`; `CHANGES.md` C-08 |
| RK-04 | Los dos | Advertencia | Pruebas asignadas a changes que no pueden ejecutarlas: C-05 y C-08 prueban que "la cuenta reserva" (la reserva es de C-09), y C-07 prueba la lista "sin confirmar" (es de C-16). | `CHANGES.md:299,348,368` |
| RK-05 | Los dos | Advertencia | El correo `vinculacion_rechazada` se envía aunque el correo de la cuenta no esté verificado (SU-42). Contradice la medida de RN-62: el estado solo lo ve una cuenta verificada. Además manda correo del consultorio a una dirección que nadie probó controlar. | `knowledge-base/09:404`; `05:113`; `04:304` |
| RK-06 | Los dos | Advertencia / sugerencia | El límite de registros por origen, que es la cota principal de RJ-03, no es implementable como está: "origen" no está definido detrás de los proxies, y ninguna tabla guarda el origen. | `CHANGES.md:298`; `knowledge-base/08:149-152` |
| RK-07 | Los dos | Advertencia / sugerencia | Vincular solo condiciona el estado de la solicitud. Dos vínculos simultáneos sobre la misma ficha pasan la verificación y el segundo pisa `paciente.usuario_id`. Falta la escritura condicional sobre la ficha. | `knowledge-base/04:302-303` |
| RK-08 | Los dos | Sugerencia | El tope diario cuenta todas las filas `enviando`, incluso las vencidas, y con el tope alcanzado no se reclama nada: las vencidas no pueden pasar a `omitida` ni a `fallida` y mantienen el conteo en el tope. | `knowledge-base/04:397`; `12:211` |
| RK-09 | Un juez | Sugerencia | Un turno `pendiente` que ya empezó no se libera ni se marca, sigue en el conjunto candidato y cada barrido lo reevalúa. La actualización condicional tampoco tiene el predicado "no comenzó". | `knowledge-base/07:195-200`; `04:355` |
| RK-10 | Un juez | Sugerencia | Ningún change es dueño de la plantilla `vinculacion_rechazada` ni dispara su envío: C-08 programa la fila pero no depende de C-15. | `CHANGES.md:295-298,366-368` |
| RK-11 | Un juez | Sugerencia | C-02 vuelve obligatoria `CONSULTORIO_ACTIVO_ID` y solo nombra `.env.example`. Faltan los servicios de Compose de C-01, la integración continua y los fixtures de `Settings`. | `CHANGES.md:224` |

Los jueces tampoco cargaron en esta ronda las dos skills de referencia.

## Decisión del responsable sobre la ronda 2 (2026-10-11)

| ID | Decisión |
|----|----------|
| RK-03 | Recepción y Administrador pueden desvincular una cuenta de una ficha, con motivo obligatorio, registro y cierre de las sesiones de la cuenta. También pueden reactivar una ficha inactiva. |

## Rejuicio acotado de la ronda 3

Fecha: 2026-10-11. Objetivo: el libro más el delta de la ronda 3 (del estado posterior a la ronda 2 al árbol de trabajo; sha256 del diff `80e01e55659e320e…`). Los dos jueces leyeron el delta completo; ambos se interrumpieron por límite de uso y se reanudaron sobre el mismo objetivo. Ninguno reportó un hallazgo crítico. Los dos dan por resueltos de forma coherente RK-01, RK-02, RK-05, RK-06, RK-08, RK-09, RK-10 y RK-11. RK-03 queda resuelto con las brechas RL-06 y RL-07; RK-04 con RL-09; RK-07 con RL-01.

Hallazgos sobre el delta de la ronda 3, ninguno corregido todavía:

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| RL-01 | Los dos | Advertencia | Vincular la misma solicitud con dos fichas distintas a la vez, o vincular una solicitud ya `vinculada`, no termina en "cero filas": choca con `UNIQUE (usuario_id)` de `paciente` (error 23505). Los documentos no lo traducen a 409 ni ordenan primero la escritura de la solicitud; la prueba de C-08 no puede pasar. | `knowledge-base/04:331`; `CHANGES.md:366-370` |
| RL-02 | Los dos | Sugerencia | El esquema de Compose de la KB 12 no incluye el secreto `origin_hash_secret` en `migrate`, en `api` ni en el bloque de secretos, aunque C-05 lo exige. | `knowledge-base/12:105-158` |
| RL-03 | Los dos | Sugerencia | SU-45 dice que cuenta cada intento de registro aunque después falle la validación, pero nada indica que la fila de `intento_registro` se confirme aparte de la transacción del registro. Si la comparte, los intentos fallidos no se cuentan. | `knowledge-base/04:260`; `09:435`; `07:49` |
| RL-04 | Un juez | Advertencia | `ORIGIN_HASH_SECRET` no está en la lista de variables que los logs ocultan, que C-01 define por nombre. La clave protege hashes de direcciones, que son dato personal. | `CHANGES.md:298`; `openspec/.../specs/structured-logging/spec.md:37` |
| RL-05 | Un juez | Advertencia | Al reprogramar, RN-32, C-16 y un punto de la KB 04 omiten solo las notificaciones `programada`; otro punto de la KB 04 y el flujo 6 dicen `programada` o `preparada`. Un mensaje de WhatsApp `preparada` con la fecha vieja queda en la lista de Recepción. C-17 solo prueba el turno cancelado. | `CHANGES.md:537,567`; `knowledge-base/05:80`; `04:439,443`; `07:245` |
| RL-06 | Un juez | Advertencia | Desvincular no tiene superficie de lectura: ningún endpoint devuelve qué cuenta tiene una ficha ni qué ficha tiene una cuenta, y los casos 1 y 2 de RK-03 dependen de saberlo. | `CHANGES.md:366-367`; `knowledge-base/07:66`; `04:307` |
| RL-07 | Un juez | Advertencia | El corte inmediato de acceso al desvincular se apoya en que "el token no lleva la ficha", pero RN-06 dice "como mínimo" y no lo prohíbe, y ninguna prueba verifica que un access token previo pierda la ficha. Además la política A1 es una función pura sin acceso a datos y su firma no recibe el vínculo vigente. | `knowledge-base/05:32,125`; `11:15,32,44-45`; `CHANGES.md:370` |
| RL-08 | Un juez | Sugerencia | El enum `tipo` no tiene valor para el correo de confirmación de la cancelación hecha por el paciente ni para el resumen del turno al reservar (US-014), así que la tabla de vigencia no puede regirlos. Existía antes de esta ronda. | `knowledge-base/04:407`; `07:246`; `CHANGES.md:545` |
| RL-09 | Un juez | Sugerencia | La prueba "una ficha creada por Recepción sirve para dar un turno" quedó en C-13 como prueba de interfaz con la API simulada; ninguna prueba de backend la cubre. | `CHANGES.md:350,370,472` |
| RL-10 | Fix | Abierto | Ningún documento define cómo se desactiva una ficha, así que "reactivar" no tiene contraparte. Lo informó el agente de correcciones. | `knowledge-base/04` (`paciente.activo`); SU-44 |

## Rejuicio acotado de la ronda 4

Fecha: 2026-10-11. Objetivo: el libro más el delta de la ronda 4 (del estado posterior a la ronda 3 al árbol de trabajo; sha256 del diff `c4db4d4e7c1d5dbd…`). Los dos jueces leyeron el delta completo. Ninguno reportó un hallazgo crítico y los dos dan por resueltos RL-01 a RL-10.

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| RM-01 | Un juez | Advertencia | El orden nuevo de la vinculación (solicitud primero, ficha después) puede interbloquearse cuando dos vínculos simultáneos de solicitudes distintas apuntan a la misma ficha: la verificación de la clave foránea del paso 1 toma un bloqueo compartido sobre la ficha y el paso 2 pide uno exclusivo. El motor aborta una con `40P01`, que no es una violación de unicidad. Inferido de la semántica de bloqueos de PostgreSQL, no ejecutado. | `knowledge-base/04:333`; `CHANGES.md:366-370`; `06:399` |
| RM-02 | Los dos | Sugerencia | C-04 define el punto de entrada `acceso.autorizar(usuario, accion, recurso, ahora)`, sin lugar para la ficha vigente que la KB 11 dice que llega por `contexto`. | `CHANGES.md:271`; `knowledge-base/11:80-82` |
| RM-03 | Un juez | Sugerencia | No está definido qué devuelve la lista `GET /turnos` para una cuenta sin ficha; una lectura literal del 404 rompería "Mis turnos" para toda cuenta que espera vinculación. | `knowledge-base/11:148`; `CHANGES.md` C-09 |
| RM-04 | Un juez | Sugerencia | El principio general de la KB 04 sigue diciendo que los pacientes "se desactivan", lo que sugiere una acción que SU-47 dice que no existe. Existía antes. | `knowledge-base/04:10` |

## Ronda 5 de correcciones

Fecha: 2026-10-11. Aplicada por el orquestador, sin commitear (sha256 del diff `0194b2845e9d97f5…`, 7 archivos).

| ID | Corrección |
|----|------------|
| RM-01 | La vinculación bloquea primero la fila de la ficha (`SELECT ... FOR UPDATE`) y después escribe la solicitud y la ficha. Un interbloqueo o fallo de serialización (`40P01`, `40001`) también se traduce a 409. Reconciliado en la KB 04, 05, 06, 07, 09 y C-08. |
| RM-02 | C-04 usa `acceso.autorizar(usuario, accion, recurso, contexto)`; el contexto lleva el instante `ahora` y la ficha vigente. La KB 11 dice lo mismo. |
| RM-03 | Una cuenta sin ficha vinculada que lista sus turnos recibe 200 con lista vacía; el 404 queda para el acceso por identificador. KB 11 y C-09. |
| RM-04 | El principio de la KB 04 aclara que la v1 no desactiva fichas de paciente (SU-47). |

## Rejuicio acotado de la ronda 5

Fecha: 2026-10-11. Objetivo: el delta de la ronda 5 (sha256 `0194b2845e9d97f5…`). Los dos jueces lo leyeron completo. Ninguno reportó un hallazgo crítico. Los dos dan por resueltos RM-02, RM-03 y RM-04, y confirman que el bloqueo inicial de la ficha elimina el interbloqueo de RM-01 sin ciclos nuevos contra desvincular, rechazar ni reactivar. Los identificadores de esta sección llevan el prefijo "R5-" para no confundirlos con las reglas de negocio.

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| R5-01 | Los dos | Advertencia | RM-01 a medias: la traducción de `40P01` y `40001` a 409 quedó escrita solo en el párrafo "Vincular" de la KB 04. Faltaba en C-08, que es de donde se implementa, en la KB 05, 06, 07 y 09, y en la fila resumen de RN-62 de la KB 04, que además no nombraba el bloqueo inicial. | `CHANGES.md:366,370`; `knowledge-base/04:501`; `05:115`; `07:60` |
| R5-02 | Los dos | Sugerencia | La consulta de bloqueo no filtraba por `consultorio_id` y no estaba definido qué responde vincular cuando la ficha no existe; con el orden nuevo terminaba en un error de clave foránea sin traducir. | `knowledge-base/04:333`; `CHANGES.md:366` |

## Ronda 6 de correcciones

Fecha: 2026-10-11. Aplicada por el orquestador, sin commitear.

| ID | Corrección |
|----|------------|
| R5-01 | La traducción de interbloqueo y fallo de serialización a 409 figura en C-08 (alcance y pruebas), en la KB 04 (párrafo y fila resumen de RN-62), 05, 06, 07 y 09. La fila resumen nombra el bloqueo inicial. |
| R5-02 | La consulta de bloqueo filtra por `consultorio_id`. Si la ficha no existe en el consultorio, vincular responde 404 sin cambiar nada. Escrito en los mismos seis lugares, con prueba en C-08. |

## Rejuicio acotado de la ronda 6

Fecha: 2026-10-11. Objetivo: el delta de la ronda 6 (sha256 `fd681bfc56aab970…`, 6 archivos). Los dos jueces lo leyeron completo y dan por resueltos R5-01 y R5-02 en todos los lugares que describen la vinculación; buscaron otras descripciones en la KB 02, 03, 10 y 11 y en C-05 y C-13, sin encontrar contradicciones. Un juez no reportó hallazgos. Ninguno reportó un hallazgo crítico ni una advertencia.

| ID | Jueces | Severidad | Hallazgo | Ubicación |
|----|--------|-----------|----------|-----------|
| R6-01 | Un juez | Sugerencia | Vincular responde 404 cuando la ficha no existe en el consultorio, pero desvincular y reactivar responden 409 por su regla de "cero filas", sin distinguir una ficha inexistente. No es una contradicción; existía antes de la ronda 6. Sin corregir. | `knowledge-base/04:314`; `CHANGES.md` C-08 |

## Estado al cierre del 2026-10-11

- Seis rondas de corrección sobre `44d3cdc`, todas sin commitear. Ningún rejuicio reportó un hallazgo crítico.
- Hallazgos por rejuicio: 13 (RJ), 11 (RK), 10 (RL), 4 (RM), 2 (R5), 1 (R6, sugerencia preexistente).
- Corregidos: JD-01 a JD-05 y todos los RJ, RK, RL, RM y R5. La mitad de JD-19 (ruta de confirmación por enlace) quedó resuelta por RJ-05.
- Abiertos: JD-06 a JD-31 (salvo lo anterior), las sugerencias originales y R6-01.
- Ninguna prueba se ejecutó: son documentos. El comportamiento de bloqueos de PostgreSQL de RM-01 está inferido de su semántica documentada.
- Las elecciones de los agentes y del orquestador que el responsable todavía no confirmó figuran como SU-42 a SU-47 en la KB 09.
