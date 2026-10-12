# Arquitectura Propuesta

Propuesta alineada con la prioridad de **mantenibilidad** y con el stack obligatorio. Las decisiones que el usuario no confirmó están registradas como supuestos en [09](09_decisiones_y_supuestos.md) y se indican con su código SU.

## Patrones aplicados

| Patrón | Dónde se usa | Por qué |
|--------|--------------|---------|
| Arquitectura en capas / hexagonal (puertos y adaptadores) | Backend: `domain`, `application`, `infrastructure`, `api` (SU-03) | Aísla las reglas de negocio de FastAPI, SQLAlchemy, SMTP y Redis (opcional); facilita las pruebas y cambiar un adaptador sin tocar las reglas. |
| Casos de uso (servicios de aplicación) | `application/use_cases` | Cada acción del sistema (reservar, cancelar, liberar) es una unidad con una entrada y una salida explícitas. |
| Repositorio | `infrastructure/db/repositories` con interfaces en `application/ports` | El dominio no conoce SQLAlchemy. |
| Unidad de trabajo (transacción por caso de uso) | `infrastructure/db/uow.py` | Operaciones atómicas como reprogramar (reservar el nuevo horario y liberar el anterior). |
| Funciones de política (ABAC) | `domain/policies` | Reglas de acceso legibles, puras y probadas. Ver [11](11_politicas_de_acceso_abac.md) y DD-04. |
| Entidades y objetos de valor | `domain/entities`, `domain/value_objects` | Estado del turno, intervalo de tiempo, teléfono normalizado y DNI con sus invariantes. |
| Máquina de estados del turno | `domain/entities/turno.py` | Centraliza las transiciones de RN-18. |
| Inyección de dependencias | `api/deps.py` con `Depends` de FastAPI | Construye casos de uso con sus puertos concretos; facilita pruebas con dobles. |
| DTO / esquemas Pydantic | `api/schemas` | Valida la entrada y define el contrato OpenAPI sin exponer entidades. |
| Bandeja de notificaciones (outbox) | Tabla `notificacion` más barrido en proceso | La base de datos es la fuente de verdad de lo programado; Redis, si existe, es auxiliar y no es crítico para no perder recordatorios (SU-26). |
| Barrido periódico idempotente | Barrido de hitos dentro de la API, disparado por un puerto `Planificador` | Resiliente a reinicios, a la suspensión del servicio y a disparos repetidos; evita un trabajo programado por turno. |
| Puertos de servicios externos | `Planificador`, `EnviadorCorreo`, `Reloj` | El disparador del barrido y el envío de correo se pueden cambiar (HTTP externo o bucle propio; SMTP o API HTTPS) sin tocar los casos de uso. |
| Contenedor / presentacional | Frontend: contenedores obtienen datos y manejan estado; componentes presentacionales solo pintan (SU-04) | Mantenibilidad de la interfaz y pruebas de componentes simples. |
| Diseño atómico | `components/atoms`, `molecules`, `organisms`, `templates` (SU-04) | Reutilización y coherencia visual. |
| Organización por funcionalidad (features) | Frontend: `features/<modulo>` | Cada épica concentra sus pantallas, hooks y llamadas a la API. |

## Estructura de directorios

