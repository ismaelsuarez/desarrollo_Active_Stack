# DevOps y Despliegue

Restricciones de partida: **presupuesto cero** (solo servicios gratuitos o con plan gratuito), Docker y Docker Compose obligatorios, y el enlace público de reserva alojado en un plan gratuito de hosting en la nube. La primera entrega, el 2026-10-19, es el repositorio y no exige el sistema publicado; la publicación (C-20) corresponde a la segunda parte (DD-22 en [09](09_decisiones_y_supuestos.md)).

Este documento fija la **arquitectura de despliegue base** a partir de la exploración técnica del 2026-10-05 (`discovery/exploracion-tecnica.md`). Las cifras de planes gratuitos se leyeron en las páginas de cada proveedor en esa fecha y **cambian con el tiempo**; algunas se leyeron con extractores automáticos, por lo que conviene contrastarlas antes de comprometer el plan. Lo no verificado se marca `[NV]` y figura como suposición o pregunta abierta ([09](09_decisiones_y_supuestos.md), [10](10_preguntas_abiertas.md)). La elección concreta del proveedor del servicio web sigue abierta (Q-02 resuelta en cuanto a la arquitectura, Q-24 en cuanto al proveedor).

## Entornos

| Entorno | Propósito | Cómo se levanta |
|---------|-----------|-----------------|
| Desarrollo local | Programar y probar | `docker compose --profile dev up` (recarga en caliente, servidor de correo de prueba). |
| Demostración / producción v1 | Enlace público de reserva y uso del consultorio | Arquitectura base de varios servicios gratuitos (ver "Arquitectura de despliegue base"). |
| Alternativa: stack completo en una VM | Si se exige el stack completo con Redis y proceso persistente | El mismo `docker-compose.yml` en una máquina virtual propia, con el mismo servicio único de la API que sirve el frontend compilado (DD-26). |

No se prevé un entorno intermedio (staging) en la v1 por presupuesto y plazo; se registra como decisión implícita en [09](09_decisiones_y_supuestos.md).

## Arquitectura de despliegue base

Entre lo verificado no existe un stack gratuito con API, PostgreSQL, Redis y un proceso aparte siempre activo en un único PaaS sin tarjeta. La arquitectura base, la menos mala entre las opciones verificadas, es:

| Componente | Servicio | Notas |
|------------|----------|-------|
| Frontend | Lo sirve la propia API desde el build compilado (DD-26) | Un solo origen y un solo servicio; si el host duerme la API, la pantalla tarda en responder mientras despierta. |
| API | Servicio web gratuito (proveedor por decidir, Q-24) | Contiene el barrido de hitos en proceso. Se duerme por inactividad en los planes gratuitos conocidos. |
| Base de datos | PostgreSQL en Neon | `btree_gist` figura como soportado [V]. Plan gratuito permanente de 1 GB. |
| Redis | Opcional (Upstash) o sustituido por la reclamación por fila en PostgreSQL | La base de datos es la fuente de verdad de lo programado; ver abajo. |
| Disparador del barrido | Llamada HTTP externa cada 5 minutos | `POST /internal/barrido`, autenticada con un secreto compartido. |
| Correo | SMTP o API HTTPS de correo, según el puerto permitido por el host | Ver "Configuración de correo". |

Reglas de diseño del barrido ([08](08_arquitectura_propuesta.md)):

- La tabla `notificacion` sigue siendo la fuente de verdad y el barrido es **idempotente**; repetirlo o dispararlo dos veces no duplica los cambios de estado ni los envíos concurrentes. La entrega de correo es al menos una vez: una caída entre el envío y el registro del resultado puede repetir un correo (RN-61).
- El puerto `Planificador` oculta el disparador: en producción es la llamada HTTP externa; en local o en una VM puede ser un bucle `asyncio` propio. El caso de uso del barrido es el mismo.
- Contra ejecuciones simultáneas no hay un candado global: cada fila se reclama por separado con `SELECT ... FOR UPDATE SKIP LOCKED` en PostgreSQL (estado intermedio `enviando` y hora de reclamación), el envío SMTP ocurre fuera de la transacción y el resultado se registra en otra transacción corta, condicionada a que la fila siga `enviando` con la misma `reclamada_en` que fijó ese envío (DD-17, RN-61). No se usan candados de sesión (`pg_try_advisory_lock`): no son fiables detrás del pooler de Neon. La entrega es al menos una vez: una caída entre el envío y el registro puede repetir un correo. Redis, si se despliega, es auxiliar (por ejemplo para límites de intentos).
- El endpoint `/internal/barrido` exige el secreto compartido (variable `SWEEP_SHARED_SECRET`, sensible) y no es parte de la API pública.

