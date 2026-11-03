# Design

## Context

C-02 aporta usuario, paciente, token_usuario, refresh_token y el reloj; C-03 aporta credenciales, sesión, origen confiable y consultorio_sin_token. Ver proposal.md para motivación y CHANGES.md C-05 para alcance canónico. Las seis specs de este change son los contratos de aceptación. Backend únicamente; no se implementan pantallas de C-11/C-14 ni resolución de vinculación de C-08.

## Goals / Non-Goals

Implementar cuenta y correo durable reutilizando la arquitectura existente, con PostgreSQL real y TDD estricto. No incorporar un worker, Redis obligatorio, resolución de solicitudes, ciclo de notificación, barrido de C-15 ni publicación.

## Decisions

1. **Identidad y transacciones.** Routers finos con esquemas extra=forbid, dependencias RBAC y servicios/casos de uso. El Principal determina la cuenta autenticada; consultorio_sin_token determina registro/reenvío/recuperación/aviso; tokens enviados por correo determinan su consultorio desde la fila hasheada. Rechazar identidad del cliente. No agregar autorización ad hoc al router.
2. **Registro.** Dependencia de límite ejecutada antes de validar el cuerpo: en la misma sesión de solicitud cuenta la ventana, rechaza excedido sin insertar y confirma cada intento admitido antes de validar o iniciar registro. Purga las filas de más de 24 h con el reloj. Reutiliza resolver_ip_origen y HMAC de C-03. Después crea usuario y ficha con INSERT ON CONFLICT (consultorio_id,dni) DO NOTHING RETURNING; si no insertó, crea solicitud pendiente. Usuario, ficha/solicitud, hash de token y notificación se confirman juntos. Evita capturar una violación de DNI que aborte la transacción. Normaliza usuario/correo y Dni antes de buscar/escribir. Conflictos de usuario/correo revierten el registro conservando el intento confirmado.
3. **Tokens.** Aleatorios con secrets, hash SHA-256 usando utilidad de C-03 cuando corresponda; nunca token en respuesta, log o query. Verificación y recuperación consumen token con bloqueo de fila/actualización condicional y validación del propósito y vencimiento usando Reloj. Cambio de correo invalida tokens previos de verificación y recuperación para que la dirección anterior no permita verificar ni recuperar la cuenta. Restablecer revoca todos los refresh de esa cuenta en su transacción; no promete revocar access emitidos. Correo de recuperación solo a cuenta activa verificada. Registro del intento se confirma antes de parsear JSON, mediante dependencia de validación explícita con contrato OpenAPI preservado.
4. **Límites de reenvío/recuperación.** Puerto de límites con implementación PostgreSQL mediante tokens/notificaciones recientes; defaults de diseño: tres envíos por cuenta y tipo en quince minutos, configurables con ACCOUNT_EMAIL_LIMIT y ACCOUNT_EMAIL_WINDOW_MINUTES. No crear almacén de direcciones ni habilitar Redis. Respuesta genérica aun para cuentas no elegibles y limitadas, sin programar más correos. Los límites del registro usan nombres canónicos REGISTRATION_LIMIT_PER_ORIGIN/GLOBAL/WINDOW_MINUTES, no los nombres preliminares españoles de proposal.md.
5. **Aviso.** Copiar literalmente texto y versión de KB 13 a recurso local de backend; interpolar solamente nombre, dirección y teléfono del consultorio. Conserva marcadores si faltan datos y verifica preparación production sin marcadores. No convertir el borrador técnico en un aviso legal aprobado. Registro compara contra esa misma versión.
6. **Correo.** Puerto de dominio EnviadorCorreo y adaptador con EmailMessage + aiosmtplib; texto plano, enlaces con fragmento token. Primera tentativa por BackgroundTasks después del commit usando sesión propia, nunca compartiendo AsyncSession. Timeout SMTP de diseño: 30 s; TTL de reclamación: 120 s; máximo: tres intentos, configurables y validados. SMTP_STARTTLS=true/587 por defecto y false/1025 para Mailpit. Variables opcionales con defaults de desarrollo: host mailpit, remitente de prueba y credenciales opcionales; producción configura su proveedor en C-20. SMTP_PASSWORD es SecretStr. Actualizar pyproject/uv.lock, .env.example y README con instalación/verificación.
7. **Reclamación.** DespacharNotificacion toma id y consultorio, abre transacción corta con SELECT FOR UPDATE SKIP LOCKED; filtra email y vencimiento. Revisa vigencia por tipo, intentos, cupos; confirma enviando/reclamada_en/intentos antes del transporte. Segunda transacción actualiza WHERE id/consultorio/estado/reclamada_en propia. Pérdida de reclamación descarta resultado. Error guardado es categoría segura sin secretos ni destinatario. Cada salida limpia la marca. Sin candados globales ni de sesión.
8. **Cupos.** Nombres canónicos EMAIL_DAILY_LIMIT=500, EMAIL_DAILY_LIMIT_ACCOUNT=150 y EMAIL_DAILY_ALERT_RATIO=0.8 (no NOTIFICATION_DAILY_LIMIT del borrador). Cuenta enviados dentro del día local convertido a límites UTC y enviando no vencidos, siempre por consultorio/email; cuenta cupo de cuenta solo en sus tres tipos. Omisión/fallo por reclamación vencida no consumen cupo. Concurrentes pueden superar el cupo en solicitudes en vuelo, riesgo aceptado en KB 04; no introducir un candado global para evitarlo.
9. **Migraciones.** Tres revisiones encadenadas al único head actual: solicitud_vinculacion, notificacion e intento_registro. BIGINT identidad según DD-23, TIMESTAMPTZ, TEXT+CHECK e índices de KB 04; sin defaults SQL de tiempo. La aceptación del aviso ya existe en usuario: no duplicarla. Aunque la rebanada C-00 ya creó turno, mantener la nueva columna notificacion.turno_id nullable sin FK según contrato C-05; C-07 integra su FK. No agregar ciclo hasta C-15. Probar upgrade/downgrade/re-upgrade contra PostgreSQL vacío, sin autogenerate para reglas específicas.

