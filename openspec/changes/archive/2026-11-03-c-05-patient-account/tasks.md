# Tasks

Bloqueo de integración: falta contenedor PostgreSQL/Mailpit. Las dos fallas preexistentes de test_logging_server.py fueron corregidas con autorización del usuario; baseline final unit/API: 216 pruebas pasando. Ver design.md, Verification status y actualización posterior. Cada comportamiento exige baseline verde, RED ejecutado, GREEN, triangulación y REFACTOR con ejecución y evidencia.

## 1. Entorno y configuración

- [x] 1.1 Restablecer baseline verde tras revisar por separado las fallas preexistentes y disponer PostgreSQL/Mailpit en contenedores; verificar `uv run pytest tests/unit tests/api -q` y las pruebas de integración existentes con TEST_DATABASE_URL, documentando resultados y sin usar SQLite.
- [x] 1.2 Incorporar aiosmtplib y configuración de correo, TTL, límites y cupos con pruebas RED/GREEN de valores válidos e inválidos (cupo igual/mayor al total, ventana mayor a 1440 y timeout mayor/igual al TTL); actualizar uv.lock, .env.example y README y comprobar que no agrega secretos obligatorios a seed/migrate.

## 2. Persistencia de cuenta y correo

- [x] 2.1 Crear modelo/migración solicitud_vinculacion encadenada al head existente; verificar en PostgreSQL campos, unicidad por cuenta, DNI normalizado, estados, índice de consulta y rechazo de referencias inválidas conforme core-data-models; incluir tests y documentación del esquema.
- [x] 2.2 Crear modelo/migración notificacion con diez tipos, canales, estados, índices y CHECK de reclamación; verificar estados válidos e inválidos en PostgreSQL, turno_id nullable sin nueva FK y ausencia de ciclo; documentar el contrato para C-08/C-15.
- [x] 2.3 Crear modelo/migración intento_registro e índices de ventana/retención; verificar origen HMAC nullable, aislamiento por consultorio y upgrade/downgrade/re-upgrade con un único head en PostgreSQL.

## 3. Aviso y registro

- [x] 3.1 Copiar aviso/versión de KB 13 y servir GET publico/aviso-privacidad; verificar sustitución de los tres datos del consultorio y detección de marcadores en preparación production (incluida dirección nula), documentando su carácter borrador.
- [x] 3.2 Implementar puerto/límite PostgreSQL y PurgarIntentosRegistro antes de validar el cuerpo; verificar límite por origen/global, 429 sin nueva fila, conservación tras validación/transacción fallida, ventana, HMAC sin dirección en logs, purga a 24 h y reglas de TRUSTED_PROXY_HOPS con tests de comportamiento.
- [x] 3.3 Implementar registro atómico usuario/ficha o solicitud/token/notificación; verificar consentimiento/versiones, extra=forbid, contraseña mínima/hash, normalización y duplicados; comprobar DNI nuevo/existente y dos registros concurrentes con misma respuesta, una ficha y una solicitud; documentar endpoint y respuestas.

## 4. Transporte y despacho durable

- [x] 4.1 Implementar EnviadorCorreo, plantillas de verificación/recuperación con fragmento token y adaptador EmailMessage/aiosmtplib; verificar mensajes sin datos sensibles con doble del puerto y recepción real en Mailpit, documentando SMTP STARTTLS y transporte local.
- [x] 4.2 Implementar reclamación por fila y resultado condicionado con sesión propia y envío fuera de transacción; verificar doble despacho concurrente, resultado exitoso, fallo reintentable/definitivo, CHECK de limpieza y pérdida de reclamación tardía en PostgreSQL.
- [x] 4.3 Implementar revisión de reclamación vencida y vigencia por tipo de cuenta; verificar vencida/vigente, intentos agotados, rechazo de vinculación sin correo verificado (programada y vencida), prioridad omisión/agotamiento y caída entre envío y resultado con reenvío al menos una vez; documentar riesgo de duplicados.
- [x] 4.4 Implementar cupos total/de cuenta, día local y alerta; verificar cuenta agotada con turno enviable, total agotado, enviando vigente/vencido, cambio de día, alerta 80 %, conservación de estado/intentos y resolución de omitida/fallida aun sin cupo.
- [x] 4.5 Integrar BackgroundTasks después del commit con fábrica de sesiones propia; verificar que fallo SMTP no revierte registro y queda reintentable, y que nunca se comparte AsyncSession entre solicitud y tarea; documentar reuso desde C-15.