### Datos verificados de proveedores (consulta del 2026-10-05)

| Proveedor | Datos relevantes |
|-----------|------------------|
| Render | [V] El servicio web gratuito se duerme a los 15 minutos de inactividad. [V] Bloquea la salida por los puertos 25, 465 y 587. [V] El Postgres gratuito de 1 GB expira a los 30 días. [V] No hay worker ni cron gratuitos. |
| Neon | [V] Plan gratuito permanente de 1 GB, 100 CU-h por mes y suspensión del cómputo a los 5 minutos. [V] `btree_gist` figura como soportado. |
| Upstash Redis | [V] 500.000 comandos por mes. |
| Cloudflare | [V] Pages para sitios estáticos (no se usa: DD-26 sirve el frontend desde la API) y Workers con 5 cron triggers en el plan gratuito (candidato a disparador, Q-25). |
| GitHub Actions | [V] `schedule` con intervalo mínimo de 5 minutos. |
| Fly.io | [V] Sin plan gratuito: prueba de 2 horas o 7 días. |
| Railway | [V] Crédito de 1 USD por mes. |
| Vercel Hobby | [V] Solo uso no comercial; cron una vez al día (no sirve para el barrido). |
| Supabase | [V] 500 MB y pausa tras una semana de inactividad. `btree_gist` [NV]. |
| Koyeb | [V] Un servicio web gratuito. La información sobre el escalado a cero es contradictoria [NV]. |
| Oracle Always Free | [V] VM ARM de 2 OCPU y 12 GB, con reclamo de instancias inactivas. Si exige tarjeta es contradictorio [NV]. |

### Consecuencias y riesgos de la arquitectura base

| Aspecto | Consecuencia |
|---------|--------------|
| API dormida | Con la API dormida el barrido no corre. Mitigación: el disparador cada 5 minutos la despierta; que además la mantenga activa es una **suposición** `[NV]` que debe medirse. Los hitos de 48, 24 y 12 horas toleran un retraso de pocos minutos solo si el disparador es confiable. |
| Cuota de Neon | La suspensión a los 5 minutos y el barrido cada 5 minutos pueden mantener el cómputo casi siempre activo; si eso agota las 100 CU-h por mes depende del tamaño de cómputo, que no se verificó. Pregunta abierta Q-27. |
| Cuota de Upstash | 500.000 comandos por mes: si se usa Redis, limitar su uso a lo auxiliar. |
| Postgres de Render | Expira a los 30 días: no se usa como base de producción. |
| Correo desde el host | Render gratuito bloquea los puertos SMTP; ver "Configuración de correo". |
| Cookie de renovación | Resuelto por DD-26: frontend y API en un solo origen, cookie propia con `SameSite=Strict`; ver "Cookie de renovación y origen". |
| Disparador externo | Es una dependencia operativa más (Q-25). Si falla, los recordatorios no se envían ni los turnos se liberan hasta que vuelva; al volver, el barrido procesa lo vencido sin duplicar. |

Si el docente exige el stack completo (API, PostgreSQL, Redis y proceso persistente), la alternativa es Docker Compose en una VM propia (por ejemplo la VM de Oracle Always Free, sujeta a sus condiciones `[NV]`).

## Servicios de Docker Compose

Compose es el entorno de desarrollo local y la alternativa para una VM. No es la topología de la arquitectura base de producción.

