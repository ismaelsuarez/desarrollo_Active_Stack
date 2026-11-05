# Tasks

Apply autorizado y retomado por el usuario. Las casillas completadas reflejan comportamiento implementado y comprobado; ver [evidence.md](evidence.md) para ejecuciones, evidencia TDD por tarea, límites de los RED históricos recuperados y trazabilidad de los 17 requisitos/50 escenarios. PostgreSQL y Mailpit reales, reloj inyectado también para JWT. Ver [design.md](design.md) y los [tres deltas](specs/).

## 1. Autorización y red de seguridad

- [x] 1.1 Confirmar autorización de apply para C-08, consultar list/status/instructions y cargar skills locales según los archivos afectados; verificar C-04/C-05 archivados, alcance sin UI y decisiones confirmadas SU-42/44/47. Registrar el estado real sin marcar implementado por completar planificación.
- [x] 1.2 Ejecutar las suites existentes sin integración y con integración, con PostgreSQL/Mailpit reales y datos sintéticos; capturar baseline y detener ante fallos preexistentes. No atribuir a C-08 las 906 pruebas históricas de C-07 ni modificar fixtures fuera del alcance sin autorización.
- [x] 1.3 Verificar con metadatos/tests existentes los campos, FK, índices y unicidades de paciente/solicitud/refresh/notificación, y `alembic heads` único 0008; confirmar que no hace falta DDL. Si aparece una carencia no observada, reportar y revisar diseño antes de crear migración.

## 2. Contratos, repositorios y frontera transaccional

- [x] 2.1 Definir con tests unitarios los esquemas de alta/PATCH por rol, motivos y consultas: reutilizar normalización C-05, DNI con trim exterior y rechazo de puntos/letras/espacios internos, datos obligatorios, opcionales anulables, extras prohibidos y paginación válida/inválida. Verificar errores sin input privado y documentar DTO de colecciones según diseño §2.
- [x] 2.2 Agregar puertos y repositorios de fichas/solicitudes con PostgreSQL: obtener/listar/crear/editar, filtros del consultorio obligatorios, total calculado después del alcance y locks/actualizaciones condicionales con resultado comprobable. Probar IDs existentes/ajenos, vacío y constraints reales, conservando repositorios C-05/C-07.
- [x] 2.3 Integrar contexto de lectura y políticas puras con el adaptador C-07: probar Profesional propio/fuera de agenda, Paciente con/sin ficha vigente, tenant ajeno y Administrativo; ficha ajena por id debe ser 404 y acciones no permitidas 403. Añadir regresiones que conserven los permisos restantes de ABAC y documentar la corrección del antiguo 403 del Profesional.
- [x] 2.4 Exponer los repositorios nuevos por la UoW existente; probar con sesiones propias `expire_on_commit=False`, commit conjunto, rollback y cierre ante fallo del cuerpo, flush y commit. Verificar desde otra sesión que una operación fallida no persiste datos y documentar su uso transaccional sin commits internos.
- [x] 2.5 Implementar traducción selectiva de conflictos de DNI/usuario y SQLSTATE 40P01/40001 al salir de la transacción; probar errores esperados y otra FK/error no relacionado que no se transforme en conflicto de vínculo. Confirmar que el éxito HTTP sólo se construye tras commit y documentar los códigos 403/404/409/422.

## 3. Fichas, búsqueda y edición autorizada

- [x] 3.1 Implementar POST /pacientes para Recepción/Administrador; probar alta 201 recuperable por GET y elegible para vincular, datos obligatorios/opcionales, DNI duplicado mismo consultorio 409 y mismo DNI en otro consultorio permitido. Cubrir rol 403 y extras/formatos 422 sin ficha parcial; documentar payload y respuestas en OpenAPI/README.
- [x] 3.2 Implementar GET /pacientes con apellido/DNI/teléfono, AND, comodines literales, orden y paginación del diseño; probar cada criterio, combinación, páginas y vacío, con tenant/Profesional/Paciente acotados antes del total. Verificar que un paciente sin ficha recibe lista vacía y documentar filtros y envelope.
- [x] 3.3 Implementar GET /pacientes/{id} con proyecciones por rol; probar personal con cuenta de cuatro campos o null, Profesional/Paciente sin propiedad cuenta, ficha ajena/inexistente 404 y ausencia de hashes/tokens. Probar turnos históricos para alcance de Profesional y documentar los campos visibles por actor.
- [x] 3.4 Implementar PATCH de personal: probar correcciones parciales, trim de contacto, opcionales null, campos omitidos conservados, conflicto DNI 409 y obligatorio null/extras/activo/vínculo 422. Verificar cuenta de login, verificación, datos no tocados y turnos intactos, incluso ante fallo transaccional; documentar distinción ficha/cuenta.
- [x] 3.5 Implementar PATCH de contacto propio reutilizando un núcleo transaccional de C-05 sin commit autónomo; probar teléfono, correo diferente/equivalente/ocupado y campos no permitidos. Conservar los tests de /auth/actualizar-cuenta, reverificación e invalidación de enlaces. Forzar cambio de vínculo entre lectura inicial y escritura para comprobar 404 y que no edita otra ficha; probar contacto/desvinculación concurrentes y 40P01/40001 en el nuevo PATCH como 409 con rollback de ficha/cuenta/verificación, sin ampliar correcciones a C-05. Documentar ambas rutas.
- [x] 3.6 Comprobar minimización de listados, detalle, errores y logs con sentinelas privados; sin DNI/contacto/notas/obra social en rechazos o logs ni query de búsqueda. Verificar ausencia de DELETE/desactivación (405/422) y compatibilidad de /pacientes/{id}/turnos C-07 antes/después de editar, sin duplicar rutas. Completar documentación de este grupo y sus límites RN-58/RN-65.

