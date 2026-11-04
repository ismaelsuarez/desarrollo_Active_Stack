# Design

## Context

Preparación de C-07 al 2026-11-03. Ver `proposal.md` para motivación y límites funcionales. Documento de planificación: no acredita implementación ni ejecución de pruebas.

OpenSpec 1.16.0 instalado localmente con autorización (`npm.cmd install --no-save --package-lock=false @fission-ai/openspec`). `list --json` y `context --json` resolvieron la raíz existente; no había changes activos. `new change c-07-turnos-core` creó la metadata con el esquema `spec-driven` ya configurado. No se ejecutó init ni se modificó `openspec/config.yaml`.

Estado observado fuera de OpenSpec:

- C-04 y C-06 figuran archivados en `CHANGES.md`; sus specs principales están presentes y se consultaron con la CLI.
- `backend/app/application/use_cases/crear_turno.py` crea un turno básico; no integra todavía horario, políticas y ciclo de confirmación de C-07.
- `backend/app/infrastructure/db/models.py` ya contiene `TurnoModel`, el enum y `ExcludeConstraint`; `0001_turnos_sin_solapamiento.py` ya creó `btree_gist` y la exclusión a mano. El extremo actual de la cadena declarada es `0007_agenda_config`.
- `repositorios.py` traduce selectivamente SQLSTATE y nombre de restricción a `HorarioOcupado`. `sesion.py` usa `expire_on_commit=False` y desactiva caché de prepared statements. `unidad_de_trabajo.py` abre sesión propia, confirma/revierte y cierra.
- Ya hay una prueba de `23P01` en `backend/tests/integration/test_migracion.py`, pruebas de creación y unidad de trabajo. Se inspeccionaron; no se ejecutaron en esta preparación. SU-39 sigue sin confirmarse en esta sesión.
- El endpoint de bloqueos de C-06 ya consulta turnos afectados y evita guardar el bloqueo si los hay. C-07 debe probar y completar esa integración, no duplicarla.
- La spec ABAC y `domain/policies/acceso.py` devuelven 403 para ciertos turnos de otra agenda; KB 11 y las instrucciones exigen 404 por identificador. El delta corrige el contrato y tasks incluye la regresión.
- Se consultó `.atl/skill-registry.md` y las skills locales completas. La revisión de dominio no refrescó el registro, como exige su límite de solo lectura. El refresco Python del flujo general no está disponible en PATH; no se sustituyó por skills globales ni se instalaron otras herramientas.

## Goals / Non-Goals

**Goals:** preservar la garantía de C-00 al integrar transiciones, historia, autorización y agenda; expresar criterios observables y tareas trazables; distinguir pruebas existentes, propuestas y pendientes.

**Non-Goals:** rediseñar auth, introducir un nuevo patrón de persistencia, ejecutar migraciones, operar datos reales, construir UI o adelantar C-08/C-09/C-10/C-15/C-16/C-17/C-20. No modificar specs principales durante la propuesta.

## Decisions

### 1. Extender la unidad de trabajo existente

Cada caso de uso mutador tendrá una unidad de trabajo con sesión propia. La lectura del turno, las validaciones con estado relevante, su escritura y su historial pertenecen a una sola transacción. Los repositorios no hacen commits parciales. No compartir la unidad ni una AsyncSession entre tareas; compartir la fábrica sí es válido.

Se mantiene `expire_on_commit=False` y la configuración del pooler. Son decisiones de ciclo de vida e IO; no serializan reservas. Alternativa descartada: una sesión global o una sesión compartida dentro de `asyncio.gather`, incompatible con la documentación y la regla dura 10.

### 2. La exclusión sigue siendo la garantía final entre regulares

Mantener `turno_sin_solapamiento` con consultorio/profesional e intervalo `tstzrange(inicio, fin, '[)')`, operador `&&`, solo para regulares en pendiente/confirmado/atendido/ausente. Cancelado/liberado no ocupan; otro profesional u otro consultorio no chocan en esta restricción. La autorización sigue siendo independiente del conflicto temporal.

Consultar disponibilidad antes de insertar puede mejorar la respuesta, pero dos transacciones podrían ver el hueco libre. La exclusión decide la escritura incluso entonces (RN-17/RN-24/DD-08). No añadir candado global, advisory lock ni bloquear una fila de turno inexistente como garantía de hueco.