| Servicio | Imagen / origen | Función | Depende de | Puerto |
|----------|-----------------|---------|-----------|--------|
| `db` | Imagen oficial de PostgreSQL | Base de datos. Volumen persistente. | — | 5432 (solo red interna) |
| `redis` (opcional) | Imagen oficial de Redis | Límites de intentos y otros usos auxiliares. Perfil `redis`. | — | 6379 (solo red interna) |
| `migrate` | Imagen del backend | Ejecuta las migraciones (`alembic upgrade head`) y termina. | `db` saludable | — |
| `api` | Imagen del backend | API FastAPI con el barrido en proceso (bucle `asyncio` o llamada a `/internal/barrido`). | `db`, `migrate` | 8000 |
| `seed` (desde C-02) | Imagen del backend | Carga la semilla (`python -m app.seed`) con su propia `SeedSettings` y termina. | `migrate` completado | — |
| `frontend` | Imagen del frontend (etapa `dev`) | Solo desarrollo: servidor de Vite, que reenvía `/api` a la API con `VITE_DEV_PROXY_TARGET`. En producción, y en la VM, no existe este servicio: la API sirve el frontend compilado (DD-26). | `api` | 5173 (desarrollo) |
| `mailpit` (solo desarrollo) | Servidor SMTP de prueba | Captura los correos sin enviarlos (SU-33). Perfil `dev`. | — | 1025 (SMTP) / 8025 (interfaz) |

Esquema de `docker-compose.yml` (ilustrativo; los valores salen del archivo `.env` y de secretos). Es el entorno completo al terminar la v1: cada change agrega sus propios servicios y secretos, y en C-01 solo existen `postgres_password`, `database_url` y `jwt_secret_key`. No se declara la clave `version`, que es obsoleta:

```yaml
services:
  db:
    image: postgres:<version>
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - db_data:/var/lib/postgresql/data
    secrets:
      - postgres_password
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]

  redis:
    image: redis:<version>
    profiles: ["redis"]
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  migrate:
    build: ./backend
    command: alembic upgrade head
    env_file: .env
    secrets:
      - database_url
    depends_on:
      db:
        condition: service_healthy

  seed:
    build: ./backend
    command: python -m app.seed
    env_file: .env
    secrets:
      - database_url
      - bootstrap_admin_password
    depends_on:
      migrate:
        condition: service_completed_successfully

  api:
    build: ./backend
    command: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
    env_file: .env
    secrets:
      - database_url
      - jwt_secret_key
      - origin_hash_secret
      - smtp_password
      - sweep_shared_secret
    depends_on:
      seed:
        condition: service_completed_successfully
    ports:
      - "8000:8000"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"]
      interval: 30s
      timeout: 5s
      retries: 3

  frontend:
    build:
      context: ./frontend
      target: dev
    environment:
      VITE_API_BASE_URL: ${VITE_API_BASE_URL}
      VITE_DEV_PROXY_TARGET: http://api:8000
    ports:
      - "5173:5173"
    depends_on:
      api:
        condition: service_healthy
    restart: unless-stopped

  mailpit:
    image: axllent/mailpit
    profiles: ["dev"]
    ports:
      - "8025:8025"

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
  database_url:
    file: ./secrets/database_url.txt
  bootstrap_admin_password:
    file: ./secrets/bootstrap_admin_password.txt
  jwt_secret_key:
    file: ./secrets/jwt_secret_key.txt
  origin_hash_secret:
    file: ./secrets/origin_hash_secret.txt
  smtp_password:
    file: ./secrets/smtp_password.txt
  sweep_shared_secret:
    file: ./secrets/sweep_shared_secret.txt

volumes:
  db_data:
```

Notas del esquema:

- `depends_on` usa `condition: service_healthy` y `service_completed_successfully`; los perfiles separan los servicios de desarrollo.
- Los secretos se montan en `/run/secrets/<nombre>`; la configuración de la aplicación los lee de ahí cuando existen. `migrate` y `api` comparten imagen, pero `migrate` carga solo la configuración de base de datos y recibe únicamente `database_url`; `api` carga `Settings` completo y recibe los secretos que exige para arrancar; `seed` carga su propia `SeedSettings` y recibe solo `database_url` y `bootstrap_admin_password`. Ningún valor sensible va en `.env` ni en `environment`: `.env` solo tiene variables no sensibles. La contraseña local de la base figura en `postgres_password.txt` (para el contenedor de PostgreSQL) y dentro de `database_url.txt` (para la API); los genera `scripts/dev_secrets.sh` a partir de un mismo valor, así no pueden divergir. En un hosting se cargan desde su almacén de secretos. La carpeta `secrets/` no se versiona.
- `restart: unless-stopped` va en todos los servicios de ejecución prolongada.
- A partir de C-02 hay un servicio más, `seed`, de una sola ejecución: corre `python -m app.seed` con la imagen del backend, depende de `migrate` y `api` depende de él. Carga su propia `SeedSettings` (la configuración de base de datos más `CONSULTORIO_ACTIVO_ID`, `APP_TIMEZONE`, `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD`) y recibe solo los secretos `database_url` y `bootstrap_admin_password` (C-02 agrega ese archivo a `scripts/dev_secrets.sh`): así los secretos obligatorios que agreguen los changes siguientes se montan solo en `api` y no rompen la semilla. El esquema de arriba es el entorno al terminar la v1, no el de C-01.
- El endpoint de salud de la API es `GET /api/v1/health` (en las tablas de rutas, relativas al prefijo `/api/v1`, figura como `GET /health`) y existe para el `healthcheck`. No consulta la base.
- Las versiones de las imágenes se fijan al crear el proyecto.

## Enfoque de hosting con plan gratuito

El requisito explícito es que **el enlace público de reserva** esté en un plan gratuito de hosting en la nube, accesible desde internet. La arquitectura base distribuye la aplicación entre servicios gratuitos especializados porque ningún proveedor gratuito verificado cubre todo junto.

Criterios para elegir el proveedor del servicio web de la API (a verificar con la documentación vigente antes de decidir):

| Criterio | Por qué importa |
|----------|-----------------|
| Comportamiento ante inactividad | Si el servicio se duerme, el barrido no corre hasta que lo despierte una llamada (Render: 15 minutos). El disparador externo mitiga el problema. |
| Salida SMTP permitida | Render gratuito bloquea los puertos 25, 465 y 587. Si el proveedor elegido también los bloquea, se necesita una API HTTPS de correo `[NV]` (Q-23). |
| Contenedores Docker o proceso web | La API se despliega como servicio web. No se exige un proceso aparte siempre activo. |
| HTTPS con dominio o subdominio del proveedor | Obligatorio para el enlace público y los enlaces de los correos. |
| Variables de entorno y secretos | Para `JWT_SECRET_KEY`, `SMTP_PASSWORD`, `SWEEP_SHARED_SECRET`, `ORIGIN_HASH_SECRET` y la conexión a la base de datos. |
| Un solo servicio para la API y el frontend compilado | Con DD-26 la API sirve el frontend: el host debe admitir ese servicio único. El frontend y la API comparten origen y la cookie es propia (ver abajo). |

Topologías consideradas:

| Opción | Descripción | Estado |
|--------|-------------|--------|
| Base. Un solo servicio web con la API (que sirve el frontend compilado, DD-26), barrido en proceso, base en Neon y disparador externo | Es la arquitectura descrita arriba. | Vigente. |
| Todo en un proveedor | Frontend, API, base y Redis en un mismo proveedor gratuito. | Descartada entre lo verificado: ningún plan gratuito lo cubre sin tarjeta. |
| VM propia con Compose | Stack completo con Redis y proceso persistente, con el mismo servicio único de la API que sirve el frontend compilado (sin servidor web aparte). | Alternativa si se exige el stack completo. |

## Configuración de correo (SMTP)

Correo automático desde una cuenta existente, por ejemplo Gmail con contraseña de aplicación.

| Aspecto | Detalle |
|---------|---------|
| Implementación | `EmailMessage` de la biblioteca estándar más `aiosmtplib`, detrás del puerto `EnviadorCorreo`. No se usa `fastapi-mail`. |
| Servidor | `SMTP_HOST` (por ejemplo `smtp.gmail.com`) |
| Puerto y cifrado | 587 con STARTTLS (`SMTP_STARTTLS=true`, que corresponde a `start_tls=True`) |
| Autenticación | `SMTP_USER` y `SMTP_PASSWORD`. En Gmail se usa una **contraseña de aplicación**, que exige la verificación en dos pasos y no está disponible con Protección Avanzada ni con cuentas de trabajo o institución. No se usa la contraseña normal de la cuenta. |
| Remitente | `SMTP_FROM`; en cuentas personales de Gmail el remitente visible queda ligado a la cuenta autenticada |
| Secretos | La contraseña de aplicación se carga solo como secreto del entorno o archivo de secreto; nunca en el repositorio |
| Desarrollo | Se usa `mailpit` (perfil `dev`) en lugar de la cuenta real |