```text
tpi_ssd/
├── knowledge-base/                  # esta base de conocimiento
├── docker-compose.yml               # servicios locales y de despliegue (ver 12)
├── .env.example                     # variables de entorno de ejemplo, sin secretos
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini                  # migraciones de esquema (SU-29)
│   ├── alembic/versions/
│   ├── tests/
│   │   ├── unit/                    # dominio y políticas
│   │   ├── integration/             # repositorios y restricción de exclusión contra PostgreSQL
│   │   └── api/                     # endpoints
│   └── app/
│       ├── main.py                  # crea la app FastAPI, routers y middlewares
│       ├── core/                    # configuración, logging, errores comunes
│       │   ├── config.py            # lectura de variables de entorno
│       │   └── logging.py
│       ├── domain/                  # reglas de negocio puras, sin frameworks
│       │   ├── entities/            # turno, paciente, profesional, prestacion...
│       │   ├── value_objects/       # intervalo, telefono, dni, estado_turno
│       │   ├── policies/            # funciones ABAC (consultorio, turno, sobreturno...)
│       │   ├── services/            # disponibilidad, hitos, indicador de ausentismo
│       │   └── errors.py
│       ├── application/             # casos de uso y puertos
│       │   ├── use_cases/           # reservar_turno, cancelar_turno, liberar_turno...
│       │   ├── ports/               # repositorios, enviador_correo, planificador, reloj, generador_tokens
│       │   └── dto/
│       ├── infrastructure/          # adaptadores concretos
│       │   ├── db/                  # modelos SQLAlchemy, repositorios, uow, sesión
│       │   ├── email/               # adaptador SMTP (EmailMessage + aiosmtplib) y plantillas de correo
│       │   ├── whatsapp/            # constructor de mensajes y enlaces wa.me
│       │   ├── security/            # hash Argon2 (pwdlib), emisión y validación de JWT (PyJWT)
│       │   ├── redis/               # opcional: límites de intentos y usos auxiliares
│       │   └── jobs/                # barrido idempotente, reclamación por fila en PostgreSQL y adaptadores de Planificador
│       └── api/
│           ├── deps.py              # autenticación, consultorio_sin_token, fábricas de dependencias RBAC, casos de uso
│           ├── internal/            # POST /internal/barrido (secreto compartido, fuera de la API pública)
│           ├── schemas/             # Pydantic
│           └── v1/routers/          # auth, publico, turnos, pacientes, agenda...
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── Dockerfile
    └── src/
        ├── main.tsx
        ├── app/                     # enrutado, proveedores, guardas por rol
        ├── components/              # diseño atómico
        │   ├── atoms/
        │   ├── molecules/
        │   ├── organisms/
        │   └── templates/
        ├── features/                # un módulo por épica
        │   ├── auth/                # registro, verificación, ingreso, recuperación
        │   ├── reserva/             # enlace público, disponibilidad, reserva
        │   ├── turnos/              # mis turnos, gestión de Recepción
        │   ├── agenda/              # agenda del profesional y de Recepción
        │   ├── pacientes/
        │   ├── configuracion/       # profesionales, horarios, bloqueos, prestaciones
        │   ├── notificaciones/      # lista de WhatsApp y envíos fallidos
        │   └── indicadores/         # ausentismo
        ├── pages/                   # composición de pantallas por ruta
        ├── services/                # cliente HTTP y manejo del token
        ├── shared/                  # hooks, utilidades, tipos, formato de fechas
        └── tests/
```

Cada feature del frontend separa **contenedores** (obtienen datos, manejan estado y eventos) de **componentes presentacionales** (reciben props y pintan).

## Capas del backend y reglas de dependencia

```text
api  ──►  application  ──►  domain
 │             │                ▲
 └─────────────┴──► infrastructure (implementa los puertos de application)
```

- `domain` no importa nada de `application`, `infrastructure` ni `api`.
- `application` depende de `domain` y de **interfaces** (puertos); no importa SQLAlchemy ni SMTP.
- `infrastructure` implementa los puertos; es la única capa que conoce SQLAlchemy, Redis (si se usa), SMTP y los detalles de JWT.
- `api` traduce HTTP a casos de uso y excepciones de dominio a códigos de respuesta.

## Trabajos en segundo plano

Los trabajos programados se ejecutan como un **barrido idempotente dentro del proceso de la API**, sin proceso persistente aparte ni dependencia de Redis (SU-01, SU-26, revisadas el 2026-10-06 con `discovery/exploracion-tecnica.md`). La razón: entre los proveedores gratuitos verificados no hay un stack con API, PostgreSQL, Redis y un proceso siempre activo sin tarjeta, y el servicio web gratuito de Render se duerme a los 15 minutos. Ver [12](12_devops_y_despliegue.md).

Arquitectura base: un disparador HTTP externo llama cada 5 minutos a `POST /internal/barrido`, autenticado con un secreto compartido; el puerto `Planificador` oculta ese disparador. En local o en una VM con Compose, un bucle `asyncio` propio detrás del mismo puerto ejecuta el mismo caso de uso. Si se exigiera una librería de trabajos, ARQ es el mejor ajuste técnico (nativa en asyncio), asumiendo que está en modo de mantenimiento desde 2025-10-18; no se adopta en la v1.

