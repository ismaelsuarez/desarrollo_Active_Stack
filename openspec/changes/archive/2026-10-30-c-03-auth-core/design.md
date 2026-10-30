# Design: c-03-auth-core

## Context

El sistema cuenta con la base relacional mínima y el consultorio inicial aprovisionado (C-02), incluyendo las entidades `usuario`, `consultorio`, `refresh_token` y `token_usuario` con claves primarias de identidad (`BigInteger Identity`). Sin embargo, los endpoints de la API carecen de autenticación y autorización; las solicitudes no pueden identificarse ni restringirse según el rol del actor.

Para los motivos de negocio y alcance funcional, véase `proposal.md`. Para los requisitos contractuales de comportamiento, véanse las especificaciones delta en `specs/`.

Este diseño aborda la arquitectura técnica para la autenticación basada en JWT (PyJWT HS256), el manejo seguro de contraseñas con Argon2 (`pwdlib`), la rotación estricta de refresh tokens almacenados en cookies seguras, el control de acceso RBAC con denegación por defecto, y la defensa contra ataques de fuerza bruta y enumeración mediante la tabla relacional `intento_ingreso` (RN-09, DD-21, DD-25), respetando todas las reglas duras de arquitectura (Reglas 1, 4, 5 y 11 de `AGENTS.md`).

## Goals / Non-Goals

**Goals:**
- Implementar la emisión, verificación y ciclo de vida de tokens JWT con claims estrictamente mínimos (`sub`, `consultorio_id`, `rol`, `jti`, `iat`, `exp`), gobernados por el puerto `Reloj` inyectado (Regla Dura 4, RN-06).
- Implementar rotación atómica de `refresh_token` con detección de reuso de tokens revocados (invalidación en cascada de la cadena de sesiones), resolviendo el consultorio a partir de la fila del token en base de datos (RN-59, Regla Dura 1).
- Mitigar ataques de temporización en `POST /api/v1/auth/login` ejecutando verificación ficticia con un hash Argon2 (`DUMMY_HASH`) generado con alta entropía criptográfica (`secrets.token_hex(32)`) al iniciar la aplicación.
- Defender la API contra ataques de fuerza bruta mediante la tabla `intento_ingreso` utilizando HMAC-SHA256 con `ORIGIN_HASH_SECRET`, insertando y confirmando cada intento antes de contar en ventana y antes de verificar contraseñas, soportando nulidad segura con `IS NOT DISTINCT FROM` (RN-09, DD-25).
- Resolver la dirección IP de origen respetando `TRUSTED_PROXY_HOPS` (DD-21), tolerando hosts locales y de prueba (`testclient`).
- Prevenir la enumeración de pacientes sin verificar ejecutando el chequeo de `email_verificado` estrictamente después de validar la contraseña con éxito (RN-02).
- Proveer la entidad de dominio `Principal` y dependencias FastAPI reutilizables (`usuario_actual`, `requiere_rol`, `consultorio_sin_token`).

**Non-Goals:**
- Implementar políticas ABAC basadas en atributos dinámicos (diferido a C-04).
- Implementar flujos públicos de auto-registro de pacientes, reenvío de activación o recuperación de contraseña (diferido a C-05).
- Desplegar o requerir Redis para el almacenamiento de sesiones o contadores de tasa (PostgreSQL es la única fuente durable en esta etapa).

## Decisions

### 1. PyJWT con algoritmo simétrico HS256, claims mínimos y puerto `Reloj`