Límites verificados:

- **Gmail personal:** 500 correos por día, con bloqueo de entre 1 y 24 horas al excederlo. Workspace: 2.000 por día. El sistema documenta el tope de 500 por día y **alerta al 80 %** (el contador diario se lleva en el sistema). Se verifica antes de cada reclamación que enviaría un correo: con el tope alcanzado el barrido no reclama más correos, que siguen `programada` sin consumir intentos, ni reclama de nuevo una `enviando` vencida. El conteo del día suma las filas de canal `email` `enviada` con `enviada_en` dentro del día en la zona del consultorio y las que están `enviando` con la reclamación vigente (no vencida); pasar una reclamación vencida a `omitida` o a `fallida` no envía nada y no se frena por el tope (detalle en [04](04_modelo_de_datos.md)).
- **Puertos bloqueados por algunos hosts:** Render gratuito bloquea la salida por 25, 465 y 587. Entonces Gmail por SMTP no es utilizable desde ese host.
- **Posible API HTTPS de correo `[NV]`:** si el host elegido bloquea SMTP, hará falta un servicio de correo con API HTTPS. No se verificó ningún proveedor ni su plan gratuito; es la pregunta abierta Q-23. El puerto `EnviadorCorreo` permite cambiar el adaptador sin tocar los casos de uso.

Mitigaciones generales:

- **Volumen:** el sistema envía verificación, confirmación, recordatorio y avisos por turno, así que el volumen crece con los turnos. Mitigación: enviar solo los correos necesarios (RN-54), reintentos acotados (RN-31), registrar fallos en `notificacion` y avisar a Recepción.
- **Riesgo de spam:** los correos pueden caer en la carpeta de no deseados, y un paciente que no los lee puede perder el turno por liberación automática. Mitigación: recordatorio a T-24 h, WhatsApp semimanual y modo manual de liberación por consultorio (RN-28).
- **Dependencia de una cuenta personal:** si la cuenta se bloquea, se pierden los envíos. Mitigación: monitorear notificaciones `fallida` y el contador diario.
- **Entregabilidad:** el remitente es el de la cuenta autenticada; no se configuran registros de dominio propios en la v1.

## Cookie de renovación y origen

El token de renovación viaja en una cookie `HttpOnly` (SU-27). El frontend y la API comparten origen (DD-26 en [09](09_decisiones_y_supuestos.md)): en producción la API sirve el frontend compilado y en desarrollo el servidor de Vite reenvía `/api` a la API. La cookie es propia, con `Secure` y `SameSite=Strict`, y no hace falta CORS; `CORS_ORIGINS` queda vacío salvo que se habilite un origen adicional.

## Variables de entorno por entorno

El catálogo completo está en [08](08_arquitectura_propuesta.md). Resumen de las diferencias entre entornos:

| Variable | Desarrollo | Producción |
|----------|------------|------------|
| `APP_ENV` | Obligatoria, sin valor por defecto. `development` | Obligatoria. `production` |
| `DATABASE_URL` | PostgreSQL del Compose (`postgresql+asyncpg://...`), en el secreto `database_url` | Cadena de conexión de Neon (`postgresql+asyncpg://...`) |
| `MIGRATIONS_DATABASE_URL` | Sin definir (las migraciones usan `DATABASE_URL`) | Conexión directa de Neon, sin pooler, cuando `DATABASE_URL` pasa por el pooler |
| `SMTP_HOST` / `SMTP_PORT` | `mailpit` / `1025` | Servidor SMTP real, puerto 587 con STARTTLS (o la API HTTPS de correo que se elija, Q-23) |
| `SMTP_PASSWORD` | vacío | Contraseña de aplicación (secreto) |
| `JWT_SECRET_KEY` | Valor aleatorio de 32 bytes o más, generado por `scripts/dev_secrets.sh` | Valor aleatorio de 32 bytes o más, único del entorno |
| `SWEEP_SHARED_SECRET` | valor de prueba | Valor aleatorio largo, compartido con el disparador externo |
| `ORIGIN_HASH_SECRET` | Obligatoria. Valor de prueba | Obligatoria. Valor aleatorio largo, único del entorno |
| `TRUSTED_PROXY_HOPS` | `0` (el encabezado de reenvío se ignora) | La cantidad real de proxies de confianza delante de la API en el host elegido (por ejemplo `1`; a verificar con el host, Q-24) |
| `CONSULTORIO_ACTIVO_ID` | Obligatoria. Identificador del consultorio de la semilla local (por ejemplo `1`) | Obligatoria. Identificador del consultorio sembrado en Neon (RN-59) |
| `CORS_ORIGINS` | Vacío (el proxy de Vite deja todo en un origen) | Vacío (la API sirve el frontend, DD-26) |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Dominio público de reserva |
| `OPENAPI_DOCS_ENABLED` | `true` | `false` |
| `BOOTSTRAP_ADMIN_*` | valores de prueba (la contraseña llega como el secreto `bootstrap_admin_password`) | Valores propios, retirados luego del primer uso |
| `VITE_DEV_PROXY_TARGET` | Solo desarrollo: `http://api:8000` dentro de Compose, `http://localhost:8000` fuera de Compose | No aplica (no entra en el build; la API sirve el frontend, DD-26) |

Archivos:

- `.env.example`, versionado, con nombres y valores no sensibles.
- `.env`, no versionado (ignorado por Git), con los valores no secretos reales.
- `secrets/`, no versionado, con los secretos que Compose monta como archivos.

## Trabajos programados en el despliegue

- El **barrido** corre dentro del proceso de la API. En producción lo dispara una llamada HTTP externa cada 5 minutos a `POST /internal/barrido` con el secreto compartido. Candidatos para el disparador: GitHub Actions (`schedule`, intervalo mínimo de 5 minutos [V]) y Cloudflare Workers (5 cron triggers en el plan gratuito [V]; su frecuencia mínima no se verificó `[NV]`). Quién lo opera es la pregunta Q-25.
- En local o en una VM, el mismo caso de uso puede ejecutarse con un bucle `asyncio` propio detrás del puerto `Planificador`.
- Al reiniciar o tras una caída del disparador, el barrido procesa lo vencido sin duplicar los cambios de estado (idempotencia de [08](08_arquitectura_propuesta.md)).
- **Zona horaria:** los contenedores se ejecutan en UTC; la zona `America/Argentina/Buenos_Aires` se aplica en la lógica de negocio y en la presentación (SU-02, SU-36).
- **Dos barridos a la vez no procesan la misma fila:** la reclamación por fila (`SKIP LOCKED`, estado `enviando`) evita envíos concurrentes duplicados si llegan dos disparos o hay más de una instancia de la API; ambos barridos pueden correr a la vez. Una reclamación abandonada se revisa al vencer `NOTIFICATION_CLAIM_TTL_SECONDS`, con la misma validación de vigencia por tipo que la primera reclamación y respetando el máximo de intentos y el tope diario (solo reenvía si no se alcanzó); el resultado de un envío lento que perdió la reclamación se descarta.
- **Indicadores operativos mínimos:** cantidad de notificaciones `fallida`, antigüedad de la notificación `programada` más vieja (debería ser pequeña), cantidad de filas en `enviando` y antigüedad de la más vieja (una reclamación que supera `NOTIFICATION_CLAIM_TTL_SECONDS` sin retomarse indica un barrido caído), estado del último barrido y envíos del día frente al tope de 500.

## Migraciones, respaldo y recuperación