## 4. Solicitudes y vinculación concurrente

- [x] 4.1 Implementar GET /solicitudes-vinculacion con estado opcional, paginación y datos mínimos; probar pendiente/resuelta/sin filtro, estado inválido, ficha coincidente y ficha vinculada sólo para vinculada, motivos/última resolución según contrato y aislamiento. Verificar 403 de Profesional/Paciente/Administrativo y documentar las proyecciones.
- [x] 4.2 Implementar vinculación con primer lock de ficha scoped, solicitud actualizada por estado leído pendiente/rechazada y ficha activa sin cuenta, todo en la misma UoW; probar feliz pendiente/rechazada, actor/fecha y motivo anterior conservado. Cubrir DNI de ficha cambiado, ficha nueva, ya vinculada, inactiva, ocupada, correo sin verificar y referencias 404, con estado final íntegro.
- [x] 4.3 Forzar dos vínculos de cuentas distintas sobre una ficha mediante barrera/eventos y dos conexiones PostgreSQL; verificar una operación exitosa, una 409, una sola cuenta y solicitud perdedora intacta. Incluir controles compatibles y demostrar locks efectivos sin sleeps ni AsyncSession compartida.
- [x] 4.4 Forzar una solicitud vinculada con dos fichas y rechazo concurrente con vínculo, preservando lectura de estado antes de escribir; verificar una resolución ganadora, una 409 y ninguna ficha/cuenta/notificación parcial. Cubrir lectura obsoleta y solicitud ya vinculada sin tocar la ficha perdedora.
- [x] 4.5 Probar contra PostgreSQL cuenta ya asociada a otra ficha mediante fixture y errores 40P01/40001 provocados dentro de transacción real; verificar 409 y rollback completo, también ante fallo entre las dos escrituras y commit. No mockear repositorios/constraints ni traducir errores de integridad ajenos.
- [x] 4.6 Exponer POST /solicitudes-vinculacion/{id}/vincular con entrada estricta, Principal/RBAC/autorizar y respuesta mínima; probar 403/404/409/422 y éxito después del commit. Documentar orden de locks, payload, selección manual de ficha, conflictos y ausencia de ganador/reintento automático en OpenAPI/README.

## 5. Rechazo y correo durable

- [x] 5.1 Implementar rechazo condicional sólo desde pendiente, con motivo opcional y actor/fecha; probar rechazo válido, ya resuelta 409 y rol/recurso ajeno sin cambios. Conservar cuenta sin ficha y última resolución, sin borrar la solicitud ni crear otro estado.
- [x] 5.2 Agregar plantilla y programación de vinculacion_rechazada dentro de la misma transacción; probar cuenta verificada con exactamente un trabajo y no verificada sin trabajo. Comprobar mensaje sin motivo/DNI/salud/credenciales y fallo de inserción que revierte solicitud y correo juntos.
- [x] 5.3 Solicitar DespacharNotificacion existente después del commit; verificar con doble del puerto que se invoca inmediatamente, con otra sesión que la resolución ya está confirmada y con Mailpit el transporte real. Probar fallo SMTP que conserva rechazo/trabajo durable y la vigencia de correo verificado, sin requerir barrido C-15 ni duplicar despachador.
- [x] 5.4 Exponer POST /solicitudes-vinculacion/{id}/rechazar con extras prohibidos y códigos aplicables; probar repetición y rechazo/vínculo concurrentes sin correo duplicado. Documentar plantilla, reintentos/entrega al menos una vez, cuerpo y límites en OpenAPI/README junto a sus pruebas.