## 5. Verificación y recuperación

- [x] 5.1 Implementar verificar-email con hash, propósito, expiración y consumo atómico; verificar tokens válido/usado/vencido/inexistente/propósito erróneo y consumo concurrente, consultorio de fila del token y rechazo de consultorio_id cliente; probar login antes/después.
- [x] 5.2 Implementar reenviar-verificacion detrás del puerto de límites PostgreSQL; verificar respuesta genérica ante cuenta inexistente/verificada/no verificada, cupos y límite por cuenta/tipo sin programar de más; documentar umbrales configurables.
- [x] 5.3 Implementar recuperar-password solo para cuenta activa y correo verificado; verificar no enumeración, normalización, límites durables y consultorio configurado, con pruebas y documentación del endpoint.
- [x] 5.4 Implementar restablecer-password y revocación transaccional de refresh; verificar consumo único/concurrente, tokens rechazados, clave corta, campos extra, aislamiento de otras cuentas, login nuevo y rechazo de refresh anteriores; documentar vigencia residual de access tokens.

## 6. Autoservicio

- [x] 6.1 Implementar cambiar-password con JWT y contraseña actual; verificar correcto/incorrecto, clave corta, extra=forbid y ausencia de secretos en respuestas/logs; documentar endpoint.
- [x] 6.2 Implementar actualizar-cuenta para paciente con vínculo vigente; verificar teléfono, correo nuevo/equivalente/duplicado, reversión completa, cuenta sin ficha y rol denegado; invalidar verificación y enlaces anteriores ante cambio de correo, programar nuevo y probar login bloqueado hasta verificar; documentar endpoint.

## 7. Verificación integral

- [x] 7.1 Ejecutar suites completas backend e infraestructura en entorno soportado, pruebas reales PostgreSQL/Mailpit y migraciones de cero con único head; verificar regresión de C-03/C-04 y registrar comandos/resultados exactos y tabla TDD por tarea en este change.
- [x] 7.2 Ejecutar `openspec validate c-05-patient-account --strict`, revisar todos los escenarios contra pruebas y comparar rutas OpenAPI con los ocho endpoints propuestos; corregir diferencias dentro del alcance y verificar que no queden secretos ni tareas parciales marcadas completas.

## Workflow follow-up

- Sincronizar especificaciones y archivar con la skill correspondiente solo después de implementar y verificar todas las tareas.
- Actualizar estado C-05 en CHANGES.md con fecha, enlace de archivo y evidencia real; no marcarlo completo por tener planificación completa.
- No hacer commit/push sin pedido del usuario.

## TDD Cycle Evidence