Crear o mover un regular sobre un sobreturno activo ya existente se rechaza en la aplicación con 409. Para pruebas, esa fila proviene de una fixture. La carrera entre alta simultánea regular/sobreturno sigue siendo el riesgo residual documentado; C-10 es dueño del alta de sobreturnos.

### 3. Reprogramar actualiza la misma fila y conserva coherencia

Validar el intervalo nuevo y conservar `fin - inicio` salvo ajuste explícito del personal. Una sola escritura del turno cambia inicio/fin, estado derivado, ciclo y marca; no crear un segundo turno ni comprobar conflicto contra sí mismo. Agregar historial en la misma transacción.

Propuesta técnica para evitar aplicar una validación obsoleta: escritura condicional respecto del estado/ciclo/horario leídos. Cero filas afectadas se traduce a conflicto 409 según KB 11. No fija qué solicitud gana, reintentos automáticos o prioridad entre cancelar/mover/liberar. Esas carreras se caracterizan antes de ampliar su contrato.

Ante error en la escritura o el historial: rollback completo. Ningún cambio de ciclo, marca, estado o historial sobrevive a una reprogramación fallida (RN-37).

### 4. Traducir errores sin ocultar otras fallas

Reutilizar el filtro de SQLSTATE `23P01` y nombre `turno_sin_solapamiento` en el adaptador de persistencia; emitir error de dominio y 409 en API. No traducir todo IntegrityError a horario ocupado. El límite de manejo debe cubrir el flush y el commit que cierre la operación antes de enviar éxito HTTP.

Tras un flush fallido no continuar con consultas en la sesión inactiva: propagar la falla para rollback y cierre, o cerrarla y descartarla. No capturar el error y devolver éxito dentro de la unidad de trabajo. Ampliar la prueba del ciclo de cierre para cubrir errores de commit; no se prescribe una segunda infraestructura transaccional en paralelo.

### 5. Políticas puras, agenda y reloj

Consultorio se obtiene del Principal, nunca del body. RBAC por dependencias y `acceso.autorizar` en los casos de uso con recurso/contexto completos. No replicar autorizaciones en routers.

Usar Reloj inyectado una vez por operación y `America/Argentina/Buenos_Aires` para día de agenda y bloques. Validar que el intervalo completo cabe en un bloque, sin excepciones propias/globales. Grilla anclada al inicio del bloque; solo duración ajustada exige múltiplo de grilla, no la duración del catálogo. El personal no hereda límite de 60 días ni máximo 2.

Estado inicial pendiente salvo confirmación manual o anticipación estrictamente menor a horas_confirmacion, que exige confirmado (RN-23/RN-29). A 48 horas exactas sin confirmación manual queda pendiente. Reprogramar aplica RN-29, incrementa ciclo y limpia marca. La historia distingue confirmación por regla y por persona.

### 6. API e integración futura sin adelantar changes

Rutas de C-07: GET/POST `/api/v1/turnos`, GET/PATCH `/api/v1/turnos/{id}`, POST `/api/v1/turnos/{id}/{confirmar|cancelar|liberar|atendido|ausente}`, GET `/api/v1/turnos/{id}/historial`, GET `/api/v1/agenda?profesional_id=&fecha=` y GET `/api/v1/pacientes/{id}/turnos`. La corrección ausente→atendido se distingue como acción `turno.corregir_ausente` dentro de atendido, con historial `corregir`.

La creación expuesta aquí es por personal; los flujos de paciente de C-09 quedan fuera. Las políticas existentes de titularidad/ventana no se eliminan. DTOs de entrada con extra forbid; sin consultorio_id ni fin. Listados acotados por consultorio/rol y por fecha en agenda; salidas con datos mínimos, sin DNI, obra social, contacto o bloque de cuenta innecesarios.

Preparar un puerto de planificación de hitos invocado dentro de la unidad de trabajo, con implementación sin efectos para esta etapa. C-15 agrega avisos por cambios del personal y C-16 planificación real, omisión de hitos viejos y resumen de reserva; C-17 amplía WhatsApp. El contrato del puerto debe permitir compartir la transacción para que esas escrituras futuras sean atómicas. C-07 no envía SMTP ni promete notificaciones entregadas.

Para C-08, preparar la consulta que acota fichas a pacientes con turnos en la agenda del profesional; no crear/editar fichas aquí. Las fichas sin cuenta, sobreturnos y marca sin confirmar necesarios para pruebas se preparan con fixtures sintéticas.

### 7. Fundamento obtenido con Context7 MCP