## 6. Desvinculación y sesiones renovables

- [x] 6.1 Implementar desvinculación con primer lock de ficha, UPDATE por usuario leído y upsert de solicitud sólo si estaba vinculada; probar solicitud existente y ausente (registro DNI nuevo), origen/DNI/motivo/actor/fecha y vínculo null. Verificar que datos/turnos permanecen y no se crea correo; solicitud incompatible revierte también la ficha.
- [x] 6.2 Integrar bloqueo/recarga de usuario y revocar_sesiones dentro de esa UoW; probar refresh tokens vigentes y revocados y dos órdenes de refresh en vuelo usando eventos y conexiones reales como test_refresh_reset_race.py. Ningún reemplazo puede seguir renovable tras commit; no cambiar contraseña ni access JWT.
- [x] 6.3 Probar con el mismo JWT previo que la antigua ficha ya devuelve 404 y PATCH propio no la modifica, mientras refresh responde revocado. Cubrir cuenta sin ficha, nueva vinculación posterior y bloque cuenta null al personal tras desvincular; documentar límite conocido del access token aún vigente.
- [x] 6.4 Forzar doble desvinculación y vinculación concurrente con desvincular sobre la misma ficha; comprobar una sola desvinculación exitosa, otra 409 y serialización sin dos cuentas. Verificar escritura condicional obsoleta y rollback ante conflictos, sin imponer un ganador entre acciones distintas.
- [x] 6.5 Exponer POST /pacientes/{id}/desvincular y probar motivo ausente/vacío/extras 422, sin cuenta 409, id ajeno/inexistente 404, roles 403 y fallos de cada paso/flush/commit con reversión íntegra. Documentar operación, estados, revocación, falta de correo y atomicidad en OpenAPI/README.

## 7. Reactivación

- [x] 7.1 Implementar reactivación con lock inicial de ficha y UPDATE activo=false; probar inactiva→activa sin tocar otros datos/turnos, ya activa 409 y existencia scoped 404. Verificar desde otra sesión que los rechazos no cambian datos.
- [x] 7.2 Forzar dos reactivaciones y competencia con vínculo usando conexiones independientes: una reactivación exitosa/otra 409 y vínculo final conforme al orden serial, sin dos cuentas ni escrituras parciales. Comprobar que la ficha reactivada queda elegible para vincular.
- [x] 7.3 Exponer POST /pacientes/{id}/reactivar sin motivo ni campos de negocio; probar rol 403, extras 422 y sin cuerpo o cuerpo vacío válido. Verificar que no exista ruta de desactivación ni escritura activo por PATCH y documentar la ausencia de registro propio/correo según SU-44/47.

## 8. Recorridos e integración del change

- [x] 8.1 Recorrer con APIs C-05/C-08 los casos de vínculo equivocado y ficha correcta ocupada de RN-63: registrar/verificar, consultar cuenta/solicitud, desvincular/rechazar y vincular o crear la ficha correcta. Verificar salida completa y preservación de cada ficha/turnos y de la solicitud de la cuenta desplazada.
- [x] 8.2 Recorrer ficha inactiva y tercero registrado primero con DNI nuevo: reactivar/vincular o desvincular/corregir/vincular; conservar turnos y verificar lectura con JWT previo. En la base actual, comprobar el orden manual de cancelación C-07 ya disponible antes de corregir contacto; no automatizarlo ni agregar C-09/C-13/C-21 al alcance. Documentar los cuatro recorridos y límites.
- [x] 8.3 Ejecutar suites completas `uv run pytest -m "not integration"` y `uv run pytest -m integration` con PostgreSQL/Mailpit reales y reloj de fixtures inyectado, sin omisiones no justificadas. Conservar resultados exactos y evidencia RED/GREEN/triangulación/refactor por tarea; verificar regresiones C-04/C-05/C-07 y head único sin migraciones nuevas.
- [x] 8.4 Trazar los 17 requisitos y todos los escenarios de los tres deltas a pruebas/OpenAPI/documentación, revisar alcance y riesgos residuales, ejecutar `openspec validate c-08-patient-records --strict --no-interactive` y `git diff --check`. Entregar diferencias y matriz de evidencia antes de solicitar cierre; no confundir status de artefactos con tareas implementadas.

## Workflow follow-up

- Apply y verificación ejecutados; evidencia y límites disponibles para revisión en [evidence.md](evidence.md).
- Archivar, sincronizar specs principales, marcar C-08 finalizado y hacer commit/push sólo cuando se solicite tras la implementación verificada.