Cada bloque se ejecut? en secuencia RED ? GREEN ? TRIANGULATE ? REFACTOR; las pruebas de repositorios usan PostgreSQL real. Los n?meros de una suite compartida corresponden a su ejecuci?n conjunta, no se suman como suites independientes.

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Fix Windows autorizado | `tests/api/test_logging_server.py`, `tests/integration/test_seed.py` | Proceso real | 192/194 inicial | 2 fallas de cierre; seed WinError10106 | 2/2 cierre; 2/2 semilla | Request-id propio/generado y entorno aislado | Grupo/se?al Windows y SystemRoot m?nimo; PG baseline 71/71 |
| 1.1 | Unit/API e integraci?n existentes | Entorno | Baseline inicial registrado | Fallas previas reproducidas | 194/194 y 71/71 | PostgreSQL y Mailpit en contenedor | No se sustituy? la base |
| 1.2 | `tests/unit/test_account_config.py` | Unit | 194/194 | Defaults ausentes y seis l?mites inv?lidos | 22 nuevos; focal con regresi?n 59/59 | Cupos, TTL, ventana, entorno y secretos | Validadores separados; lock reproducible con tzdata Windows |
| 2.1?2.3 | `tests/integration/test_account_models.py` | PostgreSQL | 71/71 | Modelos/m?dulos ausentes | 13/13 | FK, unicidad, estados, tipos, marca, origen nulo, downgrade/re-upgrade/head | Esquema aislado en account_models, sin tiempo SQL |
| 3.1 | `tests/unit/test_privacidad.py`, `tests/integration/test_cuenta_api.py` | Unit/HTTP | 71/71 | Recurso/comprobador ausente y ruta 404 | 4 unit y suite HTTP 41/41 | Texto literal, datos completos, marcadores y production | Una fuente de texto/versi?n |
| 3.2 | `tests/integration/test_limites_cuenta.py`, `test_cuenta_api.py` | PostgreSQL/HTTP | 71/71 | Repositorio ausente; JSON malformado dejaba cero intentos | 7/7 l?mites y HTTP 41/41 | Proxy 0/1/2, inv?lido/global, purga, rollback, 422/429 | Validaci?n del cuerpo despu?s del intento confirmado |
| 3.3 | `tests/integration/test_cuentas.py`, `test_cuenta_api.py` | PostgreSQL/HTTP | 71/71 | Servicio ausente y conflictos sin traducir | Suite cuenta 23/23, HTTP 41/41 | Consentimiento, normalizaci?n, DNI simult?neo y rollback | Repositorio y traducci?n segura de conflicto |
| 4.1 | `tests/unit/test_correo.py`, `tests/integration/test_smtp_mailpit.py` | Unit/SMTP real | Configuraci?n verde | Imports, error privado y timeout | 8 unit + 2 Mailpit | Dos plantillas, TLS/local, auth, fallos y timeout | Timeout total y errores saneados |
| 4.2?4.4 | `tests/integration/test_notificaciones.py` | PostgreSQL | Modelos verdes | M?dulo, reintentos, cupos y alerta | 33/33 | Concurrencia, TTL exacto, ca?da, resultado tard?o, cupos, d?a local y 80 % | Cierre condicional de reclamaci?n compartido |
| 4.5 | `tests/integration/test_cuenta_api.py` | HTTP/PostgreSQL | Modelo/despacho verdes | Flujo HTTP ausente | 41/41 HTTP | Commit previo y fallo SMTP sin reversi?n | Capturar CID antes de un rollback que expira ORM |
| 5.1?5.3 | `tests/integration/test_cuentas.py`, `test_cuenta_api.py` | PostgreSQL/HTTP | Cuenta verde | M?todos ausentes | 23/23 cuenta y 41/41 HTTP | Usado/vencido/prop?sito, consumo concurrente, tenant, respuesta gen?rica y l?mites | Usuario antes de token, cuota por prop?sito |
| 5.4 | `tests/integration/test_refresh_reset_race.py`, `test_login_reset_race.py`, `test_cuentas.py` | PostgreSQL concurrente | Auth/rate 13/13 | Reset era eludido por refresh/login en vuelo | Regresi?n focal 22/22 | Ambos ?rdenes de login/reset y refresh/reset; otra cuenta preservada | Orden usuario?token y emisi?n/limpieza en una transacci?n |
| 6.1?6.2 | `tests/integration/test_cuentas.py`, `test_cuenta_api.py` | PostgreSQL/HTTP | Cuenta verde | M?todos ausentes; enlace recovery anterior segu?a v?lido | 23/23 cuenta y 41/41 HTTP | Clave actual, correo equivalente/duplicado, no ficha, enlace anterior y roles | Invalidar enlaces de ambos prop?sitos al cambiar correo |
| Compatibilidad LF | `tests/infra/test_dev_secrets.py` | Bash/Linux real | Suite integral primera: 462 pasan, 3 fallan | Dos fallas CRLF; test 0003 asum?a ?ltimo head | Infra 5/5 y auth_models 5/5 | Idempotencia, permisos y revisi?n 0003 expl?cita | `.gitattributes` limita LF a scripts Bash |

CI backend incluye Mailpit; tests de las revisiones anteriores apuntan al head nuevo o a la revisi?n expl?cita que prueban, conservando el rechazo de dos heads. Verificaci?n Windows final: `uv run pytest tests/unit tests/api -q` ? **265 passed in 20.98s**. La suite Linux ?ntegra se ejecuta con fuente de solo lectura, entorno Python/cache en `/tmp`, PostgreSQL y Mailpit de la red de pruebas, sin montar el socket Docker ni tocar PostgreSQL local.

Resultado integral final: **465 passed in 98.31s** en Linux (unitarias, HTTP, PostgreSQL, Mailpit e infraestructura), sin omisiones; **265 passed in 20.98s** en Windows unit/API. OpenSpec estricto v?lido, OpenAPI verificado, ?nico head 0006_intento_registro y diff-check correcto.