| Trabajo | Disparador | Acción | Idempotencia |
|---------|------------|--------|--------------|
| Despacho de notificaciones | Barrido periódico | Envía correos `programada` vencidos, revisa las reclamaciones `enviando` vencidas y reintenta los fallidos de forma acotada; la vigencia de cada fila depende de su tipo ("Vigencia por tipo" en [04](04_modelo_de_datos.md)). | `UNIQUE (turno_id, tipo, canal, ciclo)`, reclamación por fila (estado `enviando`) y estado de la notificación. Entrega al menos una vez (RN-61). |
| Solicitud de confirmación (T-48 h) | Barrido de hitos | Para turnos `pendiente` en su ciclo actual, crea correo y mensaje de WhatsApp preparado. | `confirmacion_solicitada_en` y la restricción de la notificación. |
| Recordatorio (T-24 h) | Barrido de hitos | Para turnos `pendiente` y `confirmado`. En los `pendiente` advierte la liberación solo si ese turno puede liberarse de forma automática (RN-60); si no, solo pide confirmar. | `recordatorio_enviado_en`. |
| Liberación (T-12 h) | Barrido de hitos | Candidatos: turnos `pendiente`, sin marca, en su ciclo actual, a 12 horas o menos del inicio y que todavía no comenzaron. Modo automático: pasa a `liberado` si su solicitud de confirmación está `enviada` (RN-60); si no, marca `marcado_sin_confirmar_en`. Modo manual: marca `marcado_sin_confirmar_en`. Un `pendiente` que ya comenzó queda fuera de la selección (el personal lo cierra como atendido o ausente, RN-44). Un turno ya marcado en su ciclo no se vuelve a evaluar; reprogramar limpia la marca (RN-32). | Actualización condicional (estado, marca, ciclo y "no comenzó"); la fila de historial se escribe en la misma transacción solo si afectó una fila. |
| Limpieza periódica | Periódico | Borra tokens expirados de `token_usuario` y `refresh_token` y los renglones de `intento_registro` e `intento_ingreso` con más de 24 horas (DD-21, DD-25). Hasta que exista el barrido (C-15), cada inserción de un intento de ingreso (C-03) o de registro (C-05) borra al escribir los renglones vencidos de su tabla. | Operación repetible. |

Diseño del barrido:

1. El barrido se dispara cada 5 minutos desde el exterior (`POST /internal/barrido` con el secreto `SWEEP_SHARED_SECRET`) o, en local o VM, con un bucle propio (`SWEEPER_INTERVAL_SECONDS`). El intervalo debe ser lo bastante corto para respetar la precisión de los hitos de 48, 24 y 12 horas.
2. Consulta la base de datos por notificaciones y turnos cuyos hitos vencieron y procesa en lotes. La tabla `notificacion` es la fuente de verdad. Cada fila candidata se reclama por separado con `SELECT ... FOR UPDATE SKIP LOCKED` (DD-17): en esa transacción corta la notificación pasa de `programada` a `enviando` con la hora de reclamación (`reclamada_en`) y se confirma antes de enviar. Antes de cada reclamación que enviaría un correo, el barrido verifica el tope diario: con el tope alcanzado no reclama más filas de canal `email`, que siguen `programada` sin consumir intentos, ni reclama de nuevo una `enviando` vencida; el conteo suma los correos enviados del día y las reclamaciones `enviando` que no vencieron, y pasar una reclamación vencida a `omitida` o a `fallida` no pasa por el tope (conteo en [04](04_modelo_de_datos.md)). No hay un candado global del barrido: dos disparos o dos instancias pueden ejecutarse a la vez y nunca reclaman la misma fila. No se usan candados de sesión (`pg_try_advisory_lock`): no son fiables detrás del pooler de transacciones de Neon, y uno por transacción tampoco sirve porque cada transacción es corta.
3. El envío SMTP ocurre fuera de toda transacción. Después, una segunda transacción corta registra el resultado: `enviada`, o el reintento acotado (vuelve a `programada`) y `fallida` de RN-31 (transiciones en [04](04_modelo_de_datos.md)). La escritura es una actualización condicional por la reclamación propia (`WHERE estado = 'enviando' AND reclamada_en = :valor_que_fijó_este_envío`): si no afecta ninguna fila, el envío perdió la reclamación y descarta su resultado sin escribir.
4. Cada transición de un turno es una transacción corta y condicional (por ejemplo `UPDATE ... WHERE estado = 'pendiente' AND marcado_sin_confirmar_en IS NULL AND ciclo_confirmacion = :ciclo`), por lo que repetirla no duplica efectos; la fila de `turno_historial` se escribe en la misma transacción solo si la actualización afectó una fila, así que dos barridos simultáneos dejan una sola. La selección de candidatos y la actualización condicional incluyen que el turno no haya comenzado (`inicio > :ahora`, con `:ahora` del puerto `Reloj`); la liberación automática exige además que la solicitud de confirmación del ciclo esté `enviada` (RN-60).
5. Una reclamación `enviando` más vieja que `NOTIFICATION_CLAIM_TTL_SECONDS` se asume abandonada y un barrido posterior la revisa con la misma validación de vigencia que la primera reclamación, que depende del tipo ("Vigencia por tipo" en [04](04_modelo_de_datos.md): un recordatorio de un turno que ya no corresponde pasa a `omitida`; un aviso de algo ya ocurrido, incluidos el resumen de la reserva y la confirmación de la cancelación del paciente, no depende del turno), respetando `NOTIFICATION_MAX_ATTEMPTS` (al alcanzarlo, `fallida` sin reenviar) y el tope diario (solo reenvía si no se alcanzó). La entrega es **al menos una vez**: una caída entre el envío y el registro del resultado puede repetir un correo (RN-61). No se promete entrega exactamente una vez.
6. Si el disparador falla, el servicio estaba dormido o Redis (si se usa) no está disponible, los recordatorios no se pierden: están en PostgreSQL y se procesan en el siguiente barrido. Los hitos se retrasan, no se pierden.
7. Cuotas a respetar: Neon (suspensión del cómputo a los 5 minutos, 100 CU-h por mes) y Upstash (500.000 comandos por mes) si se usa; ver Q-27 en [10](10_preguntas_abiertas.md).

El barrido usa el reloj del sistema a través de un puerto `Reloj` para poder probar los hitos con tiempo simulado.

## Persistencia y migraciones

- **Acceso asíncrono:** SQLAlchemy 2.x con `create_async_engine("postgresql+asyncpg://...")` y `async_sessionmaker(engine, expire_on_commit=False)`; el motor se libera con `engine.dispose()` al cerrar. Los modelos usan `DeclarativeBase`, `Mapped[...]` y `mapped_column(...)`.
- **No solapamiento (DD-08):** la restricción de exclusión (`ExcludeConstraint` de `sqlalchemy.dialects.postgresql`, con `where`, `using` y `name`) requiere la extensión `btree_gist`. Se declara en el modelo y se **crea a mano en la migración** después de `CREATE EXTENSION IF NOT EXISTS btree_gist`, porque el autogenerate de Alembic no detecta restricciones EXCLUDE.
- **Prueba obligatoria:** un test de integración inserta dos turnos solapados del mismo profesional y espera el rechazo. La documentación de SQLAlchemy no trae un ejemplo literal con `tstzrange`, por lo que la expresión `tstzrange(inicio, fin, '[)')` con el operador `&&` debe quedar cubierta por ese test.
- **Traducción del error:** el adaptador del repositorio traduce el error de exclusión (SQLSTATE `23P01`) a "horario ocupado". **Suposición:** el código `23P01` no se verificó en fuente primaria; confirmarlo en la primera prueba de integración. El dominio no conoce el código SQL.
- **Migraciones:** Alembic con `env.py` asíncrono (`alembic init -t async`), `compare_type=True`, historia lineal con una migración por change y un único head. CI ejecuta `alembic heads` y exige un solo head; se aplica `alembic upgrade head`, nunca `heads`.

