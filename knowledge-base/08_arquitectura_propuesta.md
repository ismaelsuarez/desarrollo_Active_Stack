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
│       │   └── jobs/                # barrido idempotente, candado en PostgreSQL y adaptadores de Planificador
│       └── api/
│           ├── deps.py              # autenticación, fábricas de dependencias RBAC, casos de uso
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
| Despacho de notificaciones | Barrido periódico | Envía correos `programada` vencidos y reintenta los fallidos de forma acotada. | `UNIQUE (turno_id, tipo, canal, ciclo)` y estado de la notificación. |
| Solicitud de confirmación (T-48 h) | Barrido de hitos | Para turnos `pendiente` en su ciclo actual, crea correo y mensaje de WhatsApp preparado. | `confirmacion_solicitada_en` y la restricción de la notificación. |
| Recordatorio (T-24 h) | Barrido de hitos | Para turnos `pendiente` y `confirmado`. | `recordatorio_enviado_en`. |
| Liberación (T-12 h) | Barrido de hitos | Modo automático: pasa a `liberado` si sigue `pendiente`. Modo manual: marca `marcado_sin_confirmar_en`. | Transición condicional por estado. |
| Limpieza de tokens vencidos | Periódico | Borra tokens expirados de `token_usuario` y `refresh_token`. | Operación repetible. |

Diseño del barrido:

1. El barrido se dispara cada 5 minutos desde el exterior (`POST /internal/barrido` con el secreto `SWEEP_SHARED_SECRET`) o, en local o VM, con un bucle propio (`SWEEPER_INTERVAL_SECONDS`). El intervalo debe ser lo bastante corto para respetar la precisión de los hitos de 48, 24 y 12 horas.
2. Toma un candado en PostgreSQL (`pg_try_advisory_lock`, o `SELECT ... FOR UPDATE SKIP LOCKED` sobre las filas a procesar) para que dos disparos o dos instancias no procesen lo mismo. Si no obtiene el candado, termina sin hacer nada.
3. Consulta la base de datos por notificaciones y turnos cuyos hitos vencieron y procesa en lotes. La tabla `notificacion` es la fuente de verdad.
4. Cada operación es una transacción corta y condicional (por ejemplo `UPDATE ... WHERE estado = 'pendiente'`), por lo que repetir el barrido no duplica efectos.
5. Si el disparador falla, el servicio estaba dormido o Redis (si se usa) no está disponible, los recordatorios no se pierden: están en PostgreSQL y se procesan en el siguiente barrido. Los hitos se retrasan, no se pierden.
6. Cuotas a respetar: Neon (suspensión del cómputo a los 5 minutos, 100 CU-h por mes) y Upstash (500.000 comandos por mes) si se usa; ver Q-27 en [10](10_preguntas_abiertas.md).

El barrido usa el reloj del sistema a través de un puerto `Reloj` para poder probar los hitos con tiempo simulado.

## Persistencia y migraciones

- **Acceso asíncrono:** SQLAlchemy 2.x con `create_async_engine("postgresql+asyncpg://...")` y `async_sessionmaker(engine, expire_on_commit=False)`; el motor se libera con `engine.dispose()` al cerrar. Los modelos usan `DeclarativeBase`, `Mapped[...]` y `mapped_column(...)`.
- **No solapamiento (DD-08):** la restricción de exclusión (`ExcludeConstraint` de `sqlalchemy.dialects.postgresql`, con `where`, `using` y `name`) requiere la extensión `btree_gist`. Se declara en el modelo y se **crea a mano en la migración** después de `CREATE EXTENSION IF NOT EXISTS btree_gist`, porque el autogenerate de Alembic no detecta restricciones EXCLUDE.
- **Prueba obligatoria:** un test de integración inserta dos turnos solapados del mismo profesional y espera el rechazo. La documentación de SQLAlchemy no trae un ejemplo literal con `tstzrange`, por lo que la expresión `tstzrange(inicio, fin, '[)')` con el operador `&&` debe quedar cubierta por ese test.
- **Traducción del error:** el adaptador del repositorio traduce el error de exclusión (SQLSTATE `23P01`) a "horario ocupado". **Suposición:** el código `23P01` no se verificó en fuente primaria; confirmarlo en la primera prueba de integración. El dominio no conoce el código SQL.
- **Migraciones:** Alembic con `env.py` asíncrono (`alembic init -t async`), `compare_type=True`, historia lineal con una migración por change y un único head. CI ejecuta `alembic heads` y exige un solo head; se aplica `alembic upgrade head`, nunca `heads`.