Herramientas ejecutadas en esta preparación: `mcp__context7__resolve_library_id` para SQLAlchemy, seguida de tres llamadas reales a `mcp__context7__query_docs` (idioma Python). No se usó búsqueda web como sustituto.

| ID de biblioteca y consulta | Fuente oficial devuelta | Aplicación al diseño y tareas |
| --- | --- | --- |
| `/websites/sqlalchemy_en_20_orm`: concurrencia, begin y expire_on_commit | [Asyncio](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html), [Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#session-faq-threadsafe) | Una AsyncSession por tarea; async_sessionmaker.begin delimita sesión/transacción; mantener configuración y probar dos sesiones independientes. |
| `/websites/sqlalchemy_en`: exclusión PostgreSQL, where, GiST y btree_gist | [ExcludeConstraint](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html#sqlalchemy.dialects.postgresql.ExcludeConstraint) | Soporta expresiones/operadores y predicado; el ejemplo de rangos requiere btree_gist. Conservar exclusión y probar su expresión concreta. |
| `/websites/sqlalchemy_en_20_orm`: rollback luego de flush fallido | [Rollback](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#rolling-back), [transacciones](https://docs.sqlalchemy.org/en/20/orm/session_transaction.html) | Sesión inactiva requiere rollback antes de reutilizar o cierre/descarte; probar ausencia de efectos parciales y cierre ante errores. |

Los resultados documentan SQLAlchemy 2.0, coherente con `sqlalchemy[asyncio]>=2.0,<2.1` del backend. No prueban la expresión exacta del proyecto ni confirman el SQLSTATE del driver: SU-39 permanece a comprobar por ejecución, aunque ya exista una prueba en C-00. La relación entre prechequeo y carrera es una inferencia de diseño respaldada además por DD-08, no una prueba ejecutada.

## Revisión de dominio — appointment-conflict-reviewer

Revisión local de solo lectura consumida por el flujo de propuesta, sin operar pacientes ni implementar. Las conclusiones siguientes sustentan las specs; la skill no aprueba reglas nuevas. Fuentes consultadas: instrucciones AGENTS/CLAUDE, registro local, CHANGES C-07, KB README y secciones pertinentes de KB 04–11, specs principales y archivos de código enumerados en Context.

### Reglas aplicables y vigencia

| Referencia | Fuente y sección | Vigencia | Operaciones |
| --- | --- | --- | --- |
| RN-14/RN-64, DD-27 | KB 05 §Agenda, KB 09 §DD-27 | Reglas/decisión documentadas | Crear/mover: bloque, grilla, duración y límites por actor |
| RN-17/RN-22/RN-24, DD-08 | KB 05 §Turnos; KB 04 §turno; KB 09 §DD-08 | Confirmadas; carrera regular/sobreturno residual explícita | Exclusión y liberación del hueco |
| RN-21/RN-29/RN-32/RN-37, DD-32 | KB 05 §Turnos/Confirmación/Cancelación; KB 07 flujo 6; KB 09 §DD-32 | Confirmadas; SU-11 reemplazado por DD-32 | Atomicidad, historia y ciclo |
| RN-38/RN-44, US-026–028 | KB 05 §Ausentismo; KB 06 épica 6; KB 07 flujo 8; KB 11 matriz | RN-38 marcado supuesto; igualdad temporal confirmada por usuario para C-07: ahora >= inicio | Atendido/ausente y propiedad |
| DD-14, SU-39/SU-40 | KB 08 §Persistencia; KB 09 secciones homónimas | DD confirmado; SU requieren verificación | Migración, error y transacción |
| Q-26 | KB 10 tabla de preguntas, despliegue publicado | Abierta, solo C-20 | No bloquea C-07 local/CI |

### Escenarios y pruebas propuestas

Datos exclusivamente sintéticos: consultorios C1/C2, profesionales P1/P2, fichas F1/F2; 2026-11-09, zona Buenos Aires; bloques 09:00–12:00 y 13:00–17:00; grilla 15 min; prestación 30 min, salvo indicación; reloj base 2026-11-06 08:00 −03. A = regular P1/C1 10:00–10:30 pendiente.

| ID / tipo | Precondición y acción | Clasificación / resultado | Prueba y fuente |
| --- | --- | --- | --- |
| ESC-01 error | A y nuevo P1 10:15–10:45, 09:45–10:15, 10:00–10:30, 09:45–10:45 o 10:00–10:15 | Rechazado, horario ocupado sin cambios parciales | Integración rangos exacto/parcial/contención; RN-17, KB 04 §turno |
| ESC-02 borde | A y nuevo P1 10:30–11:00 o 09:30–10:00 | Permitido con las demás reglas válidas | Integración contiguos en ambos extremos; RN-17, intervalo [) |
| ESC-03 normal | Mismo intervalo P2/C1 o P1/C2 en prueba de restricción | Sin conflicto de exclusión; no implica permiso API cruzado | Integración + API 404 entre consultorios; DD-08, RN-55 |
| ESC-04 error | Dos reservas regulares P1/C1 del mismo hueco libre | Una permitida y otra rechazada; 1 turno y solo su historial | Dos sesiones/conexiones, barrera antes de escrituras, sin sleeps; RN-24 |
| ESC-05 borde | A cancelado/liberado frente a A pendiente/confirmado/atendido/ausente | Primeros no ocupan; últimos sí | Integración parametrizada por estado; RN-17/RN-22 |
| ESC-06 error/borde | Alta a 09:07, 11:45–12:15, cruzando pausa, bloqueo parcial/global/propio | Rechazado; 09:00–09:30 y 11:30–12:00 válidos | Unidad + integración/API; RN-14/RN-64 |
| ESC-07 borde | Ajuste 45 o 20 min con grilla 15; catálogo 20 sin ajuste | 45 permitido, ajuste 20 rechazado, catálogo 20 permitido | Unidad + API; RN-13/RN-15/RN-64 |
| ESC-08 normal/error | Mover turno ajustado 45 min; mover sobre regular o sobreturno activo | Éxito conserva duración/id; conflicto 409 conserva todo | Integración/API con fixture de sobreturno; RN-17/RN-37 |
| ESC-09 borde | Crear/mover a 47:59 h, 48 h y 48:01 h sin confirmación manual | Confirmado / pendiente / pendiente; mover limpia marca e incrementa ciclo | Reloj inyectado, unidad/integración/API; RN-29/RN-32, DD-32 |
| ESC-10 normal/error | Confirmar pendiente; liberar en manual o marcado; cancelar atendido | Permitidos según matriz; último rechazado 403 | Unidad/API + historial atómico; RN-19/RN-30/RN-60, KB 11 |
| ESC-11 borde | Marcar ausente un segundo antes, exactamente en y un segundo después de inicio | 403 / permitido / permitido, sujeto a rol, propiedad y estado | Unidad/API con reloj inyectado; criterio >= confirmado por usuario para C-07 |
| ESC-12 error | Profesional opera turno ajeno por id o pide agenda ajena | 404 por turno; 403 por agenda | Unidad/API, corrección delta ABAC; KB 11 códigos |
| ESC-13 normal | Recepción reserva para F1 sin cuenta, tercer turno o a 61 días | Permitido si respeta horario/solapamiento | Integración/API con fichas sintéticas; US-019, RN-64 e |
| ESC-14 error | Inserción de historial falla tras cambio de turno | Rechazado sin persistir estado/horario/ciclo/marca/historial | Integración fallo controlado con PostgreSQL real; RN-21/RN-37 |
| ESC-15 error/normal | Bloqueo de C-06 sobre A y luego sobre período libre | Informa afectados sin guardar el primero; acepta el libre | Integración/API; RN-16 (supuesto), professional-schedules |

Sin pruebas ejecutadas en esta fase. La carrera se fuerza con eventos/barrera antes de escribir y conexiones independientes; no esperar que ambas escrituras terminen antes de permitir commit, porque una puede quedar esperando a la exclusión de la otra. Verificar estado final desde una tercera sesión. Para otro profesional y otro consultorio usar controles que sí persistan ambos.

No se fijan resultados nuevos para dos movimientos de la misma fila, cancelar contra mover o altas contra cambios simultáneos de horario/bloqueos: la KB no define ganador/prioridad. Se conservan atomicidad, autorización e invariantes documentados y se pide decisión si se pretende ampliar la garantía.

## Risks / Trade-offs

- [Regular contra sobreturno concurrente] → Riesgo residual existente de RN-17, visible en diseño y pruebas; no presentar el prechequeo como exclusión atómica.
- [Código/forma real de excepción asyncpg] → Ejecutar la prueba de SU-39 con esquema migrado, comprobar nombre y SQLSTATE; otros errores deben seguir distinguiéndose.
- [Redacción temporal discrepante en la KB] → Criterio >= confirmado explícitamente por el usuario para C-07; probar antes/exacto/después. La KB conserva su redacción porque no se autorizó editarla; remitir a la confirmación documentada abajo.
- [Migración de legado C-00] → La tabla ya existe; agregar campos sin inventar actores, origen o eventos desconocidos. Ciclo puede inicializarse a 1. Campos históricos desconocidos permanecen nulos para legado; nuevas operaciones exigen su trazabilidad. Verificar con fixtures, nunca contra datos reales durante esta preparación.
- [Test previo que exige ausencia de FK] → `test_account_models.py` comprueba que notificacion aún no tiene FK a turno; actualizar ese contrato en RED junto con la nueva integridad, conservando el caso turno_id nulo.
- [Esquema y API anteriores] → La spec de C-00 exige pendiente universal y duración solo de catálogo; los deltas conservan sus escenarios y explicitan RN-29 y RN-64. La corrección ABAC es cambio observable deliberado y requiere regresión.
- [Q-26/SU-40 en proveedor] → Validar permisos de extensión antes de C-20; no bloquear desarrollo local/CI.
- [Reglas de carreras adicionales] → No inventar reintentos ni garantías entre operaciones cuyo contrato no está definido; revisar antes de ampliar alcance.

## Migration Plan

1. Antes de apply, registrar baseline de pruebas relacionadas y comprobar el head real; la cadena inspeccionada termina en `0007_agenda_config`. Si cambió, rebasar la revisión nueva; no merge ni `upgrade heads`.
2. Nueva revisión incremental sobre el head: campos de turno de KB 04 que faltan, quitar default SQL de tiempo heredado en favor de Reloj, crear historial y añadir FK de turno en token/notificacion y referencias obligatorias faltantes. No recrear tabla, enum ni exclusión de C-00.
3. Comprobar referencias preexistentes mediante fixtures de upgrade; ante huérfanos abortar con diagnóstico, sin borrar/reasignar datos silenciosamente. No fabricar historia anterior ni autor; mantener desconocidos explícitos para legado.
4. Probar `alembic upgrade head`, integridad, exclusión y conservación de filas en PostgreSQL real. La exclusión debe permanecer única; si fuese necesario modificarla, su DDL se revisa y escribe a mano tras garantizar btree_gist.
5. Verificar downgrade/upgrade solo en base descartable. El downgrade que retire columnas/historial pierde información nueva: requiere revisión humana antes de usarse sobre un entorno con datos; no ejecutarlo como recuperación automática. Para una falla de despliegue, preferir corrección hacia adelante y mantener datos.

## Criterio temporal confirmado por el usuario

El 2026-11-03 el usuario respondió «si» a la pregunta explícita «¿Confirmás adoptar ahora >= inicio para C-07, manteniendo la KB sin modificaciones?». Para este change, marcar ausente se permite desde el instante exacto de inicio, sujeto a los demás permisos y estados. No queda una decisión pendiente sobre ese borde; no se atribuye esta confirmación a una DD preexistente ni se crea un código DD nuevo.

Fundamento y discrepancia original, conservados para trazabilidad:

- `knowledge-base/05_reglas_de_negocio.md:103`, RN-44: «una vez que pasó su hora de inicio»; `knowledge-base/06_funcionalidades.md:374`, US-028: «una vez pasada la hora de inicio». Admitían la lectura estricta >.
- `knowledge-base/11_politicas_de_acceso_abac.md:27` dice «solo desde la hora de inicio» y en línea 62 explicita «ahora >= turno.inicio (para atendido y ausente)». `knowledge-base/07_flujos_principales.md:305` usa «hora de inicio alcanzada». Respaldan >=.
- `knowledge-base/09_decisiones_y_supuestos.md:33`, DD-04, remite el detalle ABAC a KB 11. DD-18 (línea 135) trata liberación y DD-32 (línea 235) confirmación al reservar; ninguna resolvía explícitamente la igualdad para ausente. La confirmación del usuario cierra esa diferencia para C-07.

El contrato ABAC principal ya expresa >= y no requiere otro delta temporal. Se agrega el escenario de igualdad a lifecycle y tareas de regresión para antes/exacto/después. La KB y las specs principales permanecen sin modificaciones en esta preparación.

## UI Mockups

- Decision: no (no UI)
- Fecha: 2026-11-03.
- Este change prepara API/dominio/persistencia; no altera páginas, componentes ni interacción visual. No requiere crear un sistema visual o mockups para este alcance.