## Seguridad

- **Autenticación:** JWT firmado por el servidor con PyJWT (HS256) y los claims de RN-06 (usuario, `consultorio_id`, rol; nunca la ficha ni el identificador del paciente: el vínculo se lee de la base en cada solicitud, RN-63), siguiendo el tutorial oficial de FastAPI. Token de acceso de vida corta y sesión renovable con rotación (`refresh_token`). El almacenamiento en el navegador es un supuesto (SU-27): token de acceso en memoria y token de renovación en cookie `HttpOnly`, `Secure` y `SameSite`; si se usan cookies, se agrega protección contra CSRF en los endpoints de renovación. El frontend y la API comparten origen (DD-26 en [09](09_decisiones_y_supuestos.md)): la cookie es propia y lleva `SameSite=Strict`.
- **Contraseñas:** hash Argon2 con pwdlib (decisión DD-12), con sal; el proceso de ingreso compara contra un hash ficticio cuando el usuario no existe para igualar tiempos (práctica del tutorial oficial). Nunca en logs ni respuestas (RN-04). Política de contraseña: 8 caracteres como mínimo, sin reglas de composición (RN-04, DD-25).
- **Tokens de un solo uso** (verificación, recuperación, confirmación por enlace): aleatorios con entropía suficiente, guardados hasheados, con vencimiento y marca de uso (RN-03).
- **Autorización:** RBAC como fábricas de dependencias de FastAPI en el endpoint y ABAC como funciones de política puras invocadas desde el caso de uso (ver [11](11_politicas_de_acceso_abac.md)). Denegar por defecto.
- **Aislamiento por consultorio:** `consultorio_id` obligatorio en las tablas y en todo filtro. Los repositorios reciben `consultorio_id` desde el `Principal` (el usuario autenticado), nunca desde el cliente; no se aceptan identificadores de consultorio enviados por el cliente. Sin token, el criterio es el tipo de flujo y no el prefijo de la ruta: una ruta que recibe un token enviado por correo o de renovación (`/auth/verificar-email`, `/auth/restablecer-password`, `/turnos/confirmar-por-enlace`, `/auth/refresh`) toma el consultorio de la fila a la que apunta el token; en las demás rutas sin token (`/auth/login`, `/auth/registro`, `/auth/reenviar-verificacion`, `/auth/recuperar-password` y las lecturas públicas `/publico/*`) una única dependencia, `consultorio_sin_token`, resuelve el único consultorio activo de la v1 desde `CONSULTORIO_ACTIVO_ID` (variable obligatoria) y verifica que exista y esté activo (RN-59, DD-16).
- **Endpoint interno del barrido:** `POST /internal/barrido` exige el secreto compartido `SWEEP_SHARED_SECRET`, compara en tiempo constante y no se publica en la documentación de la API pública.
- **Validación de entrada:** esquemas Pydantic estrictos en la API; consultas parametrizadas a través del ORM; límite de tamaño de cuerpo.
- **Límite de intentos y de abuso:** limitación de los intentos de ingreso por el par cuenta y origen y por origen (RN-09, DD-25: cada intento se inserta y se confirma antes de contar, y se guarda como HMAC con `ORIGIN_HASH_SECRET` en `intento_ingreso`) y de solicitudes a los endpoints públicos de registro, recuperación y reenvío, apoyada en Redis si se despliega o en PostgreSQL si no. El registro se limita por origen (acota la fuga residual de RN-62). **Origen de los límites de registro (DD-21) y de ingreso (DD-25):** la dirección del cliente se toma del encabezado `X-Forwarded-For` confiando solo en `TRUSTED_PROXY_HOPS` saltos: el origen es la entrada que está esa cantidad de posiciones contando desde la derecha (cada proxy de confianza agrega la dirección de la que recibió la solicitud); las entradas anteriores, que el cliente puede fijar, no se usan nunca. Con `TRUSTED_PROXY_HOPS=0` (valor por defecto) el encabezado se ignora y el origen es la dirección de la conexión directa. Si el encabezado tiene menos entradas que saltos, la dirección no es válida o no hay dirección, no se determina un origen y se aplica el límite global (`REGISTRATION_LIMIT_GLOBAL`). El origen se guarda solo como HMAC-SHA256 con `ORIGIN_HASH_SECRET` en `intento_registro` e `intento_ingreso` ([04](04_modelo_de_datos.md)), con el renglón confirmado antes de la transacción del registro para que el intento cuente aunque el registro falle; la dirección en claro nunca se guarda ni se registra en logs. Los límites del registro y su ventana son las variables de abajo; los demás umbrales se definen al implementar.
- **No enumeración de cuentas:** respuestas idénticas en recuperación de contraseña (RN-05); mensajes de ingreso genéricos.
- **Transporte:** HTTPS en cualquier entorno público. El frontend y la API comparten origen (DD-26), así que CORS queda deshabilitado por defecto; `CORS_ORIGINS` existe solo para habilitar un origen adicional de forma explícita.
- **Secretos:** solo en variables de entorno, archivos de secreto (`/run/secrets/<nombre>` en Compose) o el almacén de secretos del host, nunca en el repositorio; `.env.example` no contiene valores reales. La contraseña de aplicación de SMTP, `JWT_SECRET_KEY`, `SWEEP_SHARED_SECRET` y `ORIGIN_HASH_SECRET` son secretos.
- **Datos personales:** acceso por rol y atributos, sin borrado físico, mensajes sin datos de salud (RN-54). La dirección de origen del registro solo se conserva como hash con clave, con retención de 24 horas, y sigue siendo un dato personal (Ley 25.326, RN-58). El aviso de privacidad y la aceptación en el registro están en la v1 (RN-65, DD-28); la auditoría de accesos y el circuito de derechos de la Ley 25.326 corresponden a C-21, en la segunda parte (RN-58).
- **Registro (logging):** estructurado, con identificador de solicitud; sin contraseñas, tokens ni datos personales innecesarios. Los enlaces enviados por correo llevan su token en el fragmento de la URL (`#token=...`) y la pantalla lo envía en el cuerpo de un `POST`, para que no quede en logs de acceso ni en `Referer`.
- **Documentación de API:** `/docs` y `/openapi.json` habilitados en desarrollo y restringidos en producción (SU-06).