| Aspecto | Enfoque |
|---------|---------|
| Migraciones | Alembic con `env.py` asíncrono (`alembic init -t async`) y `compare_type=True`. Historia lineal con una migración por change y **un único head**. Se aplican con `alembic upgrade head` (nunca `upgrade heads`) antes de iniciar la API (SU-29). |
| Restricción de exclusión | El autogenerate de Alembic no detecta restricciones EXCLUDE. La migración ejecuta a mano `CREATE EXTENSION IF NOT EXISTS btree_gist` y luego crea la restricción (por ejemplo con `op.create_exclude_constraint`). Un test de integración inserta dos turnos solapados y espera el rechazo (SU-28). |
| Verificación en CI | Comprobar que `alembic heads` devuelve un solo head. Dos revisiones con el mismo padre producen varios heads y `alembic upgrade head` falla; se resuelven rebasando la migración más reciente sobre la única cabeza vigente (regla dura 8), sin usar `alembic merge`. |
| Datos semilla | Un comando de inicialización crea el consultorio, el administrador inicial y el catálogo de prestaciones (ver [04](04_modelo_de_datos.md)). Es idempotente. |
| Respaldo | Volcado periódico de PostgreSQL (`pg_dump`) guardado fuera del servidor de la base. La frecuencia y el destino gratuito se definen al elegir el hosting. No se usa el Postgres gratuito de Render, que expira a los 30 días. |
| Recuperación | Restaurar el volcado y volver a levantar los servicios; el siguiente barrido retoma los hitos pendientes. |
| Datos personales | Los respaldos contienen datos de pacientes (RN-58): se guardan con acceso restringido y no se versionan en el repositorio. |

## Integración continua

No hay requisito explícito de integración continua en las fuentes. Mínimo recomendado, sin costo: ejecutar las pruebas del backend y del frontend, construir las imágenes, verificar que `alembic heads` devuelve un solo head y ejecutar el test de integración de la restricción de exclusión, en cada cambio, con el servicio gratuito del repositorio si está disponible. Se deja como supuesto de bajo riesgo, no como requisito de la v1.

## Lista de verificación previa a publicar el enlace público

- [ ] HTTPS activo, `FRONTEND_BASE_URL` apunta al dominio público y `CORS_ORIGINS` está vacío (DD-26).
- [ ] `JWT_SECRET_KEY`, `SWEEP_SHARED_SECRET`, `ORIGIN_HASH_SECRET` y la contraseña de SMTP cargados como secretos, no en el repositorio.
- [ ] `TRUSTED_PROXY_HOPS` coincide con la cantidad de proxies de confianza delante de la API en el host elegido; se comprueba que un encabezado `X-Forwarded-For` enviado por el cliente no cambia el origen que ve la API (si no, el límite de registros por origen no sirve) y que dos clientes distintos tienen orígenes distintos: con `TRUSTED_PROXY_HOPS=0` detrás del proxy del host todos los clientes comparten un origen, el límite de registros se vuelve global y el bloqueo de ingreso de DD-25 pasa a ser por cuenta (cualquiera puede bloquear una cuenta ajena durante la ventana).
- [ ] Neon con `btree_gist` habilitado; migraciones aplicadas (un único head) y datos semilla cargados.
- [ ] `CONSULTORIO_ACTIVO_ID` (obligatoria) está definida y apunta al consultorio sembrado en Neon.
- [ ] El texto que sirve `GET /publico/aviso-privacidad` no contiene ningún marcador entre corchetes (nombre, domicilio y contacto del consultorio cargados, plazo de conservación definido) y lo revisó un profesional del derecho (RN-65); la prueba de producción de C-05 se ejecuta contra el consultorio sembrado.
- [ ] Prestaciones y duraciones confirmadas por el consultorio (SU-23).
- [ ] Profesionales, boxes, horarios y feriados cargados.
- [ ] Prueba real de verificación de correo, confirmación y recuperación de contraseña desde el host elegido (confirma que la salida SMTP o la API de correo funcionan).
- [ ] Disparador externo configurado y último barrido reciente.
- [ ] Cookie de renovación probada en el servicio publicado, con un solo origen y `SameSite=Strict` (DD-26).
- [ ] `/docs` deshabilitado en producción.
- [ ] Respaldo inicial realizado y restauración probada.
- [ ] Teléfono del consultorio cargado para el mensaje de autogestión vencida (RN-33).
