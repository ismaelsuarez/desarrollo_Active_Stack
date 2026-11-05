# Design

## Context

Ver [proposal.md](proposal.md) para el motivo y las tres capacidades. C-04/C-05 están archivados; C-07 dejó disponible el adaptador de agenda y una UoW con rollback de cuerpo, flush y commit. La última implementación verificada tiene 348 pruebas unitarias y 558 de integración: es contexto histórico, no una ejecución de C-08.

Inspección de fuentes realizada antes de redactar:

| Fuente existente | Hallazgo observado | Uso previsto |
| --- | --- | --- |
| `backend/app/infrastructure/db/models.py` (`PacienteModel`) y `account_models.py` (`SolicitudVinculacionModel`) | Campos, FK, unicidades, checks e índices de KB 04 ya creados; tres estados de solicitud | Reutilizar sin una migración nueva |
| `backend/app/infrastructure/db/cuentas.py` | `revocar_sesiones` actualiza refresh sin commit; registro crea ficha o solicitud; métodos de usuario bloquean la fila | Componer revocación en la transacción de desvincular |
| `backend/app/application/services/cuentas.py` | Contacto propio cambia cuenta/ficha y reverifica correo; sus métodos hacen commit | Extraer únicamente el núcleo transaccional compartido necesario, conservando wrappers y contratos C-05; no invocar un commit autónomo desde C-08 |
| `backend/app/application/services/auth_service.py` y `tests/integration/test_refresh_reset_race.py` | Refresh y reset serializan por usuario y recargan el token antes de rotarlo | Proteger revocación de desvincular frente a refresh en vuelo, con pruebas reales de dos sesiones |
| `backend/app/infrastructure/db/agenda_turnos.py` y `application/ports/repositorios.py` | Profesional vinculado y pacientes con turnos en su agenda, scoped por consultorio | Alcance del Profesional, sin inventar otra noción de paciente asignado |
| `backend/app/domain/policies/{acceso,paciente}.py` | Acciones existentes; Profesional fuera de agenda devuelve 403 al pedir ficha | Ajustar paciente.ver a 404 para ficha ajena por id según KB 11; mantener 403 para acción prohibida |
| `backend/app/application/services/notificaciones.py` y `api/v1/routers/cuentas.py` | Despacho durable después del commit; tipo vinculacion_rechazada ya soportado y vigencia de correo verificado | Nueva plantilla/programación de rechazo, sin duplicar despacho ni agregar barrido |
| `backend/app/infrastructure/correo/plantillas.py` | Sólo plantillas de verificación y recuperación | Agregar plantilla de rechazo sin tokens, DNI ni motivo |
| `backend/app/api/v1/routers/agenda_turnos.py` | `/pacientes/{id}/turnos` ya existe para personal/Profesional | Conservar ruta y sus filtros, sin abrir reserva propia C-09 |

Fuentes de dominio: KB 04 §paciente/solicitud_vinculacion/notificacion; KB 05 RN-06, RN-47–RN-51, RN-54, RN-58, RN-62, RN-63; KB 06 US-036–US-039/US-041/US-042; KB 07 Flujo 1; KB 09 DD-19/20 y SU-42/44/47 **confirmadas**; KB 11 matriz y códigos. Q-10 no amplía la relación una cuenta–una ficha; no hay pregunta Alta del alcance local pendiente.

## Goals / Non-Goals

**Goals:** mantener los límites de una transacción por acción, datos mínimos por rol, vínculo vigente en cada solicitud y reversión completa en conflictos. Producir contratos API verificables con datos sintéticos y PostgreSQL real.

**Non-Goals:** migrar por rutina, modificar tokens de acceso, almacenar salud en notas, inventar historial de vínculos/auditoría general, cambiar la política de correo de cuenta ni construir UI, reserva pública o barrido. No se aplican cambios durante esta planificación.

## Decisions

### 1. Repositorios y UoW específicos, esquema conservado

Agregar puertos de fichas/solicitudes y adaptadores SQL en la estructura actual, expuestos por `UnidadDeTrabajoSQL`. La fábrica seguirá abriendo una sesión por operación con `expire_on_commit=False`. Lecturas y escrituras siempre llevan `consultorio_id` del Principal; no usar `session.get(id)` sin filtro de pertenencia. El reloj inyectado proporciona todas las fechas.