## Variables de entorno

Los valores de ejemplo no son secretos reales. Los valores numéricos de duraciones e intervalos no están definidos en las fuentes y figuran como "a definir" (ver [10](10_preguntas_abiertas.md)).

Una variable marcada como sensible (`Y`) nunca aparece en los logs. Los logs ocultan el valor de todo campo declarado como secreto en la configuración (y la contraseña de las URL de base), sin una lista de nombres: C-01 define el mecanismo, y el change que agrega una variable sensible la declara como campo secreto y prueba que su valor se reemplaza por `***` (por ejemplo, C-03 con `ORIGIN_HASH_SECRET`).

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `APP_ENV` | Obligatoria, sin valor por defecto. Entorno de ejecución: `development`, `test` o `production`; el arranque falla si falta o si tiene otro valor | `development` / `production` | N |
| `APP_TIMEZONE` | Zona horaria por defecto: la usa la semilla para `consultorio.zona_horaria` y nada más. Las reglas de negocio usan siempre `consultorio.zona_horaria`, que es la única fuente una vez sembrado el consultorio | `America/Argentina/Buenos_Aires` | N |
| `DATABASE_URL` | Obligatoria. Conexión a PostgreSQL de la API (controlador asíncrono asyncpg; en producción, Neon) | `postgresql+asyncpg://usuario:clave@db:5432/turnos` | Y |
| `MIGRATIONS_DATABASE_URL` | Opcional. Conexión que usan las migraciones; si falta, usan `DATABASE_URL`. En producción apunta a la conexión directa de Neon cuando `DATABASE_URL` pasa por el pooler | `postgresql+asyncpg://usuario:clave@host-directo/turnos` | Y |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales del contenedor de PostgreSQL (solo Compose) | `turnos` / `cambiar` / `turnos` | Y (contraseña) |
| `REDIS_URL` | Conexión a Redis (opcional; solo si se despliega) | `redis://redis:6379/0` | N |
| `CONSULTORIO_ACTIVO_ID` | Obligatoria, sin valor por defecto. Identificador del único consultorio activo de la v1, que el servidor usa en los flujos sin token (RN-59); no lo envía el cliente. La agrega C-02 a `Settings` | `1` | N |
| `JWT_SECRET_KEY` | Obligatoria. Clave de firma del JWT, de 32 bytes o más (el mínimo de HS256); el arranque falla con una clave más corta | cadena aleatoria de 32 bytes o más | Y |
| `JWT_ALGORITHM` | Algoritmo de firma (PyJWT) | `HS256` | N |
| `JWT_ACCESS_TTL_MINUTES` | Vida del token de acceso; es también el tiempo máximo que conserva acceso un usuario desactivado (DD-25) | `15` (por defecto) | N |
| `JWT_REFRESH_TTL_DAYS` | Vida del token de renovación | `7` (por defecto) | N |
| `EMAIL_VERIFICATION_TTL_HOURS` | Vigencia del enlace de verificación | `24` (por defecto) | N |
| `PASSWORD_RESET_TTL_MINUTES` | Vigencia del enlace de recuperación | `30` (por defecto) | N |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | La ventana no puede superar 1.440 minutos, que es la retención de 24 horas de `intento_ingreso`: la configuración rechaza el arranque con un valor mayor. Intentos que, al superarse dentro de la ventana, bloquean el par cuenta y origen, y ventana en minutos (RN-09, DD-25) | `5` / `15` (por defecto) | N |
| `LOGIN_MAX_ATTEMPTS_PER_ORIGIN` | Intentos de ingreso de un mismo origen, de todas las cuentas, que al superarse dentro de la misma ventana (`LOGIN_LOCKOUT_MINUTES`) hacen responder el 401 genérico sin verificar la contraseña (RN-09, DD-25) | `20` (por defecto) | N |
| `CORS_ORIGINS` | Opcional. Orígenes adicionales permitidos; vacío por defecto porque el frontend y la API comparten origen (DD-26) | vacío | N |
| `FRONTEND_BASE_URL` | Base de los enlaces enviados por correo | `https://reservas.ejemplo.com` | N |
| `SMTP_HOST` | Servidor SMTP | `smtp.gmail.com` | N |
| `SMTP_PORT` | Puerto SMTP (587 con STARTTLS) | `587` | N |
| `SMTP_USER` | Cuenta de correo emisora | `consultorio@ejemplo.com` | N |
| `SMTP_PASSWORD` | Contraseña de aplicación | valor secreto | Y |
| `SMTP_STARTTLS` | Usar STARTTLS | `true` | N |
| `SMTP_FROM` | Remitente visible | `Consultorio <consultorio@ejemplo.com>` | N |
| `EMAIL_DAILY_LIMIT` | Tope diario de correos de la cuenta (Gmail personal). Se verifica antes de reclamar; cuenta las filas `enviada` del día y las `enviando` cuya reclamación no venció (ver [04](04_modelo_de_datos.md)) | `500` | N |
| `EMAIL_DAILY_LIMIT_ACCOUNT` | Parte del tope diario que pueden usar los correos de cuenta (verificación, recuperación y rechazo de vinculación); el resto queda reservado para los correos de turnos (DD-29). Debe ser menor que `EMAIL_DAILY_LIMIT` | `150` (por defecto) | N |
| `EMAIL_DAILY_ALERT_RATIO` | Fracción del tope que dispara la alerta | `0.8` | N |
| `SWEEP_SHARED_SECRET` | Secreto compartido con el disparador externo del barrido | valor secreto | Y |
| `SWEEP_IN_PROCESS_ENABLED` | Activa el bucle propio del barrido (local o VM); en producción lo dispara el exterior | `false` en producción | N |
| `SWEEPER_INTERVAL_SECONDS` | Intervalo del bucle propio; el disparador externo se configura a 5 minutos | a definir | N |
| `NOTIFICATION_MAX_ATTEMPTS` | Reintentos de envío acotados (RN-31) | a definir | N |
| `TRUSTED_PROXY_HOPS` | Cantidad de proxies de confianza delante de la API, para tomar el origen del encabezado de reenvío (RN-62, DD-21, DD-25). Opcional; con `0` se ignora el encabezado, y detrás del proxy de un host todos los clientes comparten un origen (el bloqueo de ingreso pasa a ser por cuenta). La agrega C-03 y C-05 la reutiliza | `0` (por defecto); `1` detrás del proxy del host | N |
| `ORIGIN_HASH_SECRET` | Obligatoria, sin valor por defecto. Clave del HMAC con que se guardan el origen y el identificador de los intentos de ingreso (DD-25) y el origen de los intentos de registro (DD-21); la agrega C-03 a `Settings` y C-05 la reutiliza | valor secreto | Y |
| `REGISTRATION_LIMIT_PER_ORIGIN` | Registros permitidos por origen dentro de la ventana; al superarlo, 429 | `10` (por defecto) | N |
| `REGISTRATION_LIMIT_GLOBAL` | Registros permitidos dentro de la ventana cuando no se puede determinar el origen; al superarlo, 429 | `50` (por defecto) | N |
| `REGISTRATION_LIMIT_WINDOW_MINUTES` | Ventana de los dos límites anteriores, en minutos; no puede superar 1.440 (la retención de 24 horas de `intento_registro`) | `60` (por defecto) | N |
| `NOTIFICATION_CLAIM_TTL_SECONDS` | Antigüedad desde la cual una notificación `enviando` se considera abandonada y se reclama de nuevo (RN-61); debe superar el tiempo máximo de un envío SMTP | a definir | N |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | Alta del primer administrador (solo la primera vez). Las carga `SeedSettings` del servicio `seed` (C-02), no `Settings`; la contraseña llega como el secreto `bootstrap_admin_password` | valores propios | Y (contraseña) |
| `OPENAPI_DOCS_ENABLED` | Publicar `/docs` | `true` en desarrollo, `false` en producción | N |
| `VITE_API_BASE_URL` | Base de la API para el frontend (variable de compilación, pública); relativa, porque el frontend y la API comparten origen (DD-26) | `/api/v1` | N |
| `VITE_DEV_PROXY_TARGET` | Solo desarrollo: destino al que el proxy de Vite reenvía `/api` (lo configura C-11). No entra en el build ni se define en producción, donde la API sirve el frontend (DD-26) | `http://api:8000` dentro de Compose; `http://localhost:8000` fuera de Compose | N |

