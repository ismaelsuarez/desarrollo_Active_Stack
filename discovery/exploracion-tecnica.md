# Exploración técnica verificada

Fecha de consulta: 2026-10-05. Método: documentación vía Context7 y fuentes primarias en la web. [V] indica que se leyó en documentación o página oficial. [NV] indica que no se verificó en fuente primaria. Algunas páginas se leyeron mediante extractores automáticos, por lo que las cifras conviene contrastarlas antes de comprometer un plan.

## 1. SQLAlchemy 2.x y restricción anti-solapamiento

- [V] Patrón asíncrono: `create_async_engine("postgresql+asyncpg://...")` y `async_sessionmaker(engine, expire_on_commit=False)`. Hay que llamar a `engine.dispose()` al cerrar. Fuente: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- [V] Tipado 2.0 con `DeclarativeBase`, `Mapped[...]` y `mapped_column(...)`.
- [V] `ExcludeConstraint` está en `sqlalchemy.dialects.postgresql`, con `where`, `using` y `name`. La igualdad escalar en GiST requiere la extensión `btree_gist`. Fuente: https://docs.sqlalchemy.org/en/20/dialects/postgresql.html
- [NV] La documentación no trae un ejemplo literal con `tstzrange`. La expresión `func.tstzrange(inicio, fin, '[)')` con el operador `&&` debe cubrirse con un test de integración que inserte dos turnos solapados.
- Recomendación: declarar la restricción en el modelo y crearla con SQL manual en la migración. Traducir el error de exclusión (SQLSTATE `23P01`, [NV]) a "horario ocupado" en el adaptador del repositorio, no en el dominio.

## 2. Alembic

- [V] El `env.py` asíncrono se genera con `alembic init -t async`. Fuente: https://alembic.sqlalchemy.org/en/latest/cookbook.html
- [V] El autogenerate no detecta restricciones EXCLUDE ni restricciones sin nombre. Fuente: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- [V] Existe `op.create_exclude_constraint(...)`. Fuente: https://alembic.sqlalchemy.org/en/latest/ops.html
- [V] Dos revisiones con el mismo padre producen varios heads. Se resuelven con `alembic merge`, y `alembic upgrade head` falla con varios heads. Fuente: https://alembic.sqlalchemy.org/en/latest/branches.html
- [NV] `CREATE EXTENSION btree_gist` va a mano con `op.execute(...)`, antes del constraint.
- Recomendación: historia lineal con una migración por change, verificación de un único head en CI, `compare_type=True` y un test del constraint.

## 3. JWT, contraseñas y autorización

- [V] El tutorial oficial de FastAPI usa PyJWT para los tokens y pwdlib con Argon2 para las contraseñas, e incluye un hash ficticio para igualar tiempos cuando el usuario no existe. Fuente: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
- Recomendación: PyJWT con HS256 y Argon2 vía pwdlib. RBAC como fábrica de dependencias y ABAC como funciones puras de política invocadas desde el caso de uso. Los repositorios reciben `consultorio_id` desde el `Principal`, nunca desde el cliente.

## 4. Worker sobre Redis

| | ARQ | RQ | Celery |
|---|---|---|---|
| Versión [V] | 0.28.0 | 2.12.0 | 5.6.3 |
| Mantenimiento | Solo mantenimiento desde 2025-10-18 | Activo | Activo |
| asyncio | Nativo | Sin soporte documentado | Pools con soporte parcial [NV] |
| Programación | Cron y diferidos [NV] | Integrada desde 2.5, requiere `--with-scheduler` | `celery beat`, proceso aparte [NV] |

Fuentes: https://pypi.org/project/arq/ , https://github.com/python-arq/arq/issues/510 , https://pypi.org/project/rq/ , https://pypi.org/project/celery/

Con la tabla `notificacion` como fuente de verdad, el worker solo necesita un disparador periódico y un barrido idempotente con `SELECT ... FOR UPDATE SKIP LOCKED`. Recomendación: un bucle `asyncio` propio detrás de un puerto `Planificador`, con `pg_try_advisory_lock` o `SKIP LOCKED` como candado. Si se exige una librería, ARQ es el mejor ajuste técnico, asumiendo su estado de mantenimiento mínimo.

## 5. SMTP y Gmail

- [V] `aiosmtplib` 5.1.3, sin dependencias. Puerto 587 con `start_tls=True` y 465 con `use_tls=True`. Fuente: https://aiosmtplib.readthedocs.io/en/stable/client.html
- [V] La contraseña de aplicación exige verificación en dos pasos y no está disponible con Protección Avanzada ni con cuentas de trabajo o institución. Fuente: https://support.google.com/accounts/answer/185833
- [V] Gmail personal: 500 correos por día, con bloqueo de entre 1 y 24 horas al excederlo. Workspace: 2.000 por día. Fuentes: https://support.google.com/mail/answer/22839 y https://knowledge.workspace.google.com/admin/gmail/gmail-sending-limits-in-google-workspace
- Recomendación: `EmailMessage` de la biblioteca estándar más `aiosmtplib` detrás de un puerto `EnviadorCorreo`. Evitar `fastapi-mail`. Fijar el tope de 500 correos por día en la documentación y alertar al 80 %.