## Seguridad

- **Autenticación:** JWT firmado por el servidor con PyJWT (HS256) y los claims de RN-06 (usuario, `consultorio_id`, rol), siguiendo el tutorial oficial de FastAPI. Token de acceso de vida corta y sesión renovable con rotación (`refresh_token`). El almacenamiento en el navegador es un supuesto (SU-27): token de acceso en memoria y token de renovación en cookie `HttpOnly`, `Secure` y `SameSite`; si se usan cookies, se agrega protección contra CSRF en los endpoints de renovación. **Suposición:** con el frontend en Cloudflare Pages y la API en otro dominio, la cookie requiere `SameSite=None; Secure` o un dominio común (no verificado; Q-28 en [10](10_preguntas_abiertas.md)).
- **Contraseñas:** hash Argon2 con pwdlib (decisión DD-12), con sal; el proceso de ingreso compara contra un hash ficticio cuando el usuario no existe para igualar tiempos (práctica del tutorial oficial). Nunca en logs ni respuestas (RN-04). Política mínima de contraseña a definir ([10](10_preguntas_abiertas.md)).
- **Tokens de un solo uso** (verificación, recuperación, confirmación por enlace): aleatorios con entropía suficiente, guardados hasheados, con vencimiento y marca de uso (RN-03).
- **Autorización:** RBAC como fábricas de dependencias de FastAPI en el endpoint y ABAC como funciones de política puras invocadas desde el caso de uso (ver [11](11_politicas_de_acceso_abac.md)). Denegar por defecto.
- **Aislamiento por consultorio:** `consultorio_id` obligatorio en las tablas y en todo filtro. Los repositorios reciben `consultorio_id` desde el `Principal` (el usuario autenticado), nunca desde el cliente; no se aceptan identificadores de consultorio enviados por el cliente.
- **Endpoint interno del barrido:** `POST /internal/barrido` exige el secreto compartido `SWEEP_SHARED_SECRET`, compara en tiempo constante y no se publica en la documentación de la API pública.
- **Validación de entrada:** esquemas Pydantic estrictos en la API; consultas parametrizadas a través del ORM; límite de tamaño de cuerpo.
- **Límite de intentos y de abuso:** limitación de ingresos fallidos (RN-09) y de solicitudes a los endpoints públicos de registro, recuperación y reenvío, apoyada en Redis si se despliega o en PostgreSQL si no. Los umbrales se definen al implementar.
- **No enumeración de cuentas:** respuestas idénticas en recuperación de contraseña (RN-05); mensajes de ingreso genéricos.
- **Transporte:** HTTPS en cualquier entorno público; CORS restringido al origen del frontend (`CORS_ORIGINS`).
- **Secretos:** solo en variables de entorno, archivos de secreto (`/run/secrets/<nombre>` en Compose) o el almacén de secretos del host, nunca en el repositorio; `.env.example` no contiene valores reales. La contraseña de aplicación de SMTP, `JWT_SECRET_KEY` y `SWEEP_SHARED_SECRET` son secretos.
- **Datos personales:** acceso por rol y atributos, sin borrado físico, mensajes sin datos de salud (RN-54). La auditoría y el consentimiento de la Ley 25.326 están diferidos (RN-58).
- **Registro (logging):** estructurado, con identificador de solicitud; sin contraseñas, tokens ni datos personales innecesarios.
- **Documentación de API:** `/docs` y `/openapi.json` habilitados en desarrollo y restringidos en producción (SU-06).

## Variables de entorno

Los valores de ejemplo no son secretos reales. Los valores numéricos de duraciones e intervalos no están definidos en las fuentes y figuran como "a definir" (ver [10](10_preguntas_abiertas.md)).