- **Decisión**: Utilizar `PyJWT` configurado estrictamente con el algoritmo simétrico `HS256`, empleando `JWT_SECRET_KEY` (mínimo 32 bytes validados en `Settings`). 
  - La generación de marcas temporales (`iat`, `exp` con TTL de 15 minutos) utilizará el puerto inyectado [`Reloj`](file:///home/devops/Documentos/utn/Metodologia_I/tpi_ssd/backend/app/domain/ports/reloj.py), en cumplimiento estricto de la **Regla Dura 4**.
  - La decodificación verificará la expiración comparando el claim `exp` contra `int(reloj.ahora().timestamp())` (utilizando `options={"verify_exp": False}` en PyJWT para no depender del reloj nativo del sistema operativo `time.time()`), permitiendo tests determinísticos sin parches de reloj (`freezegun`).
  - Los claims del token de acceso serán exclusivamente: `sub` (`str(usuario.id)`), `consultorio_id` (`int`), `rol` (`str`), `jti` (UUIDv4 `str`), `iat` (`int`), `exp` (`int`).
  Queda prohibido incluir datos personales, de contacto, DNI, nombres de pacientes o historiales clínicos en los claims (RN-06, Ley 25.326).
- **Alternativas consideradas**:
  - *python-jose*: Descartado por ser regla dura de proyecto (Regla 5) y por falta de mantenimiento activo.
  - *Verificación automática de exp en PyJWT sin puerto Reloj*: Descartado porque rompe la predictibilidad temporal y el determinismo en suites de pruebas unitarias e integración.

### 2. Argon2id vía `pwdlib`, alta entropía en `DUMMY_HASH` y orden de verificación de cuenta

- **Decisión**: Utilizar `pwdlib` con backend `argon2` para validar y hashear contraseñas (`PasswordHash.recommended()`).
  - Para mitigar ataques de temporización, al arrancar la aplicación se genera un `DUMMY_HASH = password_hash.hash(secrets.token_hex(32))`. Cuando un intento de login especifica un usuario inexistente o inactivo, se ejecuta `password_hash.verify(password_provista, DUMMY_HASH)` y se responde incondicionalmente HTTP 401 con mensaje genérico `"Credenciales inválidas"`. El uso de un secreto aleatorio de 64 caracteres hex previene cualquier posibilidad de colisión con contraseñas enviadas por clientes.
  - Para cuentas con rol `paciente`, la comprobación de `email_verificado` (RN-02) se ejecuta **estrictamente después** de verificar con éxito la contraseña. Si la contraseña no coincide, se devuelve 401 genérico; si la contraseña es válida pero el correo no está verificado, se devuelve 403 Forbidden. Esto impide que un atacante enumere pacientes probando correos al azar.
- **Alternativas consideradas**:
  - *DUMMY_HASH con contraseña fija*: Descartado por riesgo teórico de coincidencia espuria.
  - *Verificación de email_verificado antes de la contraseña*: Descartado porque permite la enumeración de cuentas de pacientes.

### 3. Sesiones y Refresh Tokens en cookies `HttpOnly` y resolución de inquilino (RN-59)

- **Decisión**: Los tokens de renovación (`refresh_token`) serán cadenas criptográficamente aleatorias generadas con `secrets.token_urlsafe(32)`.
  - En la base de datos se almacena únicamente `token_hash = sha256(token_plano).hexdigest()` en la tabla `refresh_token`.
  - En la respuesta HTTP se envía en una cookie con directivas: `HttpOnly=True`, `SameSite="Strict"`, `Secure=cookie_secure`, `path="/api/v1/auth"`, `max_age=604800` (7 días).
  - En `POST /api/v1/auth/refresh`, el consultorio se resuelve directamente desde la fila a la que apunta el token (`refresh_token.consultorio_id`), dando cumplimiento a **RN-59** y a la **Regla Dura 1**.
  - Si una solicitud presenta un refresh token cuyo `reemplazado_por_id` o `revocado_en` ya no es nulo, se detecta ataque de reuso y se revocan inmediatamente todos los tokens activos asociados a ese `usuario_id` (`revocado_en = reloj.ahora()`), invalidando la sesión en todos los dispositivos.
  - En `POST /api/v1/auth/logout`, se extrae el token de la cookie y se marca como revocado en la base, limpiando la cookie en la respuesta, permitiendo el cierre de sesión incluso si el token de acceso de cabecera ya expiró.
- **Alternativas consideradas**:
  - *Usar consultorio_sin_token en /refresh*: Descartado porque viola RN-59 (las rutas que reciben tokens de renovación leen el consultorio de la fila persistida).
  - *Exigir token Bearer válido en /logout*: Descartado porque impediría a un usuario cerrar sesión si su token de acceso expiró tras 15 minutos de inactividad.

### 4. Tabla relacional `intento_ingreso` con inserción previa atómica y nulidad segura

- **Decisión**: Implementar la tabla `intento_ingreso` (RN-09, DD-25) mediante la migración `0003_auth_core.py`:
  - Columnas: `id` (BigInteger Identity), `consultorio_id` (BigInteger FK), `identificador_hash` (Text), `origen_hash` (Text, nullable), `creado_en` (timestamptz gobernado por `Reloj`).
  - Hashes calculados como `hmac.new(ORIGIN_HASH_SECRET, valor_normalizado.encode('utf-8'), hashlib.sha256).hexdigest()`.
  - Transaccionalidad (RN-09): **CADA intento de ingreso inserta y confirma primero su renglón en una transacción corta antes de evaluar el conteo de la ventana y antes de verificar contraseñas**. Esto garantiza que solicitudes en vuelo queden asentadas y que los intentos bloqueados prolonguen su ventana.
  - Purga oportunista: al escribir cada intento, se ejecuta `DELETE FROM intento_ingreso WHERE creado_en < reloj.ahora() - interval '24 hours'`.
  - Conteo con semántica de nulidad segura:
    - La consulta de conteo para el par utiliza `WHERE consultorio_id = :cid AND identificador_hash = :ihash AND origen_hash IS NOT DISTINCT FROM :ohash AND creado_en >= :cutoff`.
    - Si el conteo supera `LOGIN_MAX_ATTEMPTS` (5): retorno inmediato de 401 genérico sin procesar contraseñas.
    - Si `origen_hash` no es nulo y el conteo de ese origen supera `LOGIN_MAX_ATTEMPTS_PER_ORIGIN` (20): retorno inmediato de 401 genérico sin procesar contraseñas.
    - Ante un login exitoso, se eliminan los registros del par: `DELETE FROM intento_ingreso WHERE consultorio_id = :cid AND identificador_hash = :ihash AND origen_hash IS NOT DISTINCT FROM :ohash`.
- **Alternativas consideradas**:
  - *Insertar solo tras fallo de contraseña*: Descartado por contradecir RN-09 y permitir carreras concurrentes que eludan el bloqueo.
  - *Comparación simple origen_hash = :ohash*: Descartado porque en SQL `NULL = NULL` es falso, lo que permitiría eludir el conteo cuando el origen no se determina.

### 5. Resolución de IP de cliente respetando `TRUSTED_PROXY_HOPS` y entornos de prueba

- **Decisión**: Implementar la función `resolver_ip_origen(request: Request, trusted_hops: int) -> str | None` (DD-21):
  - Si `trusted_hops == 0`: se utiliza `request.client.host` si está disponible. Se permite el host de conexión directa local o de pruebas (`testclient`, `127.0.0.1`, etc.). Se descarta cualquier encabezado `X-Forwarded-For`.
  - Si `trusted_hops > 0`: se analiza `request.headers.get("x-forwarded-for")`. Se divide por comas y se toma la posición `-trusted_hops`. La dirección IP extraída de la cabecera se valida estrictamente con `ipaddress.ip_address()`. Si la cabecera falta, contiene menos entradas que `trusted_hops` o la IP es inválida, se retorna `None`.
  - Cuando se retorna `None`, `origen_hash` se almacena como `NULL` en `intento_ingreso`.
- **Alternativas consideradas**:
  - *Parsear request.client.host con ipaddress sin contemplar testclient*: Descartado porque rompe las suites de pruebas de FastAPI/Starlette con `TestClient`.

### 6. Capa de dominio: `Principal` y dependencias de autorización

- **Decisión**:
  - Modelo de dominio inmutable `Principal(usuario_id: int, consultorio_id: int, rol: RolUsuario)` en `app.domain.entities.auth`.
  - Dependencia `usuario_actual(token: str = Depends(oauth2_scheme), settings: Settings = Depends(get_settings), reloj: Reloj = Depends(get_reloj)) -> Principal`: valida firma HS256, expiración con `reloj.ahora()` y estructura, retornando 401 Unauthorized ante cualquier fallo.
  - Fábrica `requiere_rol(*roles: RolUsuario)`: evalúa `principal.rol in roles`, retornando 403 Forbidden si el rol no coincide.
  - Dependencia `consultorio_sin_token(settings: Settings = Depends(get_settings), uow: AbstractUnitOfWork = Depends(get_uow)) -> Consultorio`: consulta el consultorio activo configurado en `CONSULTORIO_ACTIVO_ID`, verificando que exista y esté activo (`activo == True`), retornando 503 o 404 si no está disponible (Regla Dura 1, RN-55, RN-59).
- **Alternativas consideradas**:
  - *Consultar la base de datos completa en cada verificación de rol*: Innecesario; el token JWT provee los claims firmados. `GET /api/v1/auth/me` sí valida que el usuario siga activo en la base de datos.

## Risks / Trade-offs

- **[Riesgo] Degradación por acumulación de filas en `intento_ingreso`** → *Mitigación*: La tabla cuenta con índice en `creado_en` y purga oportunista al escribir cada intento (`creado_en < ahora - 24h`), reutilizable por el barrido periódico en C-15.
- **[Riesgo] DoS por solicitudes concurrentes de cómputo Argon2 intensivo** → *Mitigación*: El rate limiting bloquea los intentos a nivel de base de datos antes de disparar el cálculo de Argon2 (tanto el real como el dummy) tras 5 fallos por par o 20 por origen.
- **[Riesgo] Discrepancia de Secure Cookie en desarrollo local sin HTTPS** → *Mitigación*: En `Settings`, `cookie_secure` toma por defecto `app_env != 'development'`, permitiendo pruebas HTTP locales transparentes mientras exige `Secure=True` en producción.
- **[Riesgo] Bloqueo involuntario de usuarios tras un proxy no configurado** → *Mitigación*: La variable `TRUSTED_PROXY_HOPS` está tipada y documentada en `.env.example`. Con el valor por defecto `0`, la IP se resuelve localmente sin riesgo de suplantación.

## Migration Plan

1. **Migración Alembic**: Generar `backend/migrations/versions/0003_auth_core.py` creando la tabla `intento_ingreso` con sus claves foráneas e índices compuestos.
2. **Compatibilidad hacia atrás**: La migración es puramente aditiva; no modifica esquemas ni datos existentes en `usuario`, `consultorio` o `refresh_token`.
3. **Rollback**: `alembic downgrade -1` elimina la tabla `intento_ingreso` y sus índices de manera limpia.

## Open Questions

*Ninguna*: Todos los aspectos de arquitectura y reglas de negocio (RN-02, RN-06, RN-09, RN-58, RN-59, DD-21, DD-25) han sido resueltos y confirmados en la base de conocimiento y decisiones previas.
