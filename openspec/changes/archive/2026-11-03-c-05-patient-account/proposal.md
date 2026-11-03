# Proposal

## Why

El sistema necesita que los pacientes puedan crear su cuenta, verificar su correo y recuperar su contraseña sin intervención del personal, y que cada correo se despache con fiabilidad. Sin este change no hay forma de que un paciente ingrese al sistema ni que el barrido envíe notificaciones.

## What Changes

- **Nuevo endpoint** `GET /api/v1/publico/aviso-privacidad` — sirve el texto y la versión del aviso de privacidad (Ley 25.326) que el frontend muestra antes del registro; no requiere token; el consultorio lo resuelve `consultorio_sin_token`.
- **Nuevo endpoint** `POST /api/v1/auth/registro` — crea `usuario` (rol `paciente`) y ficha `paciente` (o `solicitud_vinculacion` si el DNI ya existe), exige `acepta_aviso_privacidad: true` y que `aviso_privacidad_version` coincida con la vigente; guarda fecha y versión en la cuenta; responde igual exista o no el DNI; aplica límite de solicitudes por origen con HMAC en `intento_registro`.
- **Nuevo endpoint** `POST /api/v1/auth/verificar-email` — valida token de un solo uso y marca `email_verificado`; el consultorio sale de la fila del token (RN-59).
- **Nuevo endpoint** `POST /api/v1/auth/reenviar-verificacion` — genera un nuevo token y despacha el correo de verificación; el consultorio sale de `consultorio_sin_token`.
- **Nuevo endpoint** `POST /api/v1/auth/recuperar-password` — acepta un correo y responde igual exista o no (RN-05); programa correo de recuperación.
- **Nuevo endpoint** `POST /api/v1/auth/restablecer-password` — valida token de un solo uso, actualiza la contraseña (hasheada con Argon2), revoca todas las sesiones activas; el consultorio sale de la fila del token (RN-59).
- **Nuevo endpoint** `PATCH /api/v1/auth/cambiar-password` — exige la contraseña actual; protegido por JWT.
- **Nuevo endpoint** `PATCH /api/v1/auth/actualizar-cuenta` — actualiza teléfono y/o correo del paciente; cambiar el correo lo marca no verificado y despacha verificación; protegido por JWT.
- **Nuevas migraciones Alembic**: tabla `solicitud_vinculacion`, tabla `notificacion` (con enum de diez tipos, `estado` y `reclamada_en`; sin FK a `turno` aún), tabla `intento_registro`.
- **Puerto `EnviadorCorreo`** y **adaptador SMTP** (`aiosmtplib`, 587 STARTTLS) con plantillas de `verificacion_email` y `recuperacion_password`.
- **Caso de uso `DespacharNotificacion`** — reclamación por fila (`SELECT … FOR UPDATE SKIP LOCKED`), transición `programada → enviando` en transacción corta, envío fuera de transacción, resultado en segunda transacción corta condicionada a `reclamada_en`; entrega al menos una vez (RN-61); tope diario con alerta al 80 %.
- **Tabla `intento_registro`**: guarda HMAC del origen (nunca la IP), purga automática a las 24 h; responde 429 al superar el límite.

## Capabilities

### New Capabilities

- `patient-registration`: Registro público de paciente con aviso de privacidad, ficha o solicitud de vinculación, verificación de correo, reenvío y límite de solicitudes por origen.
- `password-recovery`: Recuperación y restablecimiento de contraseña con token de un solo uso y revocación de sesiones.
- `account-self-service`: Cambio de contraseña con la actual y actualización de teléfono/correo con re-verificación.
- `notification-dispatch`: Despacho idempotente de notificaciones por correo (puerto + adaptador SMTP, reclamación por fila, tope diario, plantillas de cuenta).

### Modified Capabilities

- `core-data-models`: Se agregan las tablas `solicitud_vinculacion`, `notificacion` e `intento_registro` (con sus modelos SQLAlchemy y migraciones Alembic); se amplía el modelo `usuario` con los campos `aviso_privacidad_aceptado_en` y `aviso_privacidad_version` si no existen aún (ya están en la spec de datos, pero la migración y el modelo pertenecen a este change).
- `user-authentication`: El flujo de login ya cubre la verificación de `email_verificado` para pacientes; este change agrega los flujos que crean esa condición (registro, verificación, recuperación, restablecimiento) y el autoservicio de cuenta.

## Impact

- **Backend**: nuevos routers `auth` (amplía el existente de C-03), `publico` y casos de uso en `app/application/`; nuevos adaptadores en `app/infrastructure/`; puerto `EnviadorCorreo` en `app/domain/ports/`; tres migraciones Alembic (`solicitud_vinculacion`, `notificacion`, `intento_registro`).
- **Dependencias Python**: `aiosmtplib` (ya en pyproject o se agrega); plantillas en texto plano (sin motor de plantillas externo).
- **Variables de entorno nuevas**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `EMAIL_VERIFICATION_TTL_HOURS`, `PASSWORD_RESET_TTL_MINUTES`, `NOTIFICATION_MAX_ATTEMPTS`, `NOTIFICATION_CLAIM_TTL_SECONDS`, `NOTIFICATION_DAILY_LIMIT`, `REGISTRO_MAX_SOLICITUDES_POR_ORIGEN`, `REGISTRO_VENTANA_MINUTOS`, `TRUSTED_PROXY_HOPS`, `FRONTEND_BASE_URL`.
- **Tests**: adaptador SMTP probado contra Mailpit; doble del puerto `EnviadorCorreo` en tests unitarios; tests de repositorio contra PostgreSQL real; `intento_registro` con HMAC sin exponer la IP.
- **Governance**: CRÍTICO — maneja contraseñas (Argon2), tokens de un solo uso, correos con enlaces de seguridad y datos personales (Ley 25.326).