Las tablas e índices necesarios existen, incluso `UNIQUE (paciente.usuario_id)` y `UNIQUE (solicitud.usuario_id)`. Se descarta crear tablas paralelas o una revisión vacía. La implementación comprobará el esquema real con tests de constraints y conservará el único head `0008_turnos_core`. Cualquier carencia de esquema no observada exige revisar este diseño antes de añadir DDL.

### 2. Contratos API y normalización

Rutas bajo `/api/v1`, sin colisiones con el GET de turnos ya entregado:

| Ruta | Actores y contrato |
| --- | --- |
| `GET /pacientes` | Personal, Profesional scoped y Paciente propio; filtros opcionales `apellido`, `dni`, `telefono`, `limit`, `offset` |
| `POST /pacientes` | Recepción/Administrador; cinco campos obligatorios, `obra_social`/`notas` opcionales; 201 con id mínimo |
| `GET /pacientes/{id}` | Roles según ABAC; detalle y proyección de cuenta dependiente del rol |
| `PATCH /pacientes/{id}` | Personal corrige ficha; Paciente titular sólo contacto; Profesional denegado |
| `GET /solicitudes-vinculacion` | Sólo Recepción/Administrador; `estado` opcional y paginación |
| `POST /solicitudes-vinculacion/{id}/vincular` | Sólo personal; cuerpo `paciente_id` |
| `POST /solicitudes-vinculacion/{id}/rechazar` | Sólo personal; `motivo` opcional |
| `POST /pacientes/{id}/desvincular` | Sólo personal; `motivo` obligatorio, no vacío tras trim |
| `POST /pacientes/{id}/reactivar` | Sólo personal; sin datos de negocio en el cuerpo |

Decisiones técnicas propuestas para revisión: colecciones `{items, total, limit, offset}`, `limit=20`, rango 1–100, `offset>=0`; combinar filtros con AND; apellido por subcadena insensible a mayúsculas, DNI exacto con el value object existente y teléfono por subcadena literal del valor guardado, sin normalización internacional nueva. Escape de comodines de LIKE. Orden de fichas por apellido/nombre/id y de solicitudes por creada_en/id; el total aplica los mismos filtros de acceso que items. Estado omitido significa todos; no equivale a pendiente. Crear devuelve 201; acciones y PATCH devuelven 200 con un mensaje/id mínimo, sin datos de cuenta innecesarios.

Reutilizar tipos de cuenta para nombre/teléfono/correo y `Dni`: normalizar espacios exteriores y rechazar puntos, letras y espacios internos, sin introducir una política distinta de C-05. El contrato general de `core-data-models` sobre DNI dice sin espacios, pero el value object existente aplica strip; esta propuesta preserva el comportamiento de C-05 y no cambia ese requisito general ni amplía los formatos aceptados. Normalizar email con trim/minúsculas. PATCH conserva omitidos y sólo permite null para opcionales `obra_social`/`notas`; exige al menos un cambio permitido. `activo`, `usuario_id`, `consultorio_id`, estados y actores son siempre del servidor. Entradas y consultas declaradas usan `extra='forbid'`; errores no incluyen input privado, igual que los validadores de cuenta existentes. No exponer parámetros privados en logs de rechazos ni copiar la query de búsqueda al log.

### 3. ABAC, proyecciones y contacto propio

Usar dependencias RBAC y `autorizar` en aplicación. Scoped lookup/colección antes de cargar y contar: Profesional usa `pacientes_de_profesional` (incluye turnos históricos de su agenda); Paciente lee la ficha vigente en la base, no desde claims. Para una ficha ajena por id se devuelve 404, incluso el Profesional; un rol que no puede ejecutar una acción obtiene 403. Los conflictos de escritura se traducen en aplicación a 409 y la entrada inválida a 422.

Listado de fichas: id/nombre/apellido/teléfono/activo suficientes para seleccionar; no notas, obra social ni cuenta. Detalle de ficha autorizada usa campos de RN-47, sin `usuario_id` en crudo; sólo el personal añade `cuenta: {id,nombre_usuario,email,email_verificado}` o null, y los otros lectores omiten la propiedad. Lista de solicitudes expone id/estado/DNI declarado/email/verificación, coincidencia mínima de ficha y última resolución; `ficha_vinculada` sólo para vinculada. En rechazada tras desvincular, conservar el origen en persistencia, sin presentarlo como vínculo actual. No serializar modelos ORM completos.