## 6. Docker Compose

- [V] La clave `version` es obsoleta y se omite. `depends_on` admite `service_healthy` y `service_completed_successfully`. Los perfiles permiten separar servicios de desarrollo. Los secretos se montan en `/run/secrets/<nombre>`. Fuente: https://docs.docker.com/reference/compose-file/
- Recomendación: añadir `healthcheck` a la API, `restart: unless-stopped` al worker y mantener `mailpit` bajo `profiles: ["dev"]`.

## 7. Hosting gratuito (páginas de cada proveedor, 2026-10-05)

| Proveedor | Datos relevantes [V] |
|---|---|
| Render | Servicio web gratuito que se duerme a los 15 minutos. Bloquea la salida por los puertos 25, 465 y 587. Postgres de 1 GB que expira a los 30 días. Sin worker ni cron gratuitos. |
| Fly.io | Sin plan gratuito: prueba de 2 horas o 7 días. |
| Railway | Crédito de 1 USD por mes. |
| Koyeb | Un servicio web gratuito. La información sobre el escalado a cero es contradictoria [NV]. |
| Neon | Plan gratuito permanente de 1 GB, 100 CU-h por mes y suspensión a los 5 minutos. `btree_gist` figura como soportado. |
| Supabase | 500 MB y pausa tras una semana de inactividad. `btree_gist` [NV]. |
| Upstash Redis | 500.000 comandos por mes. |
| Vercel Hobby | Solo uso no comercial. Cron una vez al día. |
| Cloudflare | Pages para estáticos y Workers con 5 cron triggers en el plan gratuito. |
| Oracle Always Free | VM ARM de 2 OCPU y 12 GB, con reclamo de instancias inactivas. Si exige tarjeta es contradictorio [NV]. |
| GitHub Actions | `schedule` con intervalo mínimo de 5 minutos. |

Conclusión: no existe, entre lo verificado, un stack gratuito con API, PostgreSQL, Redis y un worker aparte siempre activo en un único PaaS sin tarjeta. La arquitectura menos mala es:
1. Frontend estático en Cloudflare Pages.
2. API con barrido en proceso en un servicio web gratuito.
3. Base de datos en Neon.
4. Redis opcional (Upstash) o sustituido por el candado de Postgres.
5. Un disparador HTTP externo cada 5 minutos que llame a `POST /internal/barrido`, autenticado con un secreto.
6. Correo por un host que permita SMTP saliente o por una API HTTPS de correo [NV].

Si el docente exige el stack completo, Compose en una VM propia es la alternativa.

## 8. Conflictos con la knowledge base

| Archivo | Supuesto | Qué cambia |
|---|---|---|
| 12 y 10 (Q-02), 09 SU-01 | El hosting admite procesos persistentes, Redis y no se duerme | Inalcanzable en gratuito. La opción de barrido en proceso pasa de contingencia a base, con disparador externo. |
| 12 y 09 DD-10 | Límites de hosting sin cifras verificadas | Ya hay cifras verificadas. |
| 09 DD-06 y 12 (SMTP) | Gmail por 587 o 465 desde el hosting | Render gratuito bloquea esos puertos. Tope de 500 por día. La contraseña de aplicación no existe con Workspace ni con Protección Avanzada. |
| 09 SU-28 | `btree_gist` disponible en el proveedor | Confirmado en Neon. Pendiente en otros. |
| 09 SU-29 y 12 | Alembic versiona el esquema | El EXCLUDE y `CREATE EXTENSION` van a mano. Vigilar múltiples heads. |
| 08 Seguridad | Argon2 o bcrypt a elegir | Fijar PyJWT y pwdlib con Argon2. |
| 08 Trabajos y 09 SU-26 | Candado del barrido en Redis | Usar `pg_advisory_lock` o `SKIP LOCKED`. Respetar las cuotas de Neon y Upstash. |
| 09 SU-27 | Cookie `HttpOnly` de renovación | Con el frontend en otro dominio requiere `SameSite=None; Secure` o un dominio común [NV]. |
| 12 (Compose) | Esquema ilustrativo | Faltan `healthcheck` en la API, `restart` en el worker y secretos de archivo. |

## 9. Brechas del ecosistema de skills

No hay skills maduras para `ExcludeConstraint` con `tstzrange`, SMTP desde un backend Python, ARQ o RQ, ni ABAC con funciones de política. Para esos casos se usa Context7, que ya está conectado como MCP en esta sesión, junto con la documentación del proyecto.