## Risks / Trade-offs

- Fuga residual de pertenencia de DNI después de verificar y reservar → mitigación RN-62 mediante solicitudes y límite; no afirmar que registro elimina toda inferencia.
- SMTP puede enviar dos veces si cae el proceso o expira reclamación → entrega al menos una vez, resultado condicionado y máximo de intentos.
- Proveedores, permisos SMTP y proxies publicados pendientes → C-20, no bloquean el desarrollo local con Mailpit.
- Aviso borrador y datos incompletos → no usar con pacientes reales hasta revisión prevista y control de marcadores.

## Migration Plan

Ejecutar baseline antes de editar producción. Por cada comportamiento: RED ejecutado, GREEN, al menos dos casos y REFACTOR con tests. Ejecutar migraciones sobre base temporal de contenedor y un único head. Rollback elimina solo tablas nuevas en orden inverso antes de desplegar consumidores posteriores; una vez con datos, requiere respaldar solicitudes/notificaciones antes de downgrade. No tocar archivos archivados ni fix_changes.py ajeno.

## UI Mockups

Decision: no (no UI). Solo API, persistencia y SMTP; pantallas corresponden a otros changes.

## Verification status — 2026-11-02

Registro histórico del arranque de esta implementación; el resultado final está al final de esta sección.

Baseline ejecutado antes de producción: `cd backend; uv run pytest tests/unit tests/api -q` → **192 passed, 2 failed in 16.50s**. Fallan ambas parametrizaciones de `tests/api/test_logging_server.py::test_production_server_logs_are_json_redacted_and_correlated` (None, abc-123): el proceso devuelve 1 tras terminate(), pero el test acepta 0 o -15. Se observó en Windows; no se investigó ni probó la causa raíz. Son fallas preexistentes: el TDD estricto exige detener apply y no arreglarlas dentro de C-05 sin revisión.

Además, no hay Docker/Podman/WSL disponible; PostgreSQL local existe pero no reemplaza el contenedor exigido por la regla dura 3. No se ejecutaron pruebas PostgreSQL/Mailpit. Refresh del índice falló por ejecutable gentle-ai ausente; se usó índice y SKILL.md locales sin instalar ni sustituir skills. No se escribió código de producción ni se marcó ninguna tarea de implementación completa. Planificación completa no equivale a autorización técnica para saltar este bloqueo.

### Actualización posterior a autorización del usuario