Personal puede cambiar el contacto de **la ficha**, sin modificar el correo de login o su verificación: la KB no autoriza al personal a editar la identidad de cuenta mediante esta ruta. El Paciente sólo puede cambiar contacto propio; preservar el contrato C-05 exige reutilizar su núcleo de actualización de cuenta/verificación, sin hacer commit interno. Para PATCH propio, bloquear usuario con el protocolo C-05, volver a cargar la ficha vigente y comprobar que su id sea el de la URL **dentro de la transacción** antes de mutar; si cambió el vínculo, 404, sin editar otra ficha. Mantener `/auth/actualizar-cuenta` y sus pruebas; extraer un colaborador transaccional pequeño en vez de duplicar la lógica de verificación. El plan no crea un endpoint nuevo de autenticación ni cambios de JWT.

### 4. Vincular: ficha primero y dos escrituras condicionales

Contrato de KB 04/RN-62, no decisión nueva:

1. Cargar la solicitud scoped y el estado leído; verificar RBAC/ABAC. Sin solicitud propia, 404.
2. Tomar el **primer bloqueo de fila** sobre la ficha destino, con `SELECT ... WHERE id AND consultorio_id FOR UPDATE`. Si no existe, 404. No bloquear solicitud primero: dos cuentas que apuntan a la misma ficha podrían interbloquear por las FK.
3. Verificar correo de cuenta y elegibilidad; mantener todas las escrituras en esa UoW. Pasar solicitud a vinculada con predicado por id/consultorio/estado leído y `estado IN ('pendiente','rechazada')`, guardando ficha, actor y fecha. Conservar el motivo anterior.
4. Asignar usuario de la solicitud a la ficha con predicado por id/consultorio/`activo=true`/`usuario_id IS NULL`. Exigir una fila en ambos pasos, mediante RETURNING o rowcount verificable.
5. Confirmar antes de responder. Cualquier cero filas o unicidad de `paciente.usuario_id` revierte ambas escrituras y produce 409. No comparar el DNI de ficha con el declarado.

Las otras transiciones de ficha toman también paciente primero. Sólo la resolución ganadora conserva efectos: dos cuentas/una ficha, una solicitud/dos fichas y rechazo/vínculo se prueban con conexiones independientes y sincronización antes de escribir, sin sleeps. No inventar prioridad del ganador ni reintento automático.

### 5. Rechazar: outbox existente y despacho tras commit

Actualizar condicionalmente solicitud pendiente por el estado leído, actor/fecha/motivo; obtener la cuenta scoped y su verificación. Si corresponde, insertar una única `notificacion` email `vinculacion_rechazada`, `programada`, usuario y destinatario de cuenta, turno null y reloj de la operación. Plantilla propia de C-08: mensaje mínimo de comunicación con consultorio, sin motivo, DNI, salud, prestación ni enlace de recuperación automática.

La inserción y la resolución confirman juntas. El caso de uso retorna el id de notificación; el router solicita `DespacharNotificacion` mediante el mecanismo de C-05 sólo **después** del commit. Un doble del puerto verifica el disparo inmediato; Mailpit verifica integración del transporte. Fallo SMTP no deshace rechazo y sigue el estado/reintento del despachador existente, que vuelve a comprobar verificación. Repetir rechazo devuelve 409 sin insertar otra notificación. No reutilizar `correo_cuenta` con un token ficticio ni enviar SMTP dentro de la transacción; no agregar C-15 como dependencia.

### 6. Desvincular y reactivar con revocación segura

Desvincular: lectura scoped/primer bloqueo de ficha; si no existe 404, si no tiene cuenta 409. Guardar el usuario leído y actualizar `paciente.usuario_id=NULL` sólo si sigue coincidiendo. Upsert de solicitud por usuario, sin estados nuevos: crear rechazada con DNI actual si no existía; si existía, actualizar **sólo si estaba vinculada**. Guardar origen, actor, fecha y motivo; comprobar que devuelve una fila o revertir con 409. No cambia datos ni turnos, ni programa correo.

Antes de revocar, bloquear y recargar la fila de usuario scoped usando el protocolo existente de reset/refresh; ejecutar `RepositorioCuentas.revocar_sesiones` con la **misma sesión** y confirmar todo junto. Un refresh que ya tenía el lock termina antes y su reemplazo también se revoca; uno posterior espera y encuentra su token revocado al recargar. No basta con un UPDATE sin serialización: una rotación en vuelo podría insertar un token después del barrido de revocación. No llamar a `ServicioCuentas.restablecer_password` ni cambiar contraseña. La secuencia de C-08 respeta paciente→solicitud→usuario; los errores de interbloqueo/serialización se traducen y revierten, no se promete ausencia absoluta frente a otras operaciones C-05 con orden usuario→paciente.