| Variable | Descripción | Ejemplo | Sensible |
|----------|-------------|---------|----------|
| `APP_ENV` | Entorno de ejecución | `development` / `production` | N |
| `APP_TIMEZONE` | Zona horaria de operación | `America/Argentina/Buenos_Aires` | N |
| `DATABASE_URL` | Conexión a PostgreSQL (controlador asíncrono asyncpg; en producción, Neon) | `postgresql+asyncpg://usuario:clave@db:5432/turnos` | Y |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciales del contenedor de PostgreSQL (solo Compose) | `turnos` / `cambiar` / `turnos` | Y (contraseña) |
| `REDIS_URL` | Conexión a Redis (opcional; solo si se despliega) | `redis://redis:6379/0` | N |
| `JWT_SECRET_KEY` | Clave de firma del JWT | cadena aleatoria larga | Y |
| `JWT_ALGORITHM` | Algoritmo de firma (PyJWT) | `HS256` | N |
| `JWT_ACCESS_TTL_MINUTES` | Vida del token de acceso | a definir | N |
| `JWT_REFRESH_TTL_DAYS` | Vida del token de renovación | a definir | N |
| `EMAIL_VERIFICATION_TTL_HOURS` | Vigencia del enlace de verificación | a definir | N |
| `PASSWORD_RESET_TTL_MINUTES` | Vigencia del enlace de recuperación | a definir | N |
| `LOGIN_MAX_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | Límite de intentos fallidos y bloqueo (RN-09) | a definir | N |
| `CORS_ORIGINS` | Orígenes permitidos del frontend | `https://reservas.ejemplo.com` | N |
| `FRONTEND_BASE_URL` | Base de los enlaces enviados por correo | `https://reservas.ejemplo.com` | N |
| `SMTP_HOST` | Servidor SMTP | `smtp.gmail.com` | N |
| `SMTP_PORT` | Puerto SMTP (587 con STARTTLS) | `587` | N |
| `SMTP_USER` | Cuenta de correo emisora | `consultorio@ejemplo.com` | N |
| `SMTP_PASSWORD` | Contraseña de aplicación | valor secreto | Y |
| `SMTP_STARTTLS` | Usar STARTTLS | `true` | N |
| `SMTP_FROM` | Remitente visible | `Consultorio <consultorio@ejemplo.com>` | N |
| `EMAIL_DAILY_LIMIT` | Tope diario de correos de la cuenta (Gmail personal) | `500` | N |
| `EMAIL_DAILY_ALERT_RATIO` | Fracción del tope que dispara la alerta | `0.8` | N |
| `SWEEP_SHARED_SECRET` | Secreto compartido con el disparador externo del barrido | valor secreto | Y |
| `SWEEP_IN_PROCESS_ENABLED` | Activa el bucle propio del barrido (local o VM); en producción lo dispara el exterior | `false` en producción | N |
| `SWEEPER_INTERVAL_SECONDS` | Intervalo del bucle propio; el disparador externo se configura a 5 minutos | a definir | N |
| `NOTIFICATION_MAX_ATTEMPTS` | Reintentos de envío acotados (RN-31) | a definir | N |
| `BOOTSTRAP_ADMIN_EMAIL` / `BOOTSTRAP_ADMIN_PASSWORD` | Alta del primer administrador (solo la primera vez) | valores propios | Y (contraseña) |
| `OPENAPI_DOCS_ENABLED` | Publicar `/docs` | `true` en desarrollo, `false` en producción | N |
| `VITE_API_BASE_URL` | URL de la API para el frontend (variable de compilación, pública) | `https://api.ejemplo.com/api/v1` | N |

## Estrategia de pruebas

Se aplica TDD estricto en la implementación. Las herramientas concretas son un supuesto (SU-32).

| Nivel | Qué prueba | Herramienta propuesta |
|-------|------------|-----------------------|
| Unitaria | Dominio: transiciones de estado, cálculo de disponibilidad, hitos con reloj simulado, cada política ABAC con casos permitido y denegado | pytest |
| Integración | Repositorios y restricciones contra PostgreSQL real: exclusión de solapamientos (test que inserta dos turnos solapados y espera el rechazo), unicidad de DNI, candado del barrido | pytest con PostgreSQL en contenedor |
| Migraciones (CI) | Un único head de Alembic (`alembic heads`) y `alembic upgrade head` sobre una base vacía | Comando en CI |
| API | Endpoints, autenticación, 403 y 404 según política | pytest con cliente de FastAPI |
| Frontend | Componentes presentacionales y contenedores | Vitest y Testing Library |

## Escalabilidad

- **Dentro de la v1:** un solo consultorio. El diseño evita decisiones que impidan crecer: `consultorio_id` en todo, políticas con el atributo de consultorio y configuración por consultorio en la tabla `consultorio`.
- **Fuera de la v1:** alta de consultorios, administración por consultorio y aislamiento adicional (por ejemplo, seguridad por filas en PostgreSQL) se evaluarán cuando exista el requisito.
- **API sin estado:** la API se puede replicar; el estado vive en PostgreSQL (y en Redis, si se usa). El candado del barrido en PostgreSQL evita que varias réplicas procesen lo mismo.