El usuario autorizó corregir las dos pruebas previas. Se reprodujeron ambas fallas y se cambió solo el control de proceso del test: Windows crea grupo propio y envía CTRL_BREAK_EVENT, que Uvicorn maneja como SIGBREAK. Uvicorn completa shutdown y vuelve a emitir la señal; el proceso Python devuelve 3. Se admite ese resultado solo en Windows conservando todas las aserciones de lifecycle, JSON, correlación y redacción. Linux mantiene SIGTERM y su código esperado. Prueba focal: 2 passed in 6.41s; baseline posterior: 194 passed in 12.47s.

Se completó tarea 1.2 con 22 casos unitarios nuevos de configuración, aiosmtplib 5.1.3, lockfile, .env.example y README. La sincronización reproducible detectó tzdata previamente instalada pero no declarada: `uv sync --locked` la quitaba y fallaban cuatro imports por ZoneInfoNotFoundError en Windows. Ahora tzdata es dependencia condicionada a win32, sin cambios de lógica del reloj. `uv sync --locked` pasa y suite final `uv run pytest tests/unit tests/api -q`: **216 passed in 12.53s**. Configuración no agrega secretos obligatorios a SeedSettings/DatabaseSettings. El bloqueo restante es disponibilidad de PostgreSQL/Mailpit en contenedores; no se probó ni implementó persistencia/SMTP/endpoints y C-05 sigue abierto con 20 tareas pendientes.

### Verificación final — 2026-11-03

El usuario autorizó configurar Docker y corregir las incompatibilidades de pruebas. Docker Desktop 4.97, WSL 2.7.14 y engine 29.9.2 quedaron disponibles. Se levantó un proyecto de pruebas separado con PostgreSQL 17 en memoria temporal y Mailpit v1.30.1; no se tocó PostgreSQL local ni datos reales. El baseline de integración terminó en 71/71 después de conservar SystemRoot en el entorno mínimo de la prueba CLI de semilla en Windows.

La revisión concurrente reprodujo dos fallas de revocación: un refresh o login en vuelo podían emitir una sesión después del reset. Ambos se ordenan ahora mediante bloqueo de usuario mantenido hasta emitir/confirmar; refresh recarga y bloquea su fila después del usuario, y login limpia intentos sin commit intermedio. Las pruebas controlan ambos ordenamientos, doble refresh y el aislamiento de otra cuenta. El cambio de correo invalida también enlaces de recuperación anteriores. Se verificaron los ocho contratos HTTP, los seis grupos de especificaciones y cada escenario mediante las suites de cuenta, HTTP, modelos, límites, despacho y transporte; el detalle de TDD está en tasks.md.

Resultados finales:

- Windows: `cd backend; uv run pytest tests/unit tests/api -q` → **265 passed in 20.98s**.
- Linux, imagen de prueba construida con la etapa build del Dockerfile y lockfile: `docker exec active-stack-c05-runner uv run pytest -q -o cache_dir=/tmp/c05pytest-cache` → **465 passed in 98.31s**, sin omisiones. Incluye los tests Bash/POSIX, PostgreSQL real, Mailpit real, migraciones desde cero, downgrade/re-upgrade y único head `0006_intento_registro`.
- El runner tuvo fuente de solo lectura y Python/cache en `/tmp`, unido únicamente a la red de pruebas, sin socket Docker montado. `uv sync --locked` pasó en Windows y Linux.
- Primera suite Linux: 462 pasaron y tres fallaron: dos por CRLF del checkout de scripts y otra porque la prueba de revisión 0003 suponía que seguía siendo el último head. Se corrigieron finales LF sin cambios semánticos y se hizo explícita la revisión de esa prueba. Focales posteriores: infraestructura 5/5 y auth_models 5/5; luego la suite completa pasó.
- `openspec validate c-05-patient-account --strict` y `git diff --check` pasan. OpenAPI expone ocho endpoints con entradas cerradas y contraseñas writeOnly. El handler 422 no devuelve input ni contexto privado.

No hay cambios visuales, despliegue publicado, correos reales ni commits de esta sesión. Los trabajos de C-08/C-15/C-20 siguen fuera de este change. Los tests temporales se detienen al cerrar la verificación; el aviso permanece como borrador conforme KB 13. El ejecutable gentle-ai sigue ausente, de modo que no se pudo regenerar el índice local de skills; se leyeron sus SKILL.md locales y no se instalaron sustitutos.