Reactivar: primer bloqueo scoped de ficha; `UPDATE ... activo=false` a true, conservando el resto. Cero filas exige consulta scoped de existencia: inexistente 404, ya activa 409. Sin motivo, notificación ni registro propio. Misma serialización por ficha para vínculos concurrentes. Desvincular doble/reactivar doble dejan una operación exitosa; vínculo+desvínculo puede serializar dos operaciones válidas, pero nunca dos cuentas en la ficha. La solicitud conserva **última** resolución, no un historial nuevo.

### 7. Traducción selectiva de fallos y plan TDD

El límite de aplicación debe capturar también fallos de flush/commit tras salir de UoW. Unicidad esperada de DNI en alta/edición y de `paciente.usuario_id` en vínculos responde 409 con rollback. `40P01` y `40001` de las transacciones C-08 de vínculo/resolución/desvinculación/reactivación y del nuevo PATCH de contacto propio responden 409 sin efectos parciales. En particular, PATCH propio usa usuario→paciente y puede ser víctima al competir con desvincular; cubrir ambos órdenes y no prometer corrección global de los endpoints previos C-05. No convertir toda `IntegrityError` en un conflicto de vínculo ni ocultar otra FK o fallo de programación. Reutilizar el patrón selectivo C-07 y extraer el SQLSTATE del driver encapsulado. Context7 consultado: documentación oficial SQLAlchemy 2.x de `with_for_update`, `CursorResult.rowcount` y upsert PostgreSQL con `where`; UPDATE cuenta filas coincidentes y el upsert condicionado requiere comprobar resultado, no asumir éxito.

Antes de producción, aplicar safety net de C-05/C-07/ABAC. Después, por cada tarea: RED ejecutado, mínimo GREEN, al menos feliz+borde por comportamiento y refactor verde. Integración con PostgreSQL real: sesiones/conexiones separadas y eventos/barreras para carreras; puertos de correo doblables para reglas, Mailpit para envío. Reutilizar patrón `test_refresh_reset_race.py`. Simular errores SQLSTATE en el punto de una transacción real sin mockear repositorio/constraints; rollback y estado final se comprueban mediante otra sesión. No usar SQLite ni reloj real para JWT de fixtures.

## Risks / Trade-offs

- [Access JWT sigue válido hasta vencer] → preservar RN-06: vínculo actual en cada solicitud y revocación de refresh; no prometer revocación de access tokens.
- [Orden de locks C05 y C08 puede producir interbloqueos] → paciente primero donde KB lo exige, transacciones cortas, 40P01/40001→409 en acciones C08 y pruebas de concurrencia; no garantizar ganador ni reintento automático.
- [Correo al menos una vez] → outbox/reclamación C-05; sólo un trabajo por rechazo ganador, sin prometer exactamente una entrega SMTP.
- [Resolución conserva sólo el último actor/fecha] → cumplir DD-20/SU-44, no presentar la solicitud como auditoría histórica completa.
- [Búsqueda por subcadena puede escanear datos] → paginar y usar índices existentes; no instalar extensiones ni añadir índices de rendimiento sin medición para un consultorio pequeño.
- [Contacto de ficha y login pueden diferir] → separar proyecciones y documentar qué cambia el personal; contacto propio preserva reverificación C-05.
- [Cuatro recorridos de RN-63 conservan turnos] → en el caso del tercero, seguir Flujo 1: gestionar las cancelaciones que correspondan antes de corregir el contacto, con acciones C-07 ya existentes; no automatizar cancelaciones ni correos de turno en C-08.
- [Gobernanza ALTO y datos personales] → sólo artefactos ahora; presentar el plan y esperar una nueva instrucción de apply antes de código. RN-65 sobre la leyenda de notas corresponde a UI C-13, sin afirmar revisión legal.

## Migration Plan

Sin migración de esquema ni nueva dependencia. Apply agregará routers/casos de uso/repositorios, ampliará puertos/UoW sin cambiar sus consumidores y conservará el head 0008. Validar primero las suites existentes, después casos C-08 y al final suites completas con PostgreSQL/Mailpit. Publicación/commit/push y archivo quedan fuera de esta propuesta. Revertir código no borra fichas ni solicitudes; conservar las filas creadas/resueltas y revisar operativamente cualquier vínculo, sin un downgrade destructivo ni restauración sobre datos reales.

## UI Mockups

Decision: no (no UI), 2026-11-03. C-08 es API; la pantalla y la leyenda junto a notas corresponden a C-13. No se modifica la política visual del proyecto.