## Estrategia de pruebas

Se aplica TDD estricto en la implementación. Las herramientas concretas son un supuesto (SU-32).

| Nivel | Qué prueba | Herramienta propuesta |
|-------|------------|-----------------------|
| Unitaria | Dominio: transiciones de estado, cálculo de disponibilidad, hitos con reloj simulado, cada política ABAC con casos permitido y denegado | pytest |
| Integración | Repositorios y restricciones contra PostgreSQL real: exclusión de solapamientos (test que inserta dos turnos solapados y espera el rechazo), unicidad de DNI, reclamación por fila del barrido (dos barridos simultáneos nunca procesan la misma fila y el resultado de un envío tardío no pisa al de la reclamación vigente) | pytest con PostgreSQL en contenedor |
| Migraciones (CI) | Un único head de Alembic (`alembic heads`) y `alembic upgrade head` sobre una base vacía | Comando en CI |
| API | Endpoints, autenticación, 403 y 404 según política | pytest con cliente de FastAPI |
| Frontend | Componentes presentacionales y contenedores | Vitest y Testing Library |

## Escalabilidad

- **Dentro de la v1:** un solo consultorio. El diseño evita decisiones que impidan crecer: `consultorio_id` en todo, políticas con el atributo de consultorio y configuración por consultorio en la tabla `consultorio`.
- **Fuera de la v1:** alta de consultorios, administración por consultorio y aislamiento adicional (por ejemplo, seguridad por filas en PostgreSQL) se evaluarán cuando exista el requisito.
- **API sin estado:** la API se puede replicar; el estado vive en PostgreSQL (y en Redis, si se usa). La reclamación por fila del barrido en PostgreSQL evita que varias réplicas procesen la misma fila.
