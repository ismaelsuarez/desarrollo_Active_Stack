# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Sistema de Turnos y Agenda Odontológica** (v1, entrega en dos partes: la primera el **2026-10-19**).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
> Regenerado el **2026-10-08**; plazo actualizado el **2026-10-09** (entrega el **2026-10-19**) a partir de la KB actualizada el 2026-10-06 y alineada el 2026-10-08. Se conservan los IDs `C-01` a `C-20`, sus dependencias y el orden de la rebanada vertical; solo cambia lo que exige la arquitectura sin worker persistente (barrido en la API, DD-13), PyJWT/Argon2 (DD-12) y SQLAlchemy asíncrono con migraciones de un solo head (DD-14).

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

Reglas del proyecto que aplican a **todos** los changes:

- **TDD estricto** en la fase apply: cada change se implementa test primero (RED, GREEN, TRIANGULATE, REFACTOR), con red de seguridad previa si modifica archivos existentes. Los tests describen comportamiento (reglas `RN-NN` y criterios de aceptación `US-NNN`), no implementación. Los bullets "Tests primero" de cada scope son el punto de partida de los casos RED. Lo que depende de PostgreSQL (exclusión de solapamientos, `UNIQUE`, reclamación por fila del barrido) se prueba contra PostgreSQL real en contenedor, nunca con dobles.
- **`consultorio_id`** en toda tabla que pertenece a un consultorio, desde la primera migración. Los repositorios lo reciben del `Principal` (el token) cuando hay token. Sin token la regla es por tipo de flujo y no por prefijo de ruta: una ruta que recibe un token de un solo uso enviado por correo o un token de renovación (verificación de correo, restablecimiento de contraseña, `POST /api/v1/turnos/confirmar-por-enlace`, renovación de sesión) lo toma de la fila a la que apunta el token; las demás (`/auth/login`, `/auth/registro`, reenvío de verificación, recuperación de contraseña y las lecturas `/publico/*`) lo resuelve el servidor desde `CONSULTORIO_ACTIVO_ID` (variable obligatoria que agrega C-02 a `Settings`) con una única dependencia (`consultorio_sin_token`, C-03). Nunca viene del cliente (RN-55, RN-59). Hay un único consultorio activo en la v1.
- **Stack fijo**: Python, FastAPI, PyJWT (HS256) y pwdlib con Argon2, SQLAlchemy 2.x asíncrono (asyncpg, `expire_on_commit=False`), Alembic, PostgreSQL (Neon en producción), `aiosmtplib`; React, TypeScript, Vite (en producción el build lo sirve la propia API, DD-26). Docker Compose es entorno local/dev y alternativa en una VM. Presupuesto cero.
- **Sin worker persistente y sin Redis obligatorio**: ningún change crea un proceso aparte ni exige Redis. Lo programado es un barrido idempotente dentro de la API (C-15), con reclamación por fila en PostgreSQL (`FOR UPDATE SKIP LOCKED`, DD-17), disparado por `POST /internal/barrido` o por un bucle `asyncio` local. Redis es opcional y solo auxiliar (límites de intentos); sin `REDIS_URL` todo funciona con PostgreSQL.
- **Migraciones en paralelo con un único head**: varios changes crean migraciones Alembic a la vez. Antes de archivar, cada change rebasa su migración sobre la única cabeza vigente (`alembic heads` debe devolver una sola; el CI lo exige) y se aplica con `alembic upgrade head`, nunca `heads`. El autogenerate de Alembic no detecta restricciones `EXCLUDE`: se revisa cada migración generada. Las migraciones se numeran en el orden en que se archivan los changes.
- **Preguntas abiertas como riesgo explícito**: Q-23 a Q-27 y Q-29 (proveedor de correo, host de la API, quién opera el disparador, `btree_gist` en el proveedor, cuota de Neon, stack completo; Q-28, la cookie, quedó resuelta por DD-26) figuran en el campo **Riesgos / bloqueado por** de cada change afectado y se resumen en [Preguntas abiertas que afectan al plan](#preguntas-abiertas-que-afectan-al-plan). Siguen abiertas: ningún change las resuelve por su cuenta. Q-23, Q-24, Q-26 y Q-29 conciernen al entorno publicado (proveedor y host): en local y en CI PostgreSQL corre como superusuario y `btree_gist` funciona, el correo va a Mailpit y nada se aloja, y la primera parte de la entrega es el repositorio sin despliegue (DD-22). Por eso C-01, C-05, C-07 y C-14 las mencionan como riesgo del despliegue y no esperan su respuesta; se resuelven antes de C-20 (Q-23 también antes de que C-15 y C-16 envíen correo real).
- **Plazo y entrega en dos partes (DD-22, DD-33)**: la fecha del 2026-10-19 no se mueve. La primera parte es la entrega del Trabajo de Integración: la fundación del proyecto, el informe de Discovery y un único change llevado por el ciclo OPSX completo, [C-00] `crear-turno-sin-solapamientos`. Los changes C-01 a C-20 y C-21 se mantienen y son el plan de la segunda parte, sin fecha definida todavía, en el orden de construcción de DD-31. Se entrega el repositorio de GitHub; la primera parte no exige el sistema publicado. [Si el plazo aprieta](#si-el-plazo-aprieta) queda como referencia de qué simplificar dentro de un change.
- **Fuera de la v1**: lo diferido está en la sección [BACKLOG](#backlog-fuera-de-la-v1) y no genera changes.

---

## Árbol de dependencias

```
C-01 foundation-setup
  └── C-02 core-models
        └── C-03 auth-core                          ← desbloquea TODO lo demás
              │
              ├── C-04 abac-policies
              │     ├── C-07 turnos-core            (+ C-06)
              │     │     ├── C-09 availability-public-booking   (+ C-05)
              │     │     │     ├── C-14 frontend-public-booking          (+ C-11)
              │     │     │     └── C-16 milestones-confirmation-release  (+ C-15)
              │     │     │           ├── C-17 whatsapp-one-click
              │     │     │           │     └── C-18 frontend-notifications-ops  (+ C-13, C-15, C-16)
              │     │     │           └── C-19 absenteeism-indicator    (+ C-11)
              │     │     ├── C-10 overbooking-authorization
              │     │     ├── C-15 notifications-outbox-sweep           (+ C-05)
              │     │     └── C-12 frontend-admin-config                (+ C-06, C-11)
              │     └── C-08 patient-records                (+ C-05)
              │           └── C-13 frontend-staff-agenda   (+ C-07, C-10, C-11)
              │
              ├── C-05 patient-account
              │     └── C-11 frontend-shell-auth
              │
              └── C-06 agenda-config                (→ C-07, C-12)

C-14 + C-18 + C-19  ──►  C-20 deploy-hardening   (cierre de la v1)

C-05 + C-08         ──►  C-21 data-subject-rights (planificado para la segunda parte, DD-28)
```

Dependencias completas (fuente de verdad: el campo **Dependencias** de cada change):

| Change | Depende de |
|--------|-----------|
| C-01 | — |
| C-02 | C-01 |
| C-03 | C-02 |
| C-04 | C-03 |
| C-05 | C-03 |
| C-06 | C-03 |
| C-07 | C-04, C-06 |
| C-08 | C-04, C-05 |
| C-09 | C-05, C-07 |
| C-10 | C-07 |
| C-11 | C-05 |
| C-12 | C-06, C-07, C-11 |
| C-13 | C-07, C-08, C-10, C-11 |
| C-14 | C-09, C-11 |
| C-15 | C-05, C-07 |
| C-16 | C-09, C-15 |
| C-17 | C-16 |
| C-18 | C-13, C-15, C-16, C-17 |
| C-19 | C-11, C-16 |
| C-20 | C-14, C-18, C-19 |
| C-21 (planificado para la segunda parte, DD-28) | C-05, C-08 |

### Paralelismo por fase

> Cada "gate" es un punto de sincronización. Los changes dentro de un gate pueden ejecutarse en paralelo.
> Agente A = backend core, Agente B = backend aux, Agente C = frontend (y backend de configuración mientras no hay UI que construir).

```
GATE 0: ninguna
  → C-01 foundation-setup                    [Agente A]
  → Spike de infraestructura (no es un change)  [Agentes B y C — ver nota]

GATE 1: C-01 ✓
  → C-02 core-models                         [Agente A]

GATE 2: C-02 ✓
  → C-03 auth-core                           [Agente A]

GATE 3: C-03 ✓                               ← FORK (3 paralelos)
  → C-04 abac-policies                       [Agente A]
  → C-05 patient-account                     [Agente B]
  → C-06 agenda-config                       [Agente C]

GATE 4: C-04 ✓ + C-06 ✓ (y C-05 ✓)           ← FORK (3 paralelos)
  → C-07 turnos-core                         [Agente A — si C-04 y C-06 ✓]
  → C-08 patient-records                     [Agente B — si C-04 y C-05 ✓]
  → C-11 frontend-shell-auth                 [Agente C — si C-05 ✓]

GATE 5: C-07 ✓ (con C-05 ✓)                  ← FORK (3 paralelos + 1 en cola)
  → C-09 availability-public-booking         [Agente A]
  → C-15 notifications-outbox-sweep          [Agente B]
  → C-12 frontend-admin-config               [Agente C — si C-11 ✓ y C-06 ✓]
  → C-10 overbooking-authorization           [Agente A — en cola tras C-09]

GATE 6: C-09 ✓ (con C-15 ✓ y C-11 ✓)
  → C-16 milestones-confirmation-release     [Agente B — si C-15 ✓]
  → C-14 frontend-public-booking             [Agente C — si C-11 ✓]

GATE 7: C-16 ✓                               ← FORK (2 paralelos, + C-13 si C-10 y C-08 ✓)
  → C-17 whatsapp-one-click                  [Agente B]
  → C-19 absenteeism-indicator               [Agente A — priorizado último, ver nota]
  → C-13 frontend-staff-agenda               [Agente C — si C-07, C-08, C-10, C-11 ✓]

GATE 8: C-13 ✓ + C-15 ✓ + C-16 ✓ + C-17 ✓
  → C-18 frontend-notifications-ops          [Agente C]

GATE 9: C-14 ✓ + C-18 ✓ + C-19 ✓
  → C-20 deploy-hardening                    [Agente A]
```

> Nota de orden: C-19 (indicador de ausentismo) solo necesita C-11 y C-16, pero por instrucción de producto se programa **último** entre los changes funcionales (después de la rebanada vertical y de confirmación/recordatorios). Si hay holgura puede adelantarse sin romper dependencias.
>
> Nota sobre el spike: mientras A cierra C-01 a C-03, B y C no tienen changes desbloqueados. Ese tiempo se usa para un **spike de infraestructura** (no es un change y no genera código de producto): crear el proyecto en Neon y comprobar `CREATE EXTENSION btree_gist` (Q-26), elegir el host de la API y probar desde él una salida SMTP real o una API HTTPS de correo (Q-23, Q-24), y probar el disparador externo contra una ruta de ejemplo (Q-25). El resultado se registra en el diseño de C-20. Si no se hace, esas incógnitas aparecen recién el último día.

### Camino crítico (10 changes — mínimo irreducible)

> **Orden de construcción (DD-31)**: C-01, C-02, C-03; C-04, C-05 y C-06; C-07; C-08 y C-09; C-15 y C-16; C-11 y C-14; C-10 y C-13; y después, si alcanza el tiempo, C-12, C-17, C-18, C-19 y C-20. El camino crítico de abajo muestra las dependencias más largas; el orden de construcción decide qué se hace primero cuando hay una sola línea de trabajo, y adelanta C-15 y C-16 para que los recordatorios y la liberación automática entren en la primera parte de la entrega.

```
C-01 → C-02 → C-03 → C-06* → C-07 → C-09 → C-16 → C-17 → C-18 → C-20
```

`*` C-04, C-05 y C-06 están a la misma profundidad (todos dependen solo de C-03) y se ejecutan en paralelo en GATE 3; los tres son prerrequisito de C-07/C-09 (C-04 y C-06 para C-07, C-05 para C-09). El primero de los tres en retrasarse pasa a ser el crítico. C-15 (barrido) corre en paralelo con C-09 y debe terminar antes de C-16: si C-15 se atrasa, pasa a ser el crítico.

Diez sesiones secuenciales de 4 a 6 horas forman el camino crítico. El 2026-10-12 no había ningún change implementado, así que el camino completo no entra antes del 2026-10-19: la entrega es en dos partes (DD-22) y el camino crítico solo ordena el trabajo. Lo que siga sin terminar el 2026-10-19 pasa a la segunda parte.

### Plan óptimo con 3 agentes

> Supuesto: dos sesiones por agente y por día (mañana y tarde). Día 1 es el primer día de trabajo efectivo; el plan se pensó para empezar el 2026-10-09 y el 2026-10-12 todavía no había empezado. La tabla da el orden y el paralelismo, no fechas comprometidas: con la entrega en dos partes (DD-22), la primera parte llega hasta el paso que esté completo el 2026-10-19.

```
Paso │ Agente A (Backend Core)        │ Agente B (Backend Aux)             │ Agente C (Frontend / config)         │ Día objetivo
─────┼────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┼───────────────
  1  │ C-01 foundation-setup          │ Spike: Neon, host, correo (Q-23/24/26) │ Spike: disparador (Q-25)                   │ Día 1 mañana
  2  │ C-02 core-models               │ Spike (cierre y registro)          │              —                       │ Día 1 tarde
  3  │ C-03 auth-core                 │              —                     │              —                       │ Día 2 mañana
  4  │ C-04 abac-policies             │ C-05 patient-account               │ C-06 agenda-config                   │ Día 2 tarde
  5  │ C-07 turnos-core               │ C-08 patient-records               │ C-11 frontend-shell-auth             │ Día 3 mañana
  6  │ C-09 availability-public-bkg   │ C-15 notifications-outbox-sweep    │ C-12 frontend-admin-config           │ Día 3 tarde
  7  │ C-10 overbooking-authorization │ C-16 milestones-confirm-release    │ C-14 frontend-public-booking         │ Día 4 mañana
  8  │ (holgura: adelantar C-20)      │ C-17 whatsapp-one-click            │ C-13 frontend-staff-agenda           │ Día 4 tarde
  9  │ C-19 absenteeism-indicator     │              —                     │ C-18 frontend-notifications-ops      │ Día 5 mañana
 10  │ C-20 deploy-hardening          │              —                     │ (apoyo en E2E y ajustes de UI)       │ Día 5 tarde
```

Los pasos 1 a 3 son una cadena lineal inevitable (cimientos, modelos, auth): el paralelismo real empieza en GATE 3. La rebanada vertical completa (auth y roles, horarios, agenda sin solapamientos, reserva pública y estados del turno) queda cerrada al terminar el paso 7. En el paso 8, el Agente A puede preparar la parte de C-20 que no depende de código nuevo (workflow del disparador, variables y secretos del host, comprobación del E2E local); no cambia la dependencia formal de C-20.

### Si el plazo aprieta

> Lista priorizada de qué simplificar o recortar **primero** sin romper la rebanada vertical (agenda, reserva pública, estados del turno), ordenada de menor a mayor pérdida funcional. **No es un plan de recorte**: el dueño del proyecto decidió no recortar y entregar en dos partes (DD-22). La lista queda como referencia de qué simplificar si un change no llega completo a su entrega. Ninguna opción agrega alcance.

| Prioridad | Opción | Ahorro estimado | Qué se pierde | Referencia |
|-----------|--------|-----------------|---------------|------------|
| 1 | C-20: respaldo programado de `pg_dump` pasa a respaldo manual documentado (restauración igualmente probada); E2E reducido al camino feliz | ≈ 1/2 sesión | Automatización del respaldo | `12` §Migraciones, respaldo y recuperación |
| 2 | C-19: dejar solo el endpoint `GET /indicadores/ausentismo`, sin la pantalla `features/indicadores` | ≈ 1/2 sesión | El Administrador no lo ve en pantalla (CU-5 queda cubierto solo por API) | `06` US-040, Q-01 |
| 3 | C-12: acotar la pantalla a profesionales con box, horario semanal y bloqueos; usuarios, prestaciones y parámetros del consultorio quedan por semilla/API | ≈ 1/2 a 1 sesión | Edición visual del catálogo y parámetros | `06` Épica 3 |
| 4 | C-05: diferir `recuperar-password` y `restablecer-password` (queda registro, verificación, reenvío y cambio de contraseña) | ≈ 1/2 sesión | Recuperación autoservicio de contraseña | `06` US-004, Q-01 |
| 5 | C-17 y la lista de WhatsApp de C-18: sacar del v1 el mensaje preparado (C-18 queda con la lista de "sin confirmar" y de correos fallidos; sus dependencias pasan a C-13, C-15, C-16) | ≈ 1 a 2 sesiones, y **sale del camino crítico** | CU-2 queda solo con correo automático | `01` CU-2, Q-01 |
| 6 | C-10: omitir la respuesta del profesional (`respuesta-profesional`); queda la autorización registrada y el aviso visible en su agenda | ≈ 1/2 sesión | Aprobación/rechazo del profesional (RN-40 no la hace bloqueante) | `05` RN-40, Q-04 |
| 7 | C-19 completo | ≈ 1 sesión | Indicador de ausentismo (CU-5 confirmado: requiere decisión explícita del Product Owner) | `01` CU-5, Q-01 |

**No se pueden recortar sin romper la rebanada o el problema que da origen al sistema**:

- C-01 a C-04 (cimientos, modelos, autenticación y políticas): todo lo demás depende de ellos.
- C-05 sin el registro y la verificación de correo (la reserva online exige cuenta verificada, RN-02), C-06, C-08, C-11 y C-13 (agenda y fichas del personal).
- C-07 con la restricción de exclusión y su test de dos turnos solapados: es la regla central del sistema (RN-17).
- C-09 y C-14 (disponibilidad y reserva pública con autogestión).
- C-15 y C-16: sin el barrido, `POST /internal/barrido` y los hitos de 48, 24 y 12 horas no existe la confirmación automática ni la liberación, que son el motivo del proyecto.
- C-20 en su mínimo: API, base y frontend publicados, secretos cargados y disparador funcionando. Sin eso no hay enlace público.

---

## PRIMERA ENTREGA — Change del Trabajo de Integración

### [C-00] `crear-turno-sin-solapamientos`
- **Estado**: `[ ]` pendiente
- **Scope**: Crear un turno evitando solapamientos por profesional (y, por el box fijo de RN-10, por box). Es el único change de la primera parte de la entrega (DD-33) y recorre el ciclo OPSX completo: explore, propose, apply, verify y archive
  - Regla de negocio: un profesional no puede tener dos turnos superpuestos; los turnos `cancelado` y `liberado` no cuentan (RN-17); la duración del turno es la de la prestación elegida (RN-13)
  - La garantía final la da la base de datos: restricción de exclusión sobre el profesional y el rango de tiempo `[inicio, fin)`, creada a mano tras `CREATE EXTENSION IF NOT EXISTS btree_gist` (regla dura 7), con la violación traducida a un error de dominio "horario ocupado" (DD-08)
  - Lógica de dominio y su acceso a datos, con el andamiaje mínimo para ejecutar las pruebas contra PostgreSQL real (regla dura 3); sin autenticación, sin pantallas y sin el resto de los estados del turno
  - Escenarios mínimos de la especificación: uno feliz (turno en un horario libre), uno de error de negocio (turno superpuesto con otro del mismo profesional, rechazado) y uno de borde (turno que empieza justo cuando termina otro, aceptado). El alcance exacto se fija en `propose`
- **Dependencias**: ninguna
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: ninguna pregunta abierta. El alcance debe quedar chico: una funcionalidad, no un módulo
- **Relación con la segunda parte**: es una rebanada de C-07 (`turnos-core`) con la base mínima de C-01 y C-02; esos changes reutilizan o absorben lo hecho acá
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-10, RN-13, RN-14, RN-17
  - `knowledge-base/04_modelo_de_datos.md` §turno
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-08, DD-23, DD-33
  - `docs/discovery/informe-discovery.md` sección D (MVP recomendado)

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**: Scaffolding del monorepo e infraestructura base (local/dev; sin worker)
  - Estructura: `backend/` en capas (`app/domain`, `app/application`, `app/infrastructure`, `app/api` con `internal/`, `app/core`), `frontend/` (Vite + React + TypeScript), `docker-compose.yml`, `.env.example` (con `APP_ENV=development`; `scripts/smoke_compose.sh` y los jobs de CI que usan Compose crean `.env` a partir de él si no existe)
  - `docker-compose.yml` **sin clave `version`**, con servicios `db` (PostgreSQL con volumen y healthcheck), `migrate` (`alembic upgrade head` y termina), `api` (healthcheck, `restart: unless-stopped`), `frontend` (etapa `dev` de su Dockerfile; el build de producción lo sirve la API, DD-26, y su etapa `build` produce `dist`), `redis` (opcional, perfil `redis`) y `mailpit` (perfil `dev`); `depends_on` con `service_healthy` y `service_completed_successfully`; secretos montados en `/run/secrets/<nombre>` (la carpeta `secrets/` no se versiona). No hay servicio `worker`
  - Endpoint de salud de la API (`GET /api/v1/health`, sin consultar la base) usado por el healthcheck
  - `core/config.py`: lee las variables de `08` (y los archivos de `/run/secrets` cuando existen), falla al arrancar sin las obligatorias (`APP_ENV`, `DATABASE_URL`, `JWT_SECRET_KEY`; ninguna tiene valor por defecto) o con una `JWT_SECRET_KEY` de menos de 32 bytes; la configuración de base de datos se carga por separado para que `migrate` no necesite secretos de la API, y las migraciones usan `MIGRATIONS_DATABASE_URL` si está definida; `REDIS_URL` opcional; logging estructurado con identificador de solicitud, que oculta todo campo secreto de la configuración por su tipo y no por una lista de nombres
  - Alembic inicializado con `alembic init -t async` (`env.py` asíncrono, `compare_type=True`, `alembic/versions/`); migración base con `CREATE EXTENSION IF NOT EXISTS btree_gist`
  - pytest con PostgreSQL en contenedor para los tests de integración; Vitest + Testing Library en el frontend
  - CI gratuito: tests de backend y frontend, build de la imagen del backend y de la etapa `build` del frontend, `alembic upgrade head` sobre una base vacía y **verificación de un único head** (`alembic heads`) en cada cambio, más el arranque real del entorno (`docker compose up` sobre un volumen vacío: `migrate` termina con 0, `api` saludable y sin root)
  - Tests primero: `GET /api/v1/health` responde 200; la configuración rechaza un arranque sin `APP_ENV`/`DATABASE_URL`/`JWT_SECRET_KEY` o con una clave de firma corta, y acepta los valores desde un archivo de secreto; el logger no emite valores de variables sensibles; el chequeo de heads falla con dos revisiones del mismo padre (fixture) y pasa con una; `docker compose config` valida y el archivo no contiene la clave `version`
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Riesgos / bloqueado por**: ninguno abierto que bloquee este change. Q-26 (la migración base falla si el proveedor de PostgreSQL publicado no permite `btree_gist`; Neon figura como soportado) y Q-29 (si se exige el stack completo con Redis y proceso persistente, el mismo Compose se despliega en una VM) afectan solo al despliegue publicado y se resuelven antes de C-20, no antes de este change: en local y en CI PostgreSQL corre como superusuario y la migración base funciona (DD-22).
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md`
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Persistencia y migraciones, §Variables de entorno, §Estrategia de pruebas
  - `knowledge-base/12_devops_y_despliegue.md` §Servicios de Docker Compose, §Migraciones, respaldo y recuperación, §Integración continua

---

### [C-02] `core-models`
- **Estado**: `[ ]` pendiente
- **Scope**: Modelos base con `consultorio_id`, sesión asíncrona, unidad de trabajo y semilla inicial
  - Modelos SQLAlchemy 2.x tipados (`DeclarativeBase`, `Mapped[...]`, `mapped_column`) y migración de identidad, con clave primaria `bigint` con identidad en todas las tablas (DD-23): `consultorio` (parámetros `modo_liberacion`, `horas_confirmacion`/`recordatorio`/`liberacion`/`limite_paciente` y los de reserva `minutos_granularidad` 15, `dias_anticipacion_maxima` 60 y `max_turnos_activos_paciente` 2, con sus `CHECK`, RN-64), `usuario` (rol enum de cinco valores, `email_verificado`, `aviso_privacidad_aceptado_en` y `aviso_privacidad_version` nulos, con sus `CHECK` (los dos nulos o los dos presentes, y `CHECK (rol <> 'paciente' OR aviso_privacidad_aceptado_en IS NOT NULL)`), RN-65; sin columnas de bloqueo: el bloqueo de ingreso vive en `intento_ingreso`, que crea C-03, DD-25), `token_usuario`, `refresh_token`, `paciente`. `token_usuario.turno_id` se crea acá como columna nula sin clave foránea, porque la tabla `turno` todavía no existe; la clave foránea la agrega la migración de C-07
  - `consultorio_id` NOT NULL con índice en todas las tablas salvo `consultorio`; `UNIQUE (consultorio_id, nombre_usuario)`, `UNIQUE (consultorio_id, email)`, `UNIQUE (consultorio_id, dni)`, `UNIQUE (usuario_id)` en `paciente`; `nombre_usuario` y `email` normalizados (sin espacios en los extremos y en minúsculas) y `dni` solo con dígitos, exigidos con `CHECK` en la base y normalizados por la aplicación antes de escribir y de buscar (`04`)
  - Convenciones del modelo (`04`): enums como `text` con `CHECK` (`native_enum=False`), `naming_convention` en el `MetaData`, `CHECK` del orden de los plazos del consultorio. Ninguna consulta usa `now()` ni `CURRENT_TIMESTAMP` de SQL: el instante llega como parámetro desde el puerto `Reloj`, para que el reloj simulado gobierne también las consultas (regla dura 4); `creado_en` y `actualizado_en` los fija la aplicación con ese mismo reloj. `APP_TIMEZONE` solo da el valor inicial de `consultorio.zona_horaria` en la semilla
  - Acceso asíncrono: `create_async_engine("postgresql+asyncpg://...")`, `async_sessionmaker(engine, expire_on_commit=False)` y `engine.dispose()` al cerrar la aplicación
  - Base de infraestructura: mixin de timestamps, repositorio base que **siempre** filtra por el `consultorio_id` que recibe (el `Principal` lo entrega en C-03; nunca viene del cliente), `UnitOfWork`, puerto `Reloj` (reloj del sistema y reloj simulado)
  - `Settings` (`core/config.py`): agrega la variable obligatoria `CONSULTORIO_ACTIVO_ID` (sin valor por defecto; identificador del único consultorio activo de la v1, por ejemplo `1`): el arranque falla si falta. C-03 solo la lee (RN-59). Como el arranque falla sin ella, este change modifica los archivos de C-01 que arrancan la aplicación para que el stack siga levantando; son estos lugares, todos fuera de `openspec/` (el change de C-01 ya está archivado y no se toca): (a) el `.env` que leen los servicios de `docker-compose.yml` (la variable no es sensible): la necesitan `api` (que carga `Settings`) y el servicio `seed` (que carga `SeedSettings`, que también la define); `alembic upgrade head` carga solo la configuración de base de datos y no la necesita; (b) el workflow de integración continua (`.github/workflows/ci.yml`), en los jobs que corren `pytest` y `alembic upgrade head`; (c) las fixtures de `Settings` de los tests (`tests/unit/test_config.py`, `tests/integration/conftest.py` y toda fixture que construya `Settings`), incluidos los tests de C-01 que armaban `Settings` solo con `DATABASE_URL` y `JWT_SECRET_KEY`; (d) `.env.example`; y (e) el `README.md`, si lista las variables obligatorias
  - Value object `Dni`; sin borrado físico (`activo`)
  - Semilla idempotente: consultorio inicial (48/24/12/24 h, modo automático, zona `America/Argentina/Buenos_Aires`) y administrador desde `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` con correo verificado; la semilla crea el consultorio con el identificador que indica la variable obligatoria `CONSULTORIO_ACTIVO_ID` (RN-59). La ejecuta el comando `python -m app.seed`, en un servicio de Compose nuevo de una sola ejecución, `seed`, que usa la imagen del backend, carga su propia `SeedSettings` y no `Settings` completo (extiende la configuración de base de datos solo con `CONSULTORIO_ACTIVO_ID`, `APP_TIMEZONE`, `BOOTSTRAP_ADMIN_EMAIL` y `BOOTSTRAP_ADMIN_PASSWORD`, de modo que los secretos obligatorios que agreguen los changes siguientes no rompan la semilla), recibe como secretos solo `database_url` y `bootstrap_admin_password` (`scripts/dev_secrets.sh` gana `secrets/bootstrap_admin_password.txt` en este change) y nada más, depende de `migrate` con `service_completed_successfully` y del que pasa a depender `api`; los changes posteriores que agreguen un secreto obligatorio tocan solo `api`; este change modifica el requisito "Servicios del entorno local" de C-01 con un delta, y actualiza el test de contrato de Compose y `scripts/smoke_compose.sh`. En producción es un paso del despliegue (C-20)
  - Tests primero: un repositorio no devuelve filas de otro consultorio; las claves únicas rechazan duplicados dentro del consultorio y los admiten entre consultorios; la base rechaza un consultorio con los plazos fuera de orden y un valor de enum no declarado; la base rechaza una cuenta de rol `paciente` sin `aviso_privacidad_aceptado_en` y admite una de personal sin él; con el reloj simulado, `creado_en` es el instante simulado; un correo o un nombre de usuario que solo difiere en mayúsculas o en espacios de los extremos es un duplicado, y la base rechaza una fila sin normalizar o un `dni` con puntos; la configuración falla al arrancar sin `CONSULTORIO_ACTIVO_ID` y la acepta cuando está definida; los tests de configuración de C-01 siguen pasando con la variable agregada a sus fixtures, la CI corre con ella definida y `docker compose config --quiet` valida con la variable cargada en `migrate` y `api`; la semilla crea el consultorio con ese identificador y corrida dos veces no duplica; el servicio `seed` arranca con solo sus dos secretos (`SeedSettings` no exige `JWT_SECRET_KEY` ni ningún otro secreto de `api`, y el test de contrato de Compose comprueba que `seed` recibe únicamente `database_url` y `bootstrap_admin_password`); `scripts/dev_secrets.sh` genera `bootstrap_admin_password.txt` y no lo pisa en una segunda ejecución; el reloj simulado avanza de forma determinista; un objeto cargado sigue accesible tras el `commit` (`expire_on_commit=False`) sin recarga implícita; `alembic upgrade head` sobre base vacía deja un solo head
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Principios, §consultorio, §usuario, §token_usuario, §refresh_token, §paciente, §Datos semilla
  - `knowledge-base/05_reglas_de_negocio.md` §Multiconsultorio y protección de datos (RN-55 a RN-59)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados, §Capas del backend, §Persistencia y migraciones, §Variables de entorno (`CONSULTORIO_ACTIVO_ID`)
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-14, DD-16 y supuestos SU de modelado

---

## FASE 1 — Identidad y acceso

### [C-03] `auth-core`
- **Estado**: `[ ]` pendiente
- **Scope**: Autenticación JWT (PyJWT) y RBAC base
  - `POST /api/v1/auth/login` — JWT de acceso HS256 con PyJWT (`JWT_SECRET_KEY`, `JWT_ALGORITHM`) y claims `sub`, `consultorio_id`, `rol`, `jti` emitidos solo por el servidor (nunca la ficha ni el identificador del paciente: el vínculo entre la cuenta y su ficha se lee en cada solicitud, RN-06, RN-63), con el consultorio que entrega `consultorio_sin_token` (el cliente no lo envía); refresh con rotación
  - `POST /api/v1/auth/refresh` — rotación, el token reutilizado revoca la cadena; `POST /api/v1/auth/logout`; `GET /api/v1/auth/me`
  - Hash de contraseña **solo Argon2 con pwdlib** (sin elección de algoritmo; nunca en logs ni respuestas, RN-04); si el usuario no existe se verifica contra un hash ficticio para igualar tiempos; mensaje de error idéntico para usuario inexistente y contraseña incorrecta
  - Objeto `Principal` (usuario, `consultorio_id`, rol) construido desde el token validado; es la única fuente del `consultorio_id` para los repositorios cuando hay token
  - Dependencia única `consultorio_sin_token` para las rutas sin token que no reciben ningún token (login, registro, reenvío de verificación, recuperación de contraseña y las lecturas `/publico/*`; C-05 y C-09 la reutilizan): lee `CONSULTORIO_ACTIVO_ID` de `Settings` (variable obligatoria que agregó C-02; este change solo la lee), verifica que el consultorio exista y esté `activo` y devuelve su `consultorio_id`; ninguna ruta lo recibe del cliente. Las rutas que reciben un token enviado por correo o de renovación toman el consultorio de la fila a la que apunta el token (RN-59): este change lo construye para la renovación de sesión; la verificación de correo y el restablecimiento de contraseña los construye C-05 y la confirmación por enlace (`POST /api/v1/turnos/confirmar-por-enlace`), C-16. Pasar a varios consultorios implica cambiar esta dependencia y las rutas públicas (DD-16)
  - Bloqueo temporal por intentos fallidos (RN-09, DD-25) por el par cuenta y origen, con la tabla `intento_ingreso` (migración de este change; identificador y origen guardados como HMAC-SHA256 con `ORIGIN_HASH_SECRET`; índices `(consultorio_id, identificador_hash, origen_hash, creado_en)`, `(consultorio_id, origen_hash, creado_en)` y `(creado_en)`) detrás de un puerto de límites. Orden de cada intento: primero inserta su renglón y lo confirma en su propia transacción corta, después cuenta los renglones del par dentro de `LOGIN_LOCKOUT_MINUTES` y, si superan `LOGIN_MAX_ATTEMPTS`, responde el mismo 401 genérico sin verificar la contraseña; con origen determinado cuenta además los renglones del origen (todas las cuentas) y, si superan `LOGIN_MAX_ATTEMPTS_PER_ORIGIN`, responde el mismo 401 (sin origen determinado no rige el límite por origen); un ingreso correcto borra los renglones del par. Como en `intento_registro`, no hay candado: solicitudes simultáneas pueden superar el límite solo en la cantidad de solicitudes en vuelo. Quienes comparten una dirección (por ejemplo, la red del consultorio) comparten el origen: alguien de esa red puede bloquear una cuenta del personal desde esa red durante la ventana; la cuenta ingresa desde otro origen y el bloqueo termina solo. Como el barrido todavía no existe (C-15), el ingreso purga al escribir: cada inserción de un intento borra también los renglones de `intento_ingreso` de más de 24 horas, de todos los pares (usa el índice `(creado_en)`), con un caso de uso `PurgarIntentosIngreso` que C-15 reutiliza. El adaptador Redis es opcional y no se construye salvo que se despliegue Redis. Este change agrega a `Settings` `ORIGIN_HASH_SECRET` (obligatoria, sensible) y `TRUSTED_PROXY_HOPS`, y la función que resuelve el origen (`X-Forwarded-For` confiando solo en esa cantidad de saltos, DD-21); C-05 las reutiliza. Valores por defecto en configuración: `LOGIN_MAX_ATTEMPTS=5`, `LOGIN_LOCKOUT_MINUTES=15`, `LOGIN_MAX_ATTEMPTS_PER_ORIGIN=20`, `JWT_ACCESS_TTL_MINUTES=15`, `JWT_REFRESH_TTL_DAYS=7`; contraseña de 8 caracteres como mínimo. Como `ORIGIN_HASH_SECRET` es obligatoria, este change la agrega en los lugares que arrancan la aplicación (secreto de `api` en `docker-compose.yml`, solo `api`: el servicio `seed` carga `SeedSettings` y no la necesita; `scripts/dev_secrets.sh`, el workflow de CI y las fixtures de `Settings`)
  - Token de renovación en cookie `HttpOnly`, `Secure` y `SameSite` configurables por entorno, con protección CSRF en el endpoint de renovación; por defecto `SameSite=Strict`, porque el frontend y la API comparten origen (DD-26), y CORS deshabilitado salvo que `CORS_ORIGINS` habilite un origen
  - Un paciente con correo sin verificar no ingresa (RN-02)
  - RBAC como **fábricas de dependencias** de FastAPI: `usuario_actual`, `requiere_rol(...)` con denegación por defecto (matriz de `03`)
  - Tests primero: login correcto e incorrecto; no distingue la causa; con usuario inexistente se ejecuta igualmente la verificación contra el hash ficticio; 5 ingresos fallidos bloquean el par cuenta y origen y el sexto responde el mismo 401 aunque la contraseña sea correcta; la misma cuenta ingresa desde otro origen mientras el primer par está bloqueado; el bloqueo ocurre igual con un usuario inexistente; el par se desbloquea con el reloj simulado pasada la ventana y un ingreso correcto borra sus intentos; ocho ingresos con contraseña incorrecta simultáneos del mismo par (insertar y confirmar antes de contar): como máximo `LOGIN_MAX_ATTEMPTS` llegan a verificar la contraseña y todos responden el mismo 401; los primeros 20 intentos fallidos de un mismo origen contra cuentas distintas (o inexistentes) se verifican y el 21.º, de cualquier cuenta y aun con la contraseña correcta, responde el mismo 401 sin verificar, mientras que desde otro origen ingresa; con origen no determinado no rige el límite por origen; la purga al escribir borra los renglones de más de 24 horas de cualquier par y conserva los recientes; la tabla no guarda el nombre de usuario ni la dirección; la configuración falla al arrancar con `LOGIN_LOCKOUT_MINUTES` mayor a 1.440 (la retención de `intento_ingreso`) y sin `ORIGIN_HASH_SECRET` y un evento de log que contiene su valor lo muestra como `***`; un `X-Forwarded-For` enviado por el cliente no cambia el origen con `TRUSTED_PROXY_HOPS=0`; una contraseña de 7 caracteres se rechaza; token expirado; token con otro algoritmo o sin firma rechazado; rotación y reutilización de refresh; rol sin permiso responde 403; un cuerpo que trae `consultorio_id`, un rol u otro campo no declarado se rechaza con 422 (regla dura 11, `extra='forbid'`) y no cambia el consultorio ni los claims, que salen solo del servidor; el token de acceso de un paciente trae solo los claims declarados y no la ficha ni el identificador del paciente; `consultorio_sin_token` devuelve el consultorio configurado y falla si no existe o está inactivo; el ingreso funciona sin que el cliente envíe consultorio; la renovación de sesión toma el consultorio de la fila del `refresh_token` (los tests de la verificación de correo y del restablecimiento viven en C-05 y los de la confirmación por enlace en C-16, donde se construyen esos endpoints)
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto. Q-28 quedó resuelta por DD-26 (mismo origen) y Q-16 por DD-25 (políticas de cuenta).
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/05_reglas_de_negocio.md` §Cuentas y autenticación (RN-01 a RN-09) y RN-59
  - `knowledge-base/07_flujos_principales.md` Flujo 2
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-12, DD-16, DD-25, DD-26 y SU-27

---

### [C-04] `abac-policies`
- **Estado**: `[ ]` pendiente
- **Scope**: Los cuatro atributos ABAC como funciones de política puras en el dominio
  - Dominio puro (sin frameworks): entidad `Turno` mínima, `EstadoTurno`, tabla de transiciones de RN-18, `Intervalo`
  - `domain/policies`: `mismo_consultorio` (A2, siempre primero), `es_dueno_de_agenda` y `es_titular_del_turno` (A1; esta recibe como argumento la ficha vigente de la cuenta, `ficha_vigente_id`, que carga la capa de aplicación porque ni el `Principal` ni el token la traen, RN-06, RN-63), `turno_es_modificable` y `transicion_permitida` (A3), `dentro_de_ventana_paciente` y `hora_de_inicio_alcanzada` (A4), `puede_autorizar_sobreturno`, `puede_ver_paciente`, `puede_ver_ausentismo`
  - Punto de entrada `acceso.autorizar(usuario, accion, recurso, contexto)` invocado desde los casos de uso (RBAC ya se aplicó en el endpoint con C-03), con denegación por defecto; el `contexto` lleva lo que no está en el token: el instante `ahora` y la ficha vigente de la cuenta (`ficha_vigente_id`); el instante `ahora` se inyecta
  - Traducción en la API según la regla de códigos de `11`: 404 cuando revelar que el recurso existe expondría datos (turnos y fichas de otra persona, cualquier recurso de otro consultorio); 403 cuando la existencia del recurso ya es conocida dentro del consultorio y solo se deniega la acción (la agenda de otro profesional, una acción que el rol no puede hacer, los rechazos por estado o por ventana de tiempo, A3 y A4); 409 queda para los conflictos con el estado actual de los datos que se detectan al escribir (horario ocupado, una escritura condicional que no afecta ninguna fila, el máximo de turnos activos de RN-64 d) y no es un código de política; el rechazo se registra con usuario, acción y motivo, sin datos personales
  - Rol `administrativo` con permisos reservados y sin acceso funcional
  - Tests primero: tabla rol × acción × atributo con caso permitido y denegado por cada política; `es_titular_del_turno` compara con la ficha vigente que recibe y una cuenta sin ficha (`None`) nunca es titular; límites exactos de la ventana de 24 h (en el límite y a ±1 segundo); `sobreturno.responder` permitido al profesional y al administrador solo sobre su propia agenda (DD-24); `atendido` inmutable ni para el administrador; `ausente` no se cancela ni se reprograma, ni siquiera por el administrador, y solo admite `turno.corregir_ausente` (RN-19); `cancelado` y `liberado` finales; `turno.liberar`: Recepción y Administrador liberan un `pendiente` en modo manual aunque no tenga marca y, en cualquiera de los dos modos, un `pendiente` con la marca "sin confirmar" (en modo automático sin marca se deniega; Profesional y Paciente siempre denegados); consultorio ajeno siempre denegado
- **Dependencias**: C-03
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto.
- **Leer antes**:
  - `knowledge-base/11_politicas_de_acceso_abac.md` (completo)
  - `knowledge-base/03_actores_y_roles.md` §RBAC
  - `knowledge-base/05_reglas_de_negocio.md` §Turnos y solapamientos (RN-18, RN-19), §Cancelación y reprogramación (RN-33 a RN-38)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados

---

### [C-05] `patient-account`
- **Estado**: `[ ]` pendiente
- **Scope**: Cuenta del paciente: registro, verificación, recuperación y correo SMTP
  - `POST /api/v1/auth/registro` — exige `acepta_aviso_privacidad: true` y `aviso_privacidad_version` igual a la versión vigente del aviso, que el backend guarda junto con el texto (copiados de `knowledge-base/13`) y sirve en `GET /api/v1/publico/aviso-privacidad` (ruta sin token que construye este change; el consultorio sale de `consultorio_sin_token` y el nombre, el domicilio y el contacto del responsable, de `consultorio.nombre`, `consultorio.direccion` y `consultorio.telefono`); el frontend muestra lo que devuelve esa ruta y reenvía la versión que mostró, sin copiar el texto; si falta la aceptación o la versión no coincide, responde 422 sin crear nada, y si se acepta guarda la fecha y la versión en la cuenta (RN-65, DD-28); crea `usuario` rol `paciente` e inserta la ficha de `paciente` con `INSERT ... ON CONFLICT (consultorio_id, dni) DO NOTHING`, para que la transacción sobreviva a un DNI repetido; si no insertó nada (el DNI ya tiene ficha, con o sin cuenta, o la creó otro registro simultáneo) no crea una segunda ni la vincula y sigue por el camino de la solicitud: guarda una `solicitud_vinculacion` `pendiente` con el DNI declarado (RN-49, RN-62). La respuesta y el correo de verificación son idénticos exista o no el DNI; eso no cierra del todo la fuga de pertenencia (quien se registra con el DNI de otra persona y verifica su propio correo infiere el DNI del 403 de la reserva), riesgo aceptado y acotado con el límite de solicitudes por origen de este endpoint, el estado de la vinculación visible solo con el correo verificado y el registro de cada solicitud (RN-62, DD-19). El consultorio lo resuelve `consultorio_sin_token` (C-03)
  - Migración `solicitud_vinculacion` (`consultorio_id`, `usuario_id` con `UNIQUE`, `dni_declarado`, `estado` `pendiente`/`vinculada`/`rechazada`, `paciente_id` nulo, `resuelta_por_id`, `resuelta_en`, `motivo_rechazo`, `creada_en`; índice `(consultorio_id, estado, creada_en)`; `UNIQUE (consultorio_id, dni)` de `paciente` no cambia). La resolución por Recepción (vincular, rechazar, desvincular, reactivar una ficha y el correo `vinculacion_rechazada` con su plantilla) la agrega C-08. Costo aceptado: una cuenta sin ficha (solicitud `pendiente` o `rechazada`) no reserva en línea (lo aplica C-09)
  - `POST /api/v1/auth/verificar-email` (el consultorio sale de la fila del token, RN-59), `POST /api/v1/auth/reenviar-verificacion`
  - `POST /api/v1/auth/recuperar-password` (respuesta idéntica exista o no el correo), `POST /api/v1/auth/restablecer-password` (revoca sesiones activas; el consultorio sale de la fila del token, RN-59)
  - Cambio de contraseña con la actual y actualización de teléfono/correo del paciente; cambiar el correo exige verificarlo de nuevo (US-005)
  - `token_usuario`: aleatorio, guardado hasheado, un solo uso, con vencimiento (`EMAIL_VERIFICATION_TTL_HOURS`, `PASSWORD_RESET_TTL_MINUTES`)
  - Puerto `EnviadorCorreo` + adaptador SMTP con `EmailMessage` de la biblioteca estándar y `aiosmtplib` (587 con STARTTLS, `SMTP_*`; sin `fastapi-mail`) + plantillas de verificación y recuperación sin datos sensibles
  - Tabla `notificacion` (migración; `turno_id` se crea como columna nula sin clave foránea porque `turno` todavía no existe, y la clave foránea la agrega la migración de C-07; con el estado intermedio `enviando`, la columna `reclamada_en` y `CHECK ((estado = 'enviando') = (reclamada_en IS NOT NULL))`, RN-61; el enum de `tipo` tiene los diez valores de `04` y la columna `ciclo` la agrega C-15; `vinculacion_rechazada` la programa y despacha C-08 con este mismo caso de uso) donde se programa cada correo (`verificacion_email`, `recuperacion_password`) y caso de uso `DespacharNotificacion` que reclama la fila con `SELECT ... FOR UPDATE SKIP LOCKED` y la pasa de `programada` a `enviando` (`reclamada_en = ahora`, `intentos + 1`) en una transacción corta confirmada antes de enviar, envía fuera de toda transacción y registra el resultado en una segunda transacción corta, condicionada a la reclamación propia (`UPDATE ... WHERE id = :id AND estado = 'enviando' AND reclamada_en = :valor_que_fijó_este_envío`: si no afecta ninguna fila perdió la reclamación y descarta su resultado sin escribir) (`enviada`, o de vuelta a `programada`, o `fallida` al agotar `NOTIFICATION_MAX_ATTEMPTS`); una reclamación más vieja que `NOTIFICATION_CLAIM_TTL_SECONDS` se revisa con la misma validación de vigencia por tipo que la primera reclamación (tabla "Vigencia por tipo" de `04`; este change implementa la de los tipos sin turno: `verificacion_email` y `recuperacion_password` siempre vigentes y `vinculacion_rechazada` vigente solo con el correo de la cuenta verificado, si no `omitida`; la de los tipos con turno la agrega C-15), respeta el máximo de intentos (al alcanzarlo, `fallida` sin reenviar) y el tope diario (solo reenvía si no se alcanzó). Toda salida de `enviando` hacia otro estado deja `reclamada_en` en nulo, como exige el `CHECK`. La entrega es al menos una vez: una caída entre el envío y el resultado, o un envío más lento que el plazo, puede repetir un correo. Aquí se invoca como tarea en segundo plano de FastAPI justo después de programar, para que el correo de verificación no espere al próximo barrido de 5 minutos. C-15 reutiliza el mismo caso de uso para lo que quede `programada` o con reclamación vencida
  - Tope diario de correos (`EMAIL_DAILY_LIMIT`, 500 por defecto), verificado antes de toda reclamación que enviaría un correo: con el tope alcanzado el despacho no reclama más filas de canal `email`, que siguen `programada` sin consumir intentos y sin pasar por `enviando`, ni reclama de nuevo una `enviando` vencida. El conteo del día suma las filas de canal `email` `enviada` con `enviada_en` dentro del día calendario en la zona del consultorio y las que están `enviando` con la reclamación no vencida; pasar una reclamación vencida a `omitida` o a `fallida` no envía nada y no pasa por el tope; cupo propio de los correos de cuenta (`EMAIL_DAILY_LIMIT_ACCOUNT`, 150 por defecto, DD-29): un correo de cuenta se reclama solo si no se alcanzó ni su cupo ni el tope total, y la configuración falla al arrancar si el cupo no es menor que el tope; alerta al 80 % (`EMAIL_DAILY_ALERT_RATIO`) dentro del despacho
  - Límite de solicitudes sobre registro (por origen), recuperación y reenvío detrás de un puerto de límites: recuperación y reenvío en PostgreSQL por defecto (conteo de tokens y notificaciones recientes), Redis solo si se despliega. El límite del registro es de este change y usa la tabla mínima `intento_registro` (`consultorio_id`, `origen_hash`, `creado_en`; índices `(consultorio_id, origen_hash, creado_en)` y `(creado_en)`; migración propia), cuyo renglón se escribe y se confirma antes de que empiece la transacción del registro, en la misma sesión de la solicitud, para que el intento cuente aunque después falle la validación o el registro (SU-45), y las variables `REGISTRATION_LIMIT_PER_ORIGIN`, `REGISTRATION_LIMIT_GLOBAL` y `REGISTRATION_LIMIT_WINDOW_MINUTES` (con sus valores de ejemplo de `08`); `TRUSTED_PROXY_HOPS`, `ORIGIN_HASH_SECRET` y la función que resuelve el origen ya existen desde C-03, que las usa para el bloqueo de ingreso (DD-25), y este change las reutiliza (RN-62, DD-21). El origen es la dirección del cliente tomada de `X-Forwarded-For` confiando solo en `TRUSTED_PROXY_HOPS` saltos (la entrada a esa cantidad de posiciones desde la derecha; con `0` el encabezado se ignora y vale la dirección de la conexión directa); si no se puede determinar, rige el límite global. Se guarda solo como HMAC-SHA256 con `ORIGIN_HASH_SECRET`: nunca la dirección en claro, tampoco en logs. Un caso de uso `PurgarIntentosRegistro` borra los renglones de más de 24 horas: como el barrido todavía no existe (C-15), lo ejecuta este change al escribir, y cada inserción de un intento de registro borra también los renglones de más de 24 horas (usa el índice `(creado_en)`); el barrido de C-15 lo reutiliza. `ORIGIN_HASH_SECRET` ya está cargada en todos los lugares que arrancan la aplicación desde C-03 (secreto de `api`; el servicio `seed` usa `SeedSettings` y no la carga) y los logs ya la ocultan por ser un campo secreto de `Settings` (C-01 define el mecanismo por el tipo del campo); este change no agrega variables obligatorias
  - Tests primero: con el cupo de cuenta alcanzado, un correo de verificación queda `programada` sin consumir intentos y un correo de turno (fila preparada con una fixture) se envía igual; con el tope total alcanzado no sale ninguno; la configuración rechaza un cupo igual o mayor que el tope; un registro sin aceptar el aviso o con una versión vieja responde 422 y no crea cuenta, ficha ni solicitud; un registro aceptado guarda la fecha (reloj simulado) y la versión; `GET /api/v1/publico/aviso-privacidad` devuelve el texto y la versión vigentes con los datos del consultorio en lugar de los marcadores, y esa versión es la única que acepta el registro; con `APP_ENV=production`, una prueba falla si el texto servido todavía contiene un marcador entre corchetes (pasa con un consultorio de fixture con nombre, dirección y teléfono completos, y falla con la dirección nula; la lista de C-20 la repite contra el consultorio sembrado); token usado, vencido o inexistente rechazado; no enumeración de cuentas; un DNI existente crea la cuenta sin segunda ficha y con una solicitud `pendiente`, y la respuesta y el correo son idénticos con un DNI existente y con uno nuevo; un DNI nuevo crea la ficha vinculada a la cuenta y ninguna solicitud (que esa cuenta reserve se prueba en C-09, que construye la reserva); dos registros simultáneos con el mismo DNI nuevo dejan una ficha y una solicitud, ninguna transacción se aborta y ambos reciben la misma respuesta; el registro supera el límite por origen y responde 429 sin dejar un renglón nuevo; un registro rechazado (usuario o correo ya existentes) o que falla dentro de su transacción deja igualmente su renglón de `intento_registro`, porque se confirmó antes de que empezara; con `TRUSTED_PROXY_HOPS=1` el origen es la última entrada de `X-Forwarded-For` y una entrada anterior enviada por el cliente no lo cambia, y con `0` el encabezado se ignora; sin origen determinable (menos entradas que saltos o dirección inválida) rige el límite global y también responde 429 al superarlo; el renglón guarda un HMAC y nunca la dirección; la purga borra los renglones de más de 24 horas y conserva los recientes, y la ejecuta cada inserción de un intento de registro (un renglón de 25 horas desaparece al registrar uno nuevo); la configuración falla al arrancar con una ventana mayor a 1.440 minutos; la verificación de correo y el restablecimiento de contraseña toman el consultorio de la fila del token (un `consultorio_id` enviado por el cliente se rechaza con 422 por ser un campo no declarado, regla dura 11) y el registro, el reenvío y la recuperación toman el consultorio configurado (`consultorio_sin_token`); sesiones revocadas al restablecer; el correo se prueba con un doble del puerto y el adaptador SMTP contra `mailpit`; un doble despacho concurrente de la misma notificación envía una sola vez (la segunda reclamación no obtiene la fila); una reclamación `enviando` vencida se retoma y una vigente no; un envío que termina después de que otro barrido retomó la fila no escribe su resultado (la condición por `reclamada_en` no afecta ninguna fila) y la fila conserva el resultado y los intentos del segundo; una reclamación vencida con los intentos agotados pasa a `fallida` sin reenviar; toda salida de `enviando` (a `enviada`, `programada`, `fallida` u `omitida`) deja `reclamada_en` nulo sin violar el `CHECK`; un `vinculacion_rechazada` cuya cuenta no tiene el correo verificado pasa a `omitida` al reclamarse y al revisarse vencido, mientras que `verificacion_email` y `recuperacion_password` se envían siempre; una caída simulada entre el envío y el resultado deja la fila `enviando` y el reintento la reenvía (entrega al menos una vez); al llegar al 80 % del tope se emite la alerta y al 100 % el despacho no reclama más correos: quedan `programada`, sin consumir intentos, y el conteo incluye las filas `enviando` con la reclamación vigente y no las vencidas; con el tope alcanzado una `enviando` vencida que enviaría de nuevo no se reclama y queda como estaba, mientras que una vencida con los intentos agotados (`fallida`) o de un tipo no vigente (`omitida`) se resuelve igual; contraseña nunca en logs; un evento de log del registro no contiene la dirección de origen
- **Dependencias**: C-03
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto que bloquee este change. Q-24 y Q-23 afectan solo al despliegue publicado y se resuelven antes de C-20 (Q-23 también antes de que C-15 y C-16 envíen correo real), no antes de este change: en local y en CI el correo va a Mailpit. Q-24: la cantidad real de proxies de confianza delante de la API, `TRUSTED_PROXY_HOPS`, depende del host elegido; con el valor por defecto `0` el origen es la conexión directa y, detrás del proxy de un host, todos los clientes comparten un origen y el límite por origen se vuelve casi global, lo que se corrige al elegir el host (C-20). Q-23: SMTP saliente o API HTTPS de correo permitida desde el host elegido; Render gratuito bloquea 25, 465 y 587, y la contraseña de aplicación de Gmail no existe con Protección Avanzada ni con cuentas de trabajo. Los tests no dependen del proveedor, pero sin Q-23 no hay verificación de correo real en producción: si resulta necesaria una API HTTPS, se agrega como segundo adaptador del mismo puerto (alcance acotado, registrado en C-20). Tensión de la KB: el Flujo 1 de `07` dice que el barrido envía la verificación; este change la intenta enviar de inmediato por el mismo caso de uso para no sumar hasta 5 minutos de espera (decisión de diseño a validar).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 1 (US-001 a US-005)
  - `knowledge-base/13_aviso_de_privacidad_borrador.md` (texto y versión del aviso que sirve la API)
  - `knowledge-base/05_reglas_de_negocio.md` §Cuentas (RN-01 a RN-05), §Pacientes (RN-47 a RN-49, RN-62), RN-59 y RN-61
  - `knowledge-base/07_flujos_principales.md` Flujos 1 y 2
  - `knowledge-base/12_devops_y_despliegue.md` §Configuración de correo (SMTP)
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad; `knowledge-base/10_preguntas_abiertas.md` Q-23

---

## FASE 2 — Agenda y turnos (núcleo de la rebanada vertical)

> C-06 corre en paralelo con C-04 y C-05. C-08 corre en paralelo con C-07. C-09, C-10 y C-15 se abren juntos al completar C-07.

### [C-06] `agenda-config`
- **Estado**: `[ ]` pendiente
- **Scope**: Configuración de la agenda por el Administrador
  - Migración: `box`, `profesional` (`UNIQUE (box_id)`, `UNIQUE (usuario_id)`), `horario_semanal` (`CHECK hora_inicio < hora_fin`), `bloqueo_agenda` (`profesional_id` nulo = todos), `prestacion` (`CHECK duracion_min > 0`)
  - `GET/POST /api/v1/usuarios`, `PATCH /api/v1/usuarios/{id}` — el Administrador crea y desactiva personal con un único rol; el alta con rol `paciente` se rechaza con 422 (el paciente se autorregistra, RN-01, y toda cuenta de paciente guarda la aceptación del aviso de privacidad, RN-65); un profesional de la agenda se vincula a una cuenta de rol `profesional` o `administrador` (DD-24, US-006)
  - `GET/POST /api/v1/boxes`, `GET/POST /api/v1/profesionales`, `PATCH /api/v1/profesionales/{id}` — un box fijo por profesional; desactivar conserva el historial
  - `GET/PUT /api/v1/profesionales/{id}/horario-semanal` — varios bloques por día, rechaza bloques superpuestos del mismo día
  - `GET/POST /api/v1/profesionales/{id}/bloqueos`, `DELETE /api/v1/bloqueos/{id}` — feriado, vacaciones, ausencia, bloqueo
  - `GET/POST /api/v1/prestaciones`, `PATCH /api/v1/prestaciones/{id}` — semilla del catálogo inicial de 9 prestaciones con duraciones sugeridas; cambiar una duración no altera turnos creados (RN-15)
  - `GET/PATCH /api/v1/consultorio` — `modo_liberacion`, plazos en horas y teléfono del consultorio, y los parámetros de reserva de RN-64 (`minutos_granularidad`, `dias_anticipacion_maxima`, `max_turnos_activos_paciente`), que la API valida con los mismos límites que los `CHECK` de la base
  - Tests primero: crear un usuario con rol `paciente` responde 422 y no crea nada; bloques superpuestos rechazados; segundo profesional con el mismo box rechazado; un profesional se vincula a una cuenta de rol `profesional` o `administrador` y se rechaza con cualquier otro rol (DD-24); solo el Administrador escribe (403 para otros roles); desactivar no borra; el catálogo semilla se carga una sola vez; el `consultorio_id` de cada recurso sale del `Principal`
- **Dependencias**: C-03
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: Q-09 (duraciones sugeridas a confirmar por los profesionales), Q-13 (carga de feriados), Q-12 (quién bloquea por urgencia); no frenan la implementación.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épicas 2 (US-006) y 3 (US-008 a US-012)
  - `knowledge-base/04_modelo_de_datos.md` §box, §profesional, §horario_semanal, §bloqueo_agenda, §prestacion, §Catálogo inicial de prestaciones
  - `knowledge-base/05_reglas_de_negocio.md` §Agenda y disponibilidad (RN-10 a RN-16)
  - `knowledge-base/02_descripcion_general.md` §API REST

---

### [C-07] `turnos-core`
- **Estado**: `[ ]` pendiente
- **Scope**: Turnos sin solapamiento, máquina de estados e historial
  - Migración: `turno` (con `ciclo_confirmacion`, columnas de hitos y `marcado_sin_confirmar_en`), `turno_historial` (solo inserta). La misma migración agrega las claves foráneas hacia `turno` que quedaron pendientes: `token_usuario.turno_id` (C-02) y `notificacion.turno_id` (C-05); si C-05 todavía no se aplicó cuando se escribe esta migración, la clave de `notificacion` la agrega la migración de C-05, que entonces ya encuentra la tabla `turno` (regla dura 8: un único head, se rebasa). La restricción `turno_sin_solapamiento` (`EXCLUDE USING gist` sobre `consultorio_id`, `profesional_id`, `tstzrange(inicio, fin, '[)')`, con `where` que excluye sobreturnos y estados `cancelado`/`liberado`) se declara en el modelo con `ExcludeConstraint` y se **crea a mano en la migración** (`CREATE EXTENSION IF NOT EXISTS btree_gist` primero, luego la restricción con `op.create_exclude_constraint` u `op.execute`): el autogenerate de Alembic no la detecta
  - Casos de uso: crear turno por Recepción/Administrador (valida horario, bloqueos y duración de la prestación, o la duración que el personal fije para ese turno en múltiplos de `minutos_granularidad`; el inicio debe caer en la grilla del bloque, RN-64; sin los límites de anticipación ni de cantidad del paciente; nace `pendiente` o `confirmado`, RN-23, y siempre `confirmado` si faltan menos de `horas_confirmacion` para el inicio, RN-29; rechaza con 409 un turno regular que se superponga con un sobreturno activo del mismo profesional: la restricción de exclusión no mira sobreturnos, así que lo controla el caso de uso, y una carrera simultánea es un riesgo residual documentado), reprogramar atómico (una sola escritura sobre la misma fila, que la restricción de exclusión valida contra el horario nuevo; no se crea un segundo turno, RN-37; conserva la duración actual del turno, así que una duración ajustada no se recalcula con la de la prestación salvo que el personal fije otra, el inicio nuevo cae en la grilla y tampoco puede superponerse con un sobreturno activo, RN-64; vuelve a `pendiente`, o queda `confirmado` si el horario nuevo está a menos de `horas_confirmacion` (RN-29), incrementa el ciclo y limpia `marcado_sin_confirmar_en`: la marca "sin confirmar" pertenece al ciclo anterior, RN-32 y RN-37), cancelar con motivo, confirmar, liberar manual, `atendido`, `ausente` y corrección `ausente` a `atendido`
  - Cada transición escribe en `turno_historial` (actor, estados, fecha); todas pasan por `acceso.autorizar` de C-04
  - Violación de la restricción de exclusión (SQLSTATE `23P01`, leído de la excepción del driver) traducida en el adaptador del repositorio a un error de dominio "horario ocupado" y en la API a 409; el dominio no conoce el código SQL
  - `GET/POST /api/v1/turnos`, `GET /api/v1/turnos/{id}`, `PATCH /api/v1/turnos/{id}`, `POST /api/v1/turnos/{id}/{confirmar|cancelar|liberar|atendido|ausente}`, `GET /api/v1/turnos/{id}/historial`, `GET /api/v1/agenda?profesional_id=&fecha=` (el Profesional solo ve su agenda)
  - Lecturas de pacientes derivadas de turnos: `GET /api/v1/pacientes/{id}/turnos` (US-038) y adaptador del puerto de C-08 que acota la búsqueda del Profesional a pacientes de su agenda (RN-50)
  - RN-16: crear un bloqueo sobre un período con turnos devuelve la lista de turnos afectados y exige resolverlos de forma explícita (extiende el endpoint de C-06)
  - Tests primero (integración contra PostgreSQL real): **dos turnos solapados del mismo profesional insertados en la base son rechazados por la restricción y el error trae `23P01`** (este test valida la expresión `tstzrange` con `&&`, que la documentación de SQLAlchemy no ejemplifica, y confirma SU-39); turnos contiguos (`fin` = `inicio` del siguiente) sí se aceptan; otro profesional y otro consultorio no chocan; `cancelado`/`liberado` no ocupan el hueco; dos reservas concurrentes del mismo hueco, solo una prospera; Recepción crea un turno fuera de la grilla (inicio a las 9:07 en un bloque que empieza a las 9:00) y recibe 422; Recepción crea un turno a más de 60 días y un tercer turno activo para el mismo paciente y ambos se aceptan (los límites de anticipación y de cantidad no rigen para el personal, RN-64); una duración ajustada en múltiplo de 15 minutos se acepta y una de 20 se rechaza (422); reprogramar un turno de 45 minutos con duración ajustada conserva sus 45 minutos; crear o reprogramar un turno regular encima de un sobreturno activo (fila preparada con una fixture, porque `POST /api/v1/sobreturnos` es de C-10) responde 409; reprogramación fallida deja el original intacto; reprogramar un turno con la marca "sin confirmar" (puesta por una fixture, porque el barrido es de C-16) la limpia (`marcado_sin_confirmar_en` nulo en `GET /api/v1/turnos/{id}`) e incrementa el ciclo (que el turno salga de la lista "sin confirmar" se prueba en C-16, que construye esa lista); Recepción da un turno a una ficha sin cuenta (`usuario_id` nulo), que la prueba prepara con una fixture de la base porque `POST /api/v1/pacientes` es de C-08: el turno nace `pendiente` (con el reloj simulado a más de 48 h del inicio; a 47 h 59 min nace `confirmado` y a 48 h exactas nace `pendiente`, RN-29; reprogramar un turno `pendiente` a un horario a menos de 48 h lo deja `confirmado`, y el historial registra que fue por la regla) y `GET /api/v1/turnos/{id}` y `GET /api/v1/pacientes/{id}/turnos` lo devuelven con esa ficha; `atendido` inmutable; `ausente` antes de la hora de inicio rechazado; el Profesional no marca turnos ajenos (404: turno de otra agenda, regla de códigos de `11`)
- **Dependencias**: C-04, C-06
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto que bloquee este change. Q-26 (`btree_gist` en el PostgreSQL del entorno publicado) afecta solo al despliegue y se resuelve antes de C-20, no antes de este change: en local y en CI PostgreSQL corre como superusuario y la restricción se prueba contra la base real; si el proveedor publicado no permitiera la extensión, la regla central de no solapamiento no se garantizaría en la base. SU-39 (el código `23P01` se confirma con el propio test). Q-04 y Q-20 se leen en C-10.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §turno, §turno_historial, §Mapa de cumplimiento de reglas
  - `knowledge-base/05_reglas_de_negocio.md` §Turnos y solapamientos (RN-17 a RN-24), §Cancelación y reprogramación, §Ausentismo (RN-44)
  - `knowledge-base/06_funcionalidades.md` Épicas 5 y 6
  - `knowledge-base/07_flujos_principales.md` Flujos 6 y 8, §Ciclo de vida del turno
  - `knowledge-base/08_arquitectura_propuesta.md` §Persistencia y migraciones; `knowledge-base/09_decisiones_y_supuestos.md` DD-08, DD-14, SU-39; `knowledge-base/11_politicas_de_acceso_abac.md` §Matriz de decisión

---

### [C-08] `patient-records`
- **Estado**: `[ ]` pendiente
- **Scope**: Fichas de paciente gestionadas por Recepción
  - `GET /api/v1/pacientes` — búsqueda por apellido, DNI o teléfono, paginada; `POST /api/v1/pacientes` — ficha mínima (nombre, apellido, teléfono, correo, DNI obligatorios; obra social y notas opcionales; el formulario de la ficha muestra junto a las notas la leyenda que pide no cargar datos de salud, RN-65, que arma C-13); DNI duplicado responde 409
  - `GET/PATCH /api/v1/pacientes/{id}`; sin borrado físico (RN-58). El detalle (`GET`) incluye, solo para Recepción y Administrador, un bloque `cuenta` con el identificador del usuario, su nombre de usuario, su correo y si está verificado, o nulo si la ficha no tiene cuenta, para que puedan actuar sobre el vínculo (RN-63): el Profesional y el Paciente no lo reciben y no se devuelve otro dato de la cuenta (minimización, RN-58). `PATCH` no modifica `activo`: la v1 no tiene ninguna acción que desactive una ficha (SU-47)
  - Solicitudes de vinculación (RN-49, RN-62; la tabla la crea C-05): `GET /api/v1/solicitudes-vinculacion?estado=` (DNI declarado, correo de la cuenta y si está verificado, ficha existente con ese DNI y, en las solicitudes `vinculada`, la ficha vinculada (identificador, nombre y apellido); sin el filtro de estado lista también las resueltas, para detectar intentos sospechosos como varias cuentas sobre el mismo DNI), `POST /api/v1/solicitudes-vinculacion/{id}/vincular` con la ficha elegida (`paciente_id`): en una transacción bloquea primero la fila de la ficha elegida (`SELECT ... FOR UPDATE` sobre `paciente`, filtrado por `consultorio_id`, para que dos vínculos simultáneos sobre la misma ficha no se interbloqueen) y hace después dos escrituras condicionales, en este orden: primero el pase de la solicitud a `vinculada` con quién y cuándo (`UPDATE solicitud_vinculacion ... WHERE id = :id AND estado = :estado_leido AND estado IN ('pendiente', 'rechazada')`: una ya `vinculada` no afecta ninguna fila), y después `UPDATE paciente SET usuario_id = :usuario WHERE id = :paciente AND consultorio_id = :consultorio AND activo = true AND usuario_id IS NULL`; si cualquiera de las dos no afecta ninguna fila responde 409, revierte todo y no cambia nada, tampoco el estado de la solicitud, y toda violación de unicidad sobre `paciente.usuario_id` dentro de la transacción también se traduce a 409 con reversión completa, igual que un interbloqueo o un fallo de serialización que informe el motor (`40P01`, `40001`), sin dejar un error de integridad sin traducir; si la ficha elegida no existe en el consultorio, 404 sin cambiar nada; 409 también, sin cambiar nada, si el correo de la cuenta no está verificado; el DNI declarado es solo informativo, así que un DNI de la ficha cambiado después de la solicitud no genera conflicto, y `POST /api/v1/solicitudes-vinculacion/{id}/rechazar` (motivo opcional; si el correo de la cuenta está verificado, en la misma transacción programa el correo `vinculacion_rechazada`, que le pide al paciente comunicarse con el consultorio sin el motivo ni el DNI, y lo despacha de inmediato con el caso de uso `DespacharNotificacion` que construye C-05, el mismo camino del correo de verificación, con el barrido de C-15 como reintento (este change no depende de C-15); con el correo sin verificar no programa ninguno; 409 si la solicitud ya no está `pendiente`); solo Recepción y Administrador (`paciente.vincular`); una ficha ya vinculada no se vincula a otra cuenta (US-039). Este change es dueño de la plantilla `vinculacion_rechazada`, que sigue la misma regla de contenido que las demás (solo lo necesario, sin datos de salud, y aquí además sin motivo ni DNI, RN-54). Tras un rechazo, Recepción vincula la cuenta con la ficha correcta o crea una ficha nueva con `POST /api/v1/pacientes` y la vincula; el paciente no reintenta por su cuenta y no hay un formulario nuevo
  - `POST /api/v1/pacientes/{id}/desvincular` (motivo obligatorio, `extra='forbid'`; `paciente.desvincular`, solo Recepción y Administrador; RN-63, DD-20): en una transacción pone `paciente.usuario_id` en nulo con `UPDATE ... WHERE id = :id AND consultorio_id = :consultorio AND usuario_id = :usuario_leido` (409 sin cambiar nada si no afecta ninguna fila: la ficha no tiene cuenta o ya la cambió otra operación), deja la solicitud de esa cuenta en `rechazada` con el motivo, quién, cuándo y la ficha de origen en `paciente_id` (`INSERT ... ON CONFLICT (usuario_id) DO UPDATE ... WHERE estado = 'vinculada'`; si la cuenta se registró con un DNI nuevo y no tenía solicitud, se crea ya `rechazada` con `dni_declarado` igual al DNI de la ficha) y revoca todos los refresh tokens de la cuenta con el caso de uso del restablecimiento de contraseña de C-05; no programa ningún correo; la ficha conserva sus datos y sus turnos. La cuenta queda sin ficha, no reserva (lo aplica C-09) y se vincula de nuevo con `vincular`. Límite conocido: el token de acceso ya emitido sigue válido hasta vencer (JD-12 de la auditoría, sin corregir), pero no da acceso a la ficha: el token nunca lleva la ficha y la capa de aplicación carga el vínculo vigente en cada solicitud (RN-06, RN-63)
  - `POST /api/v1/pacientes/{id}/reactivar` (`paciente.reactivar`, solo Recepción y Administrador): `UPDATE paciente SET activo = true WHERE id = :id AND consultorio_id = :consultorio AND activo = false`; si no afecta ninguna fila, una consulta de existencia filtrada por `consultorio_id` decide la respuesta: 404 si la ficha no existe en el consultorio y 409 si existe y ya estaba activa; sin motivo (SU-44). Desvincular aplica la misma regla: 404 para una ficha que no existe en el consultorio y 409 para una que existe y no tiene cuenta, igual que vincular. La v1 no tiene ninguna acción que desactive una ficha: `activo` existe para fichas cargadas o corregidas fuera de la aplicación y reactivar sirve para recuperarlas (SU-47)
  - ABAC: Recepción y Administrador ven todos los pacientes del consultorio; el Paciente solo su ficha; el Profesional se acota mediante un puerto cuyo adaptador entrega C-07
  - Tests primero: DNI único por consultorio; búsqueda por cada criterio; Paciente no accede a la ficha de otro (404); doble vinculación rechazada (409); vincular a una ficha inactiva o con una cuenta con el correo sin verificar se rechaza (409) sin cambiar la solicitud; dos vínculos simultáneos de cuentas distintas sobre la misma ficha, contra PostgreSQL real: uno prospera, el otro recibe 409 y su solicitud sigue `pendiente`, y la ficha termina con una sola cuenta; vincular con un `paciente_id` que no existe en el consultorio responde 404 y la solicitud sigue como estaba; un error `40P01` o `40001` provocado en la transacción responde 409 con reversión completa; dos resoluciones simultáneas de la misma solicitud (rechazar y vincular, o vincular con dos fichas distintas) dejan una sola y la otra recibe 409 sin cambiar nada, y en el segundo caso la cuenta termina con una sola ficha y la respuesta perdedora es 409, no un error de integridad; vincular una solicitud ya `vinculada` responde 409 desde el primer paso, sin tocar ninguna ficha; una solicitud `pendiente` cuya cuenta ya tiene otra ficha (estado que la operación normal no produce, preparado con una fixture de la base) recibe 409 con reversión completa y no un error de integridad sin traducir; una solicitud pendiente aparece en la lista y deja de aparecer al resolverse, y sigue consultable sin filtro de estado; vincular deja la cuenta como titular de la ficha y registra quién y cuándo; vincular con una ficha cuyo DNI cambió después de la solicitud funciona; rechazar una cuenta con el correo verificado la deja sin ficha, programa un solo correo `vinculacion_rechazada` y lo despacha de inmediato con un doble del puerto, con una plantilla sin el motivo ni el DNI (rechazar de nuevo responde 409 y no lo repite); rechazar una cuenta con el correo sin verificar no programa ningún correo; una solicitud `rechazada` se vincula después con la ficha correcta o con una ficha nueva creada para esa cuenta, que queda como titular (que entonces la cuenta reserva se prueba en C-09); Profesional y Paciente reciben 403 en las solicitudes, en desvincular y en reactivar; desvincular exige motivo (sin motivo, 422), deja `paciente.usuario_id` nulo sin cambiar otras columnas de la ficha, deja la solicitud de la cuenta `rechazada` con el motivo, el actor, la fecha y la ficha de origen, no programa ningún correo y revoca los refresh tokens de la cuenta (`POST /api/v1/auth/refresh` con su token ya no renueva); desvincular una cuenta que se registró con un DNI nuevo crea su solicitud `rechazada`; desvincular una ficha sin cuenta responde 409; dos desvinculaciones simultáneas de la misma ficha dejan una sola (la otra, 409), y una desvinculación y un vínculo simultáneos sobre la misma ficha dejan una sola cuenta; la cuenta desvinculada se vincula de nuevo y la lista sin filtro de estado muestra su solicitud; reactivar deja la ficha `activo = true` y permite vincularla, reactivar una ficha activa responde 409 y dos reactivaciones simultáneas dejan una sola (la otra, 409); desvincular o reactivar una ficha inexistente o de otro consultorio responde 404; los cuatro casos de un vínculo equivocado o bloqueado (RN-63) se recorren de punta a punta con las acciones de este change y el registro de C-05: vínculo hecho por error, ficha correcta ocupada por otra cuenta, ficha correcta inactiva y ficha tomada por un tercero que se registró primero con un DNI nuevo; la ficha creada con `POST /api/v1/pacientes` se recupera con `GET /api/v1/pacientes/{id}` y es elegible al vincular (que sirva para dar un turno se prueba en C-07, contra la base y con una ficha de fixture sin cuenta, y en C-13, que depende de C-07 y de este change, como prueba de interfaz con la API simulada); el detalle de la ficha devuelve a Recepción y Administrador el bloque `cuenta` (identificador, nombre de usuario, correo y si está verificado) tras vincular y nulo tras desvincular o si nunca tuvo cuenta, el Profesional y el Paciente no reciben ese bloque, y la lista de solicitudes devuelve la ficha vinculada en las `vinculada` y no en las `pendiente`; ni el detalle ni la lista devuelven otro dato de la cuenta (por ejemplo, el hash de la contraseña); `PATCH` con `activo` en el cuerpo se rechaza (422, `extra='forbid'`); un token de acceso emitido antes de desvincular la cuenta ya no lee la ficha (`GET /api/v1/pacientes/{id}` responde 404 con ese mismo token), porque el token no lleva la ficha y el vínculo se lee en cada solicitud (la misma comprobación sobre los turnos de la ficha se hace en C-09, que construye `GET /api/v1/turnos`, porque este change no depende de C-07)
- **Dependencias**: C-04, C-05
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-10 (reserva para otra persona; no frena la implementación). Q-05 quedó resuelta el 2026-10-11 (DD-19, RN-62): la tabla `solicitud_vinculacion` la crea C-05 y este change agrega su resolución por Recepción, incluida la salida de una solicitud rechazada, y la desvinculación y la reactivación (DD-20, RN-63); las decisiones no dictadas por el dueño (ficha inactiva, correo sin verificar, ficha elegida por Recepción, detalles de desvincular y reactivar) figuran en SU-42 y SU-44.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 8 (US-036 a US-039, US-041 y US-042)
  - `knowledge-base/05_reglas_de_negocio.md` §Pacientes (RN-47 a RN-51, RN-62, RN-63), RN-06, RN-54, RN-58
  - `knowledge-base/04_modelo_de_datos.md` §paciente, §solicitud_vinculacion, §notificacion ("Vigencia por tipo")
  - `knowledge-base/11_politicas_de_acceso_abac.md` §Matriz de decisión (acciones de paciente)

---

### [C-09] `availability-public-booking`
- **Estado**: `[ ]` pendiente
- **Scope**: Disponibilidad pública y autogestión del turno por el paciente
  - Servicio de dominio puro `disponibilidad`: horario semanal − excepciones − turnos activos (los sobreturnos activos cuentan como ocupado), duración de la prestación elegida, horarios de inicio cada `minutos_granularidad` desde el inicio de cada bloque (RN-64) y zona horaria del consultorio; no ofrece horarios más allá de `dias_anticipacion_maxima`; un turno nunca se parte entre bloques (RN-14)
  - `GET /api/v1/publico/consultorio`, `/publico/prestaciones`, `/publico/profesionales`, `/publico/disponibilidad` — sin ingreso, sin datos de otros pacientes, con límite de solicitudes (adaptador en memoria por proceso para estas lecturas; Redis opcional); el consultorio lo resuelve `consultorio_sin_token` (C-03), nunca el cliente (RN-59)
  - Paciente verificado: `POST /api/v1/turnos` con origen `online` (solo para su propia ficha, nace `pendiente`, o `confirmado` si faltan menos de `horas_confirmacion` para el inicio, RN-29; una cuenta sin ficha, con la solicitud de vinculación `pendiente` o `rechazada` (también la de una cuenta desvinculada, RN-63), recibe 403 con el mensaje de que debe comunicarse con el consultorio para verificar su cuenta, sin mencionar el DNI ni el estado de la solicitud, RN-62), `GET /api/v1/turnos` (solo los propios, con acciones según estado y plazo; la ficha vigente de la cuenta se carga en cada solicitud y se pasa a `es_titular_del_turno`, porque el token no la trae, RN-06), confirmar desde la cuenta
  - Cancelar y reprogramar propios hasta 24 h antes (`horas_limite_paciente`); pasado el plazo la respuesta incluye el teléfono del consultorio; al reprogramar, el horario nuevo cae en la grilla y dentro de `dias_anticipacion_maxima` (422) y el turno conserva su duración actual, incluida una ajustada por el personal (RN-64); reprogramar no agrega un turno y no cuenta contra `max_turnos_activos_paciente`
  - Límites de la reserva en línea (RN-64): un horario fuera de la grilla o más allá de `dias_anticipacion_maxima` se rechaza con 422, y superar `max_turnos_activos_paciente` se rechaza con 409 indicando el máximo; el paciente no envía duración. El máximo es atómico: la reserva bloquea la fila del paciente (`SELECT ... FOR UPDATE` filtrado por `consultorio_id`) antes de contar sus turnos activos e insertar, en la misma transacción. Un turno regular que se superponga con un sobreturno activo del mismo profesional se rechaza con 409 (lo controla el caso de uso porque la restricción de exclusión no mira sobreturnos; una carrera simultánea es un riesgo residual documentado)
  - Conflicto de reserva responde 409 con horarios alternativos cercanos (RN-24)
  - Puerto `ProgramadorHitos` (implementación nula; la real llega en C-16) invocado al reservar y reprogramar. No confundir con el puerto `Planificador` del barrido (C-15), que solo oculta el disparador
  - Tests primero: disponibilidad con horario, bloqueo, turno existente y duraciones distintas; los inicios salen cada 15 minutos desde el inicio del bloque y cambian al cambiar `minutos_granularidad`; no hay horarios después del día 60 y sí en el día 60; el tercer turno activo de un paciente se rechaza con 409 y vuelve a aceptarse cuando uno se cancela; una reserva en línea con duración en el cuerpo se rechaza con 422; dos reservas simultáneas del mismo paciente cuando solo le queda un cupo: una prospera y la otra recibe 409 con el máximo, y el paciente termina con `max_turnos_activos_paciente` turnos activos (bloqueo de la fila del paciente); reprogramar fuera de la grilla o a más de 60 días responde 422 y el turno queda como estaba; reprogramar un turno con duración ajustada por el personal conserva esa duración; un horario cubierto por un sobreturno activo (fixture) no se ofrece en la disponibilidad y reservarlo por pedido directo responde 409; reserva sin verificar rechazada; el paciente no ve ni opera turnos ajenos; cancelación a 24 h exactas y a 23 h 59 min con reloj simulado; reprogramar a un horario ocupado mantiene el original; una cuenta con ficha vinculada reserva `online` para sí y el turno nace `pendiente`, o `confirmado` si reserva con menos de 48 h de anticipación (con un DNI nuevo, la cuenta recibe su ficha en el registro de C-05 y reserva sin solicitud); una cuenta sin ficha (solicitud `pendiente` o `rechazada`, incluida la que deja una desvinculación) no reserva (403, mensaje sin DNI ni estado) y sí reserva una vez vinculada; un token de acceso emitido antes de que la cuenta fuera desvinculada (vínculo cambiado con una fixture, sin renovar el token) ya no opera los turnos de esa ficha (404 por identificador) y su lista `GET /api/v1/turnos` responde 200 vacía, igual que la de cualquier cuenta sin ficha vinculada; los estados de cuenta, ficha y solicitud de estos casos se preparan con fixtures de la base, porque este change no depende de la resolución por Recepción de C-08
- **Dependencias**: C-05, C-07
- **Governance**: ALTO
- **Riesgos / bloqueado por**: ninguno abierto. Q-06 y Q-11 quedaron resueltas por DD-27 (RN-64).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 4 (US-013 a US-018)
  - `knowledge-base/05_reglas_de_negocio.md` RN-11 a RN-14, RN-17, RN-24, RN-33, RN-35, RN-37
  - `knowledge-base/07_flujos_principales.md` Flujos 3 y 6
  - `knowledge-base/05_reglas_de_negocio.md` RN-64 y `knowledge-base/09_decisiones_y_supuestos.md` DD-27 (reglas de reserva)
  - `knowledge-base/11_politicas_de_acceso_abac.md` A4 (ventana temporal)

---

### [C-10] `overbooking-authorization`
- **Estado**: `[ ]` pendiente
- **Scope**: Sobreturnos con autorización registrada
  - Migración `autorizacion_sobreturno` (`UNIQUE (turno_id)`, respuesta del profesional `sin_respuesta`/`aprobado`/`rechazado`)
  - `POST /api/v1/sobreturnos` — solo Recepción o Administrador; recibe los datos del turno, el motivo y la autorización explícita, y crea en una transacción el turno con `es_sobreturno = true` y su `autorizacion_sobreturno` (DD-30); si el horario no se superpone con ningún turno activo del profesional responde 422 e indica crear un turno normal; `es_sobreturno = true` queda fuera de la restricción de exclusión; respeta horario semanal y bloqueos (RN-43); los pacientes nunca lo generan
  - Registro de autorizante, fecha, motivo y `profesional_notificado_en`; aviso al profesional visible en su agenda
  - `POST /api/v1/sobreturnos/{id}/respuesta-profesional` — el Profesional afectado, o el Administrador cuando la agenda afectada es la suya (DD-24), aprueba o rechaza (solo en su agenda; `{id}` es el del turno); la respuesta se registra y no bloquea el otorgamiento: no hay veto (RN-40, DD-30)
  - Sobreturnos marcados en `GET /agenda` y en las vistas del turno
  - Tests primero: sobreturno sin autorización o sin motivo rechazado; un pedido de sobreturno sobre un horario libre responde 422 y no crea nada; si falla la escritura de la autorización no queda ningún turno `es_sobreturno` (reversión completa); un rechazo del profesional no cambia el estado del turno; fuera de horario o sobre bloqueo rechazado; el paciente recibe 403; el profesional no responde un aviso ajeno; el administrador con agenda propia responde el aviso de su agenda y no el de otro profesional, y el administrador sin agenda recibe 403 (DD-24); el sobreturno no bloquea ni es bloqueado por la restricción de exclusión (se inserta uno encima de un turno regular en PostgreSQL real)
- **Dependencias**: C-07
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: Q-20 (máximo de sobreturnos simultáneos y sobreturno fuera del horario; prioridad Baja, no frena: la v1 no pone máximo y respeta el horario, RN-43). Q-04 quedó resuelta por DD-30.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-024 y US-029
  - `knowledge-base/05_reglas_de_negocio.md` §Sobreturnos (RN-39 a RN-43)
  - `knowledge-base/07_flujos_principales.md` Flujo 7
  - `knowledge-base/04_modelo_de_datos.md` §autorizacion_sobreturno
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-30 y `knowledge-base/10_preguntas_abiertas.md` Q-20

---

## FASE 3 — Frontend de la rebanada vertical

> Agente C trabaja en estas pantallas mientras los agentes A y B avanzan en el backend. El flujo completo de reserva y gestión funciona de punta a punta al terminar C-14 y C-13.

### [C-11] `frontend-shell-auth`
- **Estado**: `[ ]` pendiente
- **Scope**: Esqueleto del frontend y pantallas de cuenta
  - `src/app` con enrutado, proveedores y guardas por rol; layouts por rol (paciente, recepción, profesional, administrador); las rutas de los enlaces de correo (`/verificar-email`, confirmación de turno) las resuelve el router de la SPA
  - `src/services`: cliente HTTP con `VITE_API_BASE_URL` (variable de compilación pública, relativa: `/api/v1`; en desarrollo `vite.config.ts` reenvía `/api` a la API con `server.proxy`, hacia el destino de `VITE_DEV_PROXY_TARGET` (variable solo de desarrollo, no entra en el build: `http://api:8000` dentro de Compose y `http://localhost:8000` fuera de Compose), y en producción la API sirve el build, DD-26), token de acceso en memoria y renovación por cookie `HttpOnly` con `credentials: 'include'`, manejo de 401/403/404; reintento acotado con aviso en las lecturas cuando la API está dormida y responde lento o con error de arranque
  - Diseño atómico base (`atoms`, `molecules`, `organisms`, `templates`) y patrón contenedor/presentacional
  - `features/auth`: registro (con el aviso de privacidad que devuelve la API en `GET /api/v1/publico/aviso-privacidad`, sin copiar el texto en el frontend, y su casilla de aceptación sin marcar; el botón de envío queda deshabilitado hasta marcarla y el registro envía la versión que se mostró, RN-65), verificación de correo, reenvío, ingreso, recuperación y restablecimiento de contraseña, cuenta del usuario
  - Tests primero (Vitest + Testing Library): componentes presentacionales con props; contenedores con la API simulada; el aviso y su versión salen de la respuesta de la API simulada y el registro reenvía esa versión; la guarda de rol redirige; el token no se persiste en `localStorage`; una API que tarda o falla en el arranque muestra el aviso y reintenta sin romper la pantalla
- **Dependencias**: C-05
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: ninguno abierto. Q-28 quedó resuelta por DD-26: la renovación se prueba en local contra la API real a través del proxy de Vite.
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend), §Patrones aplicados, §Seguridad
  - `knowledge-base/12_devops_y_despliegue.md` §Cookie de renovación y origen
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas, §Rutas privadas por rol
  - `knowledge-base/06_funcionalidades.md` Épica 1
  - `knowledge-base/07_flujos_principales.md` Flujos 1 y 2

---

### [C-12] `frontend-admin-config`
- **Estado**: `[ ]` pendiente
- **Scope**: Pantallas de configuración del Administrador
  - `features/configuracion`: usuarios del personal, profesionales con su box, editor de horario semanal por bloques, excepciones y bloqueos (muestra la lista de turnos afectados y exige resolverlos), catálogo de prestaciones, parámetros del consultorio (modo de liberación, plazos, teléfono, y los de reserva de RN-64: granularidad, anticipación máxima y turnos activos por paciente)
  - Páginas bajo guarda de rol `administrador`; formularios con validación y errores de campo del backend
  - Tests primero: el editor de horario rechaza bloques superpuestos antes de enviar; el bloqueo con turnos afectados no se confirma sin resolverlos; un rol no administrador no ve las rutas
- **Dependencias**: C-06, C-07, C-11
- **Governance**: BAJO
- **Riesgos / bloqueado por**: ninguno abierto. Candidato a simplificación si el plazo aprieta (ver [Si el plazo aprieta](#si-el-plazo-aprieta)).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 3 y US-006
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend)
  - `knowledge-base/03_actores_y_roles.md` §Rutas privadas por rol

---

### [C-13] `frontend-staff-agenda`
- **Estado**: `[ ]` pendiente
- **Scope**: Agenda y gestión de turnos para Recepción y Profesional
  - `features/agenda`: vista diaria por profesional con estado de cada turno y sobreturnos marcados; el Profesional ve solo la propia; el administrador con agenda propia tiene un filtro "mi agenda" (DD-24)
  - `features/turnos`: dar turno (buscar o crear ficha en el momento), mover, cancelar con motivo, confirmar por el paciente, marcar atendido y ausente
  - `features/pacientes`: búsqueda, ficha (con la cuenta vinculada, o su ausencia, para Recepción y Administrador), historial de turnos, lista de solicitudes de vinculación (pendientes y resueltas, con la ficha vinculada en las `vinculada`) y su resolución (vincular con la ficha elegida, también si ya fue rechazada, o rechazar, C-08), desvincular una cuenta de su ficha con un motivo obligatorio y reactivar una ficha inactiva (C-08)
  - Autorizar sobreturno con motivo y aviso/respuesta del profesional
  - Tests primero: el 409 de horario ocupado se muestra con alternativas; las acciones no permitidas por estado no se renderizan; el Profesional no ve acciones de creación; dar turno con una ficha creada en el momento (crea la ficha y da el turno, con la API simulada); desvincular no se envía sin motivo y un 409 de vincular, desvincular o reactivar se muestra sin romper la pantalla; las acciones de desvincular y reactivar no se muestran al Profesional; la ficha muestra la cuenta vinculada (o que no tiene) a Recepción y Administrador y no muestra ese bloque al Profesional
- **Dependencias**: C-07, C-08, C-10, C-11
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: ninguno abierto.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épicas 5, 6 y 8
  - `knowledge-base/07_flujos_principales.md` Flujos 6, 7 y 8
  - `knowledge-base/11_politicas_de_acceso_abac.md` §Matriz de decisión
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend)

---

### [C-14] `frontend-public-booking`
- **Estado**: `[ ]` pendiente
- **Scope**: Enlace público de reserva y autogestión del paciente
  - `features/reserva`: elegir prestación y profesional, ver disponibilidad sin ingresar, reservar (exige cuenta verificada: lleva a registro o ingreso)
  - Mis turnos: estado, fecha, profesional y prestación; confirmar, cancelar y reprogramar; pasadas las 24 h se muestra el teléfono del consultorio en lugar de la acción
  - Pantalla de horario ocupado con alternativas; página de turno liberado que ofrece reservar de nuevo
  - Con DD-26 la pantalla duerme junto con la API (la API sirve el frontend): el enlace tarda en cargar mientras el host despierta el servicio; una vez que la pantalla carga y la API todavía no responde, muestra la pantalla de espera "el servicio está iniciando" con reintento antes de mostrar un error
  - Diseño responsive (el paciente usa el celular)
  - Tests primero: las acciones se ocultan fuera de ventana; el flujo registro, verificación y reserva con la API simulada; los errores 409 y 403 se muestran sin romper la pantalla; una API lenta muestra la espera y luego los datos
- **Dependencias**: C-09, C-11
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: ninguno abierto que bloquee este change. Q-24 (cuánto tarda en despertar el host elegido; afina el tiempo de espera de la pantalla) afecta solo al despliegue publicado y se resuelve antes de C-20: este change usa un tiempo de espera configurable y lo prueba con una API simulada.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 4
  - `knowledge-base/07_flujos_principales.md` Flujos 3, 4 y 6
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas, §Frontend
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend)
  - `knowledge-base/12_devops_y_despliegue.md` §Arquitectura de despliegue base

---

## FASE 4 — Confirmación, recordatorios y liberación automática

### [C-15] `notifications-outbox-sweep`
- **Estado**: `[ ]` pendiente
- **Scope**: Barrido idempotente en la API, endpoint disparador y bandeja de notificaciones (reemplaza al worker; antes `notifications-outbox-worker`)
  - Puerto `Planificador` con dos adaptadores sobre el **mismo caso de uso** `EjecutarBarrido`: disparo externo (el endpoint de abajo) y bucle `asyncio` propio (`SWEEP_IN_PROCESS_ENABLED`, intervalo `SWEEPER_INTERVAL_SECONDS`, arrancado en el `lifespan` de FastAPI; para local o VM)
  - `POST /internal/barrido` fuera de `/api/v1`, excluido del OpenAPI público, autenticado con `SWEEP_SHARED_SECRET` comparado en tiempo constante; sin secreto configurado o con uno incorrecto no ejecuta nada; responde con el resumen del barrido (conteos de filas reclamadas, enviadas, reintentadas, omitidas y fallidas)
  - Concurrencia por reclamación por fila, sin candado global ni candados de sesión (DD-17, RN-61): `SELECT ... FOR UPDATE SKIP LOCKED` sobre las filas candidatas, estado intermedio `enviando` con `reclamada_en` y transacción corta confirmada antes de enviar; el envío ocurre fuera de toda transacción y una segunda transacción corta registra el resultado, condicionada a que la fila siga `enviando` con la `reclamada_en` que fijó ese envío (si no afecta ninguna fila, el envío perdió la reclamación y descarta su resultado sin escribir); una reclamación vencida (`NOTIFICATION_CLAIM_TTL_SECONDS`) se revisa en un barrido posterior con la misma validación de vigencia por tipo que la primera reclamación (tabla "Vigencia por tipo" de `04`: la solicitud de confirmación y el recordatorio valen solo con el turno en el estado y el ciclo para los que se programaron y sin comenzar, si no `omitida`; los avisos de liberación, cancelación o reprogramación por el personal, el resumen de la reserva y la confirmación de la cancelación del paciente (que programa C-16) y los correos de cuenta no dependen del turno activo; `vinculacion_rechazada` ya la valida C-05), respetando `NOTIFICATION_MAX_ATTEMPTS` (al alcanzarlo, `fallida` sin reenviar) y el tope diario: solo reenvía si no se alcanzó, y pasar a `omitida` o a `fallida` no se frena por el tope. Toda salida de `enviando` deja `reclamada_en` nulo. La entrega es al menos una vez: una caída entre el envío y el resultado, o un envío más lento que el plazo, puede repetir un correo. Dos barridos simultáneos pueden ejecutarse a la vez y nunca reclaman la misma fila. Transiciones cortas y condicionales por fila. Sin Redis
  - Despacho de notificaciones de correo `programada` vencidas con el caso de uso `DespacharNotificacion` de C-05, reintentos acotados (`NOTIFICATION_MAX_ATTEMPTS`) y estado final `fallida`; un fallo no cambia el estado del turno (RN-31); el tope diario de correos y el cupo de los correos de cuenta (DD-29) se verifican antes de toda reclamación que enviaría un correo (con el tope alcanzado no se reclaman más correos, las filas siguen `programada` sin consumir intentos y una `enviando` vencida no se reclama de nuevo; el conteo suma las `enviando` no vencidas, C-05)
  - Limpieza periódica como tarea del barrido: tokens vencidos de `token_usuario` y `refresh_token`, y los renglones de `intento_registro` e `intento_ingreso` de más de 24 horas (ejecuta los casos de uso `PurgarIntentosRegistro` de C-05, DD-21, y `PurgarIntentosIngreso` de C-03, DD-25, que ya corren al escribir cada intento)
  - Migración: columna `ciclo` y `UNIQUE (turno_id, tipo, canal, ciclo)` en `notificacion` (los correos de cuenta con `turno_id` nulo no se deduplican por esta clave: PostgreSQL trata los nulos como distintos); los correos de cuenta de C-05 siguen el mismo despacho
  - Aviso al paciente cuando el personal cancela o reprograma su turno (US-034), disparado desde los casos de uso de C-07: tipos `cancelacion_por_personal` y `reprogramacion_por_personal`, que se programan en la misma transacción del cambio, no se omiten por él (comunican algo ya ocurrido) y llevan el `ciclo` vigente al programar (el de la reprogramación, el nuevo)
  - `GET /api/v1/notificaciones?estado=fallida` para Recepción y Administrador
  - Indicadores operativos mínimos: cantidad de `fallida`, antigüedad de la `programada` más vieja, cantidad de filas en `enviando` y antigüedad de la más vieja, estado del último barrido y envíos del día frente al tope de 500 con alerta al 80 % (almacenamiento de la marca del último barrido a decidir en el diseño)
  - Plantillas de correo con solo nombre, fecha, hora, profesional, consultorio y acción (RN-54)
  - Tests primero (reloj simulado, PostgreSQL real): doble barrido no duplica envíos; **dos barridos simultáneos nunca procesan la misma fila** (ambos pueden correr a la vez y cada fila se reclama una sola vez); una reclamación `enviando` vencida se retoma y una vigente no; el resultado de un envío lento que perdió la reclamación no pisa el del barrido que la retomó (la escritura condicionada por `reclamada_en` no afecta ninguna fila); la revisión de una reclamación vencida de una `solicitud_confirmacion` o un `recordatorio` cuyo turno ya no corresponde (cancelado, liberado, de otro ciclo o ya comenzado; la solicitud también si está `confirmado`) la pasa a `omitida` sin enviar, y con los intentos agotados a `fallida` sin reenviar; un aviso de `liberacion`, de `cancelacion_por_personal` o de `reprogramacion_por_personal` de un turno ya `liberado`, `cancelado` o reprogramado se envía y no se omite por la vigencia, y lo mismo un `resumen_reserva` y una `cancelacion_por_paciente` (filas preparadas con una fixture, porque las programa C-16); toda salida de `enviando` deja `reclamada_en` nulo; con el tope diario alcanzado, una `enviando` vencida que enviaría de nuevo no se reclama y queda como estaba, mientras que una vencida que pasaría a `omitida` o a `fallida` se resuelve igual y no cuenta en el conteo del tope; el barrido borra los renglones de `intento_registro` e `intento_ingreso` de más de 24 horas y conserva los recientes; una caída simulada entre el envío y el resultado se reenvía (entrega al menos una vez); con el tope diario alcanzado el barrido no reclama más correos y las filas siguen `programada` sin consumir intentos; los indicadores informan la cantidad de filas `enviando` y la antigüedad de la más vieja; un barrido tras 3 horas de servicio dormido procesa lo vencido sin duplicar; SMTP simulado que falla reintenta N veces y deja `fallida`; el sistema completo funciona sin `REDIS_URL`; `POST /internal/barrido` sin secreto o con secreto incorrecto responde 401/403 y no despacha; el endpoint no aparece en el OpenAPI; la plantilla no contiene datos de salud; el bucle propio ejecuta el mismo caso de uso que el endpoint
- **Dependencias**: C-05, C-07
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-25 (quién opera el disparador externo y rota el secreto; local y tests no dependen de él, producción sí). Q-27 (100 CU-h mensuales de Neon frente a un barrido cada 5 minutos con suspensión a los 5: puede mantener el cómputo casi siempre activo; si no alcanza, subir el intervalo y aceptar menor precisión de los hitos). Q-24 (con la API dormida el barrido no corre hasta que el disparador la despierta; SU-38 sin verificar; solo al publicar, se resuelve antes de C-20). Q-23 (el despacho real depende del correo saliente; se resuelve antes de que este change envíe correo real). No se usan candados de sesión: pueden no ser fiables detrás de un pooler de transacciones de Neon (no verificado); `SKIP LOCKED` por fila funciona dentro de transacciones cortas.
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Trabajos en segundo plano, §Seguridad (endpoint interno)
  - `knowledge-base/04_modelo_de_datos.md` §notificacion
  - `knowledge-base/05_reglas_de_negocio.md` RN-31, RN-54
  - `knowledge-base/12_devops_y_despliegue.md` §Trabajos programados en el despliegue, §Consecuencias y riesgos de la arquitectura base, §Configuración de correo (SMTP)
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-13, DD-17, SU-01, SU-26, SU-38
  - `knowledge-base/06_funcionalidades.md` US-034 y US-035

---

### [C-16] `milestones-confirmation-release`
- **Estado**: `[ ]` pendiente
- **Scope**: Hitos de 48/24/12 horas, confirmación por enlace y liberación automática o manual (procesados por el barrido de C-15)
  - Implementación real de `ProgramadorHitos`: al reservar o reprogramar calcula los hitos desde `inicio` y programa las notificaciones en `notificacion`; reprogramar incrementa `ciclo_confirmacion`, pasa a `omitida` las notificaciones `programada` o `preparada`, de cualquier canal, de solicitud de confirmación y de recordatorio del ciclo anterior (la regla no distingue canal; las `preparada` de WhatsApp las crea C-17, que prueba esa parte; no el aviso de reprogramación por el personal, que se programa con el ciclo nuevo, ver "Vigencia por tipo" en `04`) y limpia `marcado_sin_confirmar_en` (RN-32). Cancelar o liberar un turno omite del mismo modo las de su ciclo vigente (flujo 6 y "Vigencia por tipo" en `04`)
  - Barrido T-48 h: solicitud de confirmación por correo a turnos `pendiente`, con enlace de un solo uso (`token_usuario` tipo `confirmar_turno`, que guarda el `ciclo_confirmacion` del turno al emitirse; la migración agrega la columna `ciclo` a `token_usuario`)
  - Barrido T-24 h: recordatorio a `pendiente` y `confirmado`; para `pendiente` advierte la liberación solo si ese turno puede liberarse de forma automática según RN-60 (modo automático, solicitud de confirmación del ciclo actual `enviada`, sin marca y sin comenzar); en otro caso solo pide confirmar, sin advertencia
  - Barrido T-12 h: los candidatos son los turnos `pendiente`, sin marca, en su ciclo actual, a 12 horas o menos del inicio y que todavía no comenzaron (`inicio > :ahora`, con el reloj inyectado); un `pendiente` que ya comenzó queda fuera de la selección y no se reevalúa en cada barrido (el personal lo cierra como `atendido` o `ausente`, RN-44). El modo automático pasa `pendiente` a `liberado` con `UPDATE ... WHERE id = :id AND estado = 'pendiente' AND marcado_sin_confirmar_en IS NULL AND ciclo_confirmacion = :ciclo AND inicio > :ahora` y avisa al paciente solo si la `solicitud_confirmacion` por correo de su ciclo actual está `enviada` y el turno todavía no comenzó (RN-60, DD-18); si ese envío falló, fue omitido o sigue `programada` o `enviando`, fija `marcado_sin_confirmar_en` sin liberar (otra actualización condicional con la misma guarda), igual que el modo manual; un turno cuyo inicio ya pasó nunca se libera de forma automática ni recibe la marca (RN-27, RN-28): ni la selección ni ninguna de las dos actualizaciones lo incluyen. La fila de `turno_historial` (`liberar` o `marcar_sin_confirmar`) y el aviso se escriben en la misma transacción solo si la actualización afectó una fila. Un turno ya marcado en su ciclo no se vuelve a evaluar aunque su solicitud se envíe después: decide Recepción
  - RN-29 (DD-32): un turno creado o reprogramado con menos de `horas_confirmacion` ya nació `confirmado` (lo asigna C-07); este change no le programa la solicitud de confirmación, le programa el recordatorio solo si no venció y el barrido no lo selecciona para liberar ni para marcar
  - Los hitos tienen una precisión de la frecuencia del disparador (5 minutos) y toleran un retraso del barrido: nunca se pierden (están en PostgreSQL) y, salvo una caída entre el envío y su registro (entrega al menos una vez, RN-61), no se duplican
  - `POST /api/v1/turnos/confirmar-por-enlace` con token (ruta sin sesión, fuera de `/publico/*`; el consultorio sale de la fila de `token_usuario` a la que apunta el token, RN-59) — solo confirma; turno ya `liberado` se rechaza y ofrece reservar de nuevo; un token cuyo `ciclo` no coincide con el `ciclo_confirmacion` del turno se rechaza igual que uno vencido
  - `GET /api/v1/turnos?sin_confirmar=true` para Recepción (lista de los `pendiente` con `marcado_sin_confirmar_en`); confirmar, cancelar y liberar reutilizan los casos de uso de C-07
  - Dos correos más de hechos ya ocurridos, programados en la misma transacción del hecho, desde los casos de uso de reservar y de cancelar (C-07, C-09), y despachados con el caso de uso de C-05: el resumen del turno al reservar (US-014, flujo 3; `tipo` `resumen_reserva`) y la confirmación de la cancelación hecha por el paciente (flujo 6; `tipo` `cancelacion_por_paciente`). Los dos son siempre vigentes (tabla "Vigencia por tipo" de `04`): no se omiten porque el turno cambie después, y llevan el `ciclo` vigente al programar
  - Tests primero (reloj simulado, tablas de tiempo): solicitud a 48 h exactas y no antes; idempotencia ante barridos repetidos y simultáneos; reserva con 10 h de anticipación; modo manual no libera; dos barridos simultáneos sobre el mismo turno producen una sola fila de historial (`liberar` o `marcar_sin_confirmar`) y un solo aviso; un turno marcado cuya solicitud se envía después no se libera; reprogramar un turno marcado limpia la marca, lo saca de la lista "sin confirmar" (`GET /api/v1/turnos?sin_confirmar=true`) y lo evalúa de nuevo en su ciclo nuevo; la lista "sin confirmar" muestra los turnos `pendiente` marcados y no los confirmados, cancelados ni liberados; un turno `pendiente` cuyo inicio ya pasó no recibe la marca, no se libera aunque la solicitud esté `enviada` y no es candidato en barridos sucesivos (no se reevalúa ni se escribe historial); el recordatorio de un `pendiente` advierte la liberación solo si el turno puede liberarse de forma automática (modo automático, solicitud `enviada`, sin marca) y en otro caso solo pide confirmar; el enlace de confirmación toma el consultorio de la fila del token (un `consultorio_id` enviado por el cliente se rechaza con 422 por ser un campo no declarado, regla dura 11); el modo automático libera solo con la solicitud del ciclo actual `enviada`: con la solicitud `fallida`, `omitida`, `programada` o `enviando` el turno queda con la marca y no se libera, y una solicitud `enviada` de un ciclo anterior no cuenta; enlace usado o vencido rechazado; un enlace emitido antes de una reprogramación se rechaza y no confirma el horario nuevo (su ciclo no coincide con el del turno); reprogramar reinicia el ciclo y omite solo la solicitud de confirmación y el recordatorio del ciclo anterior que estén `programada` (o `preparada`, en cualquier canal; la parte de WhatsApp se prueba en C-17), no el aviso de reprogramación; cancelar o liberar un turno omite las suyas del ciclo vigente; reservar programa un `resumen_reserva` y cancelar el paciente una `cancelacion_por_paciente`, que se envían aunque el turno quede después cancelado o reprogramado; un `confirmado` nunca se libera; un barrido tardío (reloj adelantado tras un corte del disparador) procesa lo vencido una sola vez
- **Dependencias**: C-09, C-15
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-07 (enlace de un solo uso sin contraseña; prioridad Media, no frena: rige RN-30). Q-03 quedó resuelta por DD-32. SU-38 y Q-25 (en el entorno publicado la liberación a las 12 h depende de que el disparador externo sea puntual; en local el barrido corre con su bucle propio y no depende de él). Si el barrido se retrasa más allá de un hito siguiente, los hitos vencidos se omiten y rige la guarda de RN-60. Con la guarda de RN-60, un correo fallido o un disparador caído dejan más turnos "sin confirmar" para Recepción en lugar de liberarlos solos, y un barrido que llega después del inicio del turno no lo libera.
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Confirmación, recordatorio y liberación (RN-25 a RN-32, RN-60), RN-59 (consultorio en la confirmación por enlace) y la línea de tiempo del turno
  - `knowledge-base/07_flujos_principales.md` Flujos 4 y 5
  - `knowledge-base/04_modelo_de_datos.md` §turno (hitos), §token_usuario, §notificacion
  - `knowledge-base/06_funcionalidades.md` US-016, US-025, US-030 a US-032
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-32 y `knowledge-base/10_preguntas_abiertas.md` Q-07

---

### [C-17] `whatsapp-one-click`
- **Estado**: `[ ]` pendiente
- **Scope**: WhatsApp semimanual preparado por el sistema y enviado por Recepción
  - Value object `Telefono` con normalización internacional (código de país de Argentina por defecto, RN-53)
  - Constructor de mensaje sin datos de salud (RN-54) y enlace `wa.me` con teléfono y texto prellenados
  - Los hitos T-48 h y T-24 h de C-16 y los avisos por cambios del personal (US-034) crean además, en el mismo barrido, una notificación canal `whatsapp` en estado `preparada`. Reprogramar, cancelar o liberar el turno pasa a `omitida` las `preparada` de solicitud de confirmación y de recordatorio con la misma regla que C-16 aplica a las `programada` (RN-32, "Vigencia por tipo" en `04`): la lista de Recepción no conserva un mensaje con la fecha vieja
  - `GET /api/v1/notificaciones?canal=whatsapp&estado=preparada`, `GET /api/v1/notificaciones/{id}/whatsapp`, `POST /api/v1/notificaciones/{id}/marcar-enviada` (estado `enviada_manual` y quién la marcó)
  - Sin API oficial de WhatsApp Business (backlog)
  - Tests primero: normalización con prefijos locales y formatos variados; el mensaje no incluye prestación detallada ni datos de salud; marcar enviada registra al usuario; solo Recepción y Administrador acceden; un turno cancelado no deja mensajes `preparada` activos; reprogramar un turno con mensajes `preparada` de solicitud de confirmación y de recordatorio los pasa a `omitida` y los saca de `GET /api/v1/notificaciones?canal=whatsapp&estado=preparada`, y el mensaje `preparada` del aviso de reprogramación por el personal no se omite; un barrido repetido no duplica el mensaje preparado
- **Dependencias**: C-16
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: ninguno abierto. Candidato de recorte (CU-2 se cumple en parte): ver [Si el plazo aprieta](#si-el-plazo-aprieta).
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` RN-52, RN-53, RN-54
  - `knowledge-base/06_funcionalidades.md` US-033 y US-034
  - `knowledge-base/07_flujos_principales.md` Flujo 9
  - `knowledge-base/04_modelo_de_datos.md` §notificacion
  - `knowledge-base/02_descripcion_general.md` §Integraciones externas

---

### [C-18] `frontend-notifications-ops`
- **Estado**: `[ ]` pendiente
- **Scope**: Pantallas operativas de Recepción y estado operativo del barrido
  - `features/notificaciones`: lista de WhatsApp pendientes (el clic abre `wa.me` en otra pestaña y permite marcar enviada) y lista de envíos de correo fallidos
  - Lista de turnos "sin confirmar" con acciones confirmar, cancelar y liberar
  - Insignias de estado y contadores en el layout de Recepción
  - Panel de estado operativo para el Administrador con los indicadores de C-15: último barrido, antigüedad de la notificación `programada` más vieja, filas en `enviando` y antigüedad de la más vieja, `fallida` y envíos del día frente al tope de 500 (alerta visible al 80 %)
  - Tests primero: marcar enviada actualiza la lista; el enlace usa el `wa.me` entregado por la API; acciones de la lista respetan los permisos; vista vacía y de error; la alerta del tope aparece al 80 % y no antes; un último barrido viejo se muestra como advertencia; una fila `enviando` vieja se muestra con su antigüedad
- **Dependencias**: C-13, C-15, C-16, C-17
- **Governance**: BAJO
- **Riesgos / bloqueado por**: ninguno abierto. Si se recorta C-17, esta lista pierde la parte de WhatsApp y sus dependencias pasan a C-13, C-15, C-16 (ver [Si el plazo aprieta](#si-el-plazo-aprieta)).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-025, US-033, US-035
  - `knowledge-base/07_flujos_principales.md` Flujos 5 y 9
  - `knowledge-base/12_devops_y_despliegue.md` §Trabajos programados en el despliegue (indicadores operativos)
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend)

---

## FASE 5 — Indicador de ausentismo

### [C-19] `absenteeism-indicator`
- **Estado**: `[ ]` pendiente
- **Scope**: Indicador de ausentismo del Administrador (backend y pantalla)
  - `GET /api/v1/indicadores/ausentismo?desde=&hasta=&profesional_id=` — cantidad de `ausente`, tasa `ausentes / (atendidos + ausentes)` sobre turnos cuya hora ya llegó (RN-45), por período y por profesional, más cantidad de `liberado` y `cancelado`
  - Solo el Administrador (`puede_ver_ausentismo`); Administrativo con permiso reservado y sin acceso
  - `features/indicadores`: tabla y resumen por período y por profesional
  - Tests primero: fórmula con datos conocidos; período sin atendidos ni ausentes devuelve tasa nula y no divide por cero; `liberado` y `cancelado` no se cuentan como ausentes; Recepción y Profesional reciben 403; filtro por profesional y por consultorio
- **Dependencias**: C-11, C-16
- **Governance**: BAJO
- **Riesgos / bloqueado por**: Q-15 (fórmula y períodos a validar con el Administrador). Primer candidato de simplificación (solo endpoint) o de recorte si el plazo aprieta.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-040
  - `knowledge-base/05_reglas_de_negocio.md` §Ausentismo (RN-44 a RN-46)
  - `knowledge-base/07_flujos_principales.md` Flujo 10
  - `knowledge-base/10_preguntas_abiertas.md` Q-15 (fórmula y períodos a validar con el Administrador)
  - `knowledge-base/11_politicas_de_acceso_abac.md` §Matriz de decisión (indicadores)

---

## FASE 6 — Puesta en producción

### [C-20] `deploy-hardening`
- **Estado**: `[ ]` pendiente
- **Scope**: Despliegue en servicios gratuitos, endurecimiento y prueba de punta a punta
  - Topología de producción (DD-13): un solo servicio web gratuito con la API, que sirve también el frontend compilado (DD-26: la imagen de producción incluye el build de Vite con `VITE_API_BASE_URL=/api/v1` y la aplicación lo monta con `app.frontend()` o, si la versión fijada de FastAPI no lo trae, con `StaticFiles` y una ruta de respaldo; contenedor del `Dockerfile` del backend, host por decidir, Q-24), PostgreSQL en **Neon** (`DATABASE_URL` con `postgresql+asyncpg`, `btree_gist` verificado), sin proceso persistente aparte y sin Redis obligatorio
  - Migraciones (`alembic upgrade head`, un único head) y semilla idempotente como paso de despliegue; HTTPS, `FRONTEND_BASE_URL` del dominio público y `CORS_ORIGINS` vacío (DD-26); `OPENAPI_DOCS_ENABLED=false` (`/docs` y `/openapi.json` deshabilitados); secretos (`JWT_SECRET_KEY`, `SWEEP_SHARED_SECRET`, `ORIGIN_HASH_SECRET`, `SMTP_PASSWORD`, `DATABASE_URL`) solo en el almacén de secretos del host; `TRUSTED_PROXY_HOPS` con la cantidad real de proxies del host (Q-24), comprobando que un `X-Forwarded-For` enviado por el cliente no cambia el origen del límite de registros ni el del bloqueo de ingreso, y que dos clientes distintos tienen orígenes distintos (con `TRUSTED_PROXY_HOPS=0` detrás del proxy del host todos comparten un origen: el bloqueo de ingreso pasa a ser por cuenta y el límite por origen, global)
  - Disparador externo cada 5 minutos a `POST /internal/barrido` con `SWEEP_SHARED_SECRET` (por ejemplo `schedule` de GitHub Actions o cron trigger de Cloudflare Workers; quién lo opera y cómo se rota el secreto, Q-25); comprobar que el último barrido es reciente y medir su puntualidad (SU-38)
  - Correo real desde el host: SMTP con `aiosmtplib` (587 con STARTTLS) o, si el host bloquea los puertos, un segundo adaptador de `EnviadorCorreo` sobre una API HTTPS de correo (Q-23); contador diario con tope de 500 y alerta al 80 % verificado
  - Cookie de renovación probada en el servicio publicado, con `SameSite=Strict` y un solo origen (DD-26); una ruta del frontend recargada en el navegador devuelve la aplicación y una ruta inexistente bajo `/api` devuelve 404 en JSON
  - Docker Compose solo para local/dev y como alternativa en una VM si se exige el stack completo (Q-29; con el mismo servicio único que sirve el frontend compilado, sin un servidor web aparte): sin clave `version`, healthchecks, `restart: unless-stopped`, `mailpit` en perfil `dev`, Redis en perfil `redis`
  - `pg_dump` programado fuera de la base y restauración probada (los respaldos contienen datos personales: acceso restringido, no se versionan, RN-58)
  - Prueba E2E de la rebanada completa contra el stack local de Compose con reloj simulado: registro, verificación, reserva, solicitud a 48 h, recordatorio a 24 h, liberación a 12 h, indicador, y el camino de la solicitud de vinculación (registro con un DNI ya cargado, 403 al reservar, vinculación o desvinculación por Recepción y reserva); más una prueba de humo contra el despliegue real (sin reloj simulado)
  - Recorrer la lista de verificación previa a publicar el enlace público (`12`); confirmar con el consultorio nombre, domicilio, teléfono y duraciones de prestaciones, y ejecutar la prueba de producción del aviso de privacidad (`APP_ENV=production`, sin marcadores entre corchetes) contra el consultorio sembrado
  - Tests primero / verificaciones: humo del arranque con `docker compose up`; `POST /internal/barrido` sin secreto responde 401/403 y con secreto 200; `/docs` responde 404 en producción; `alembic heads` devuelve uno solo; el despliegue deja un barrido reciente
- **Dependencias**: C-14, C-18, C-19
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-23 (correo saliente), Q-24 (host de la API; la API se duerme por inactividad), Q-25 (operador del disparador), Q-26 (`btree_gist` en el proveedor), Q-27 (horas de cómputo de Neon frente al intervalo del barrido), y Q-29 (si se exige el stack completo, este change se resuelve con Compose en una VM: la alternativa está documentada en `12`). Todas siguen abiertas: el spike de GATE 0 busca cerrarlas antes del último día; si no se cierran, este change es donde fallan.
- **Leer antes**:
  - `knowledge-base/12_devops_y_despliegue.md` (completo, §Lista de verificación previa a publicar el enlace público)
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad, §Variables de entorno, §Trabajos en segundo plano
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-10, DD-13, §Riesgos, SU-27, SU-37, SU-38
  - `knowledge-base/10_preguntas_abiertas.md` Q-02, Q-09, Q-18, Q-23 a Q-29

---

## Preguntas abiertas que afectan al plan

> Siguen abiertas en `knowledge-base/10_preguntas_abiertas.md`. Esta tabla solo indica dónde pegan; no las resuelve.

> **Puerta de las preguntas Alta** (hallazgo JD-08): un change no se propone mientras tenga abierta una pregunta de prioridad Alta que bloquea su propio alcance; primero decide el dueño del proyecto y la decisión se registra como `DD-NN`. "A fijar en el diseño" no es una salida válida para una pregunta Alta. Al 2026-10-12 ningún change que se construye en local tiene abierta una que bloquee su alcance: Q-03 quedó resuelta por DD-32. Las abiertas (Q-23 a Q-27 y Q-29) conciernen al entorno publicado y bloquean solo C-20; C-01, C-05, C-07, C-14, C-15 y C-16 las nombran como riesgo del despliegue y no las esperan, porque en local el correo va a Mailpit y el barrido corre con su bucle propio (DD-31).

| Pregunta | Tema | Changes afectados | Efecto si no se resuelve |
|----------|------|-------------------|--------------------------|
| Q-03 | Resuelta (DD-32): con menos de `horas_confirmacion` el turno nace `confirmado` | C-07, C-09, C-16 | — |
| Q-23 | Correo saliente o API HTTPS de correo permitida desde el host | C-20 (antes de enviar correo real) | Sin correo automático en producción (único canal automático); en local y CI el correo va a Mailpit y C-05 no espera la respuesta |
| Q-24 | Servicio web gratuito para la API | C-20 | Define suspensión, tiempo de arranque, puertos, secretos y `TRUSTED_PROXY_HOPS`; C-05, C-14 y C-15 solo lo mencionan como riesgo del despliegue |
| Q-25 | Quién opera el disparador externo y rota el secreto | C-20 | Sin disparador no hay recordatorios ni liberación; al volver procesa lo vencido sin duplicar |
| Q-26 | `btree_gist` en el PostgreSQL elegido | C-20 | No se garantiza el no solapamiento en la base publicada; en local y CI funciona (superusuario) y C-01 y C-07 no la esperan |
| Q-27 | 100 CU-h de Neon frente al intervalo del barrido | C-20 | Hay que subir el intervalo y los hitos pierden precisión |
| Q-28 | Resuelta (DD-26): frontend y API en el mismo origen | C-03, C-11, C-14, C-20 | — |
| Q-29 | Si se exige el stack completo | C-20 | Despliegue con Compose en una VM propia; C-01 no cambia |
| Q-01 | Resuelta (DD-22): entrega en dos partes, sin recorte | todos | — |

---

## BACKLOG (fuera de la v1)

> No generan changes ni entran en el plazo del 2026-10-19, salvo C-21, que ya está planificado para la segunda parte (DD-28). Orden de prioridad acordado en `knowledge-base/06_funcionalidades.md` Épica 10. Cuando se planifiquen, se agregan como changes nuevos (`C-21` en adelante) sin alterar los de la v1.

| Prioridad | ID | Funcionalidad diferida | Nota |
|-----------|----|------------------------|------|
| 1 | US-B01 | Auditoría y consentimiento de datos conforme a la Ley 25.326 | Planificada como **C-21 `data-subject-rights`** para la segunda parte de la entrega (DD-28): acceso y descarga de los datos propios, pedidos de rectificación y supresión con sus plazos, supresión compatible con la regla de no borrar fichas (anonimización), auditoría de accesos a fichas y plazo de conservación (Q-17). Depende de C-05 y C-08. Se detalla con `/opsx:propose` cuando empiece la segunda parte. La v1 ya incluye el aviso y la aceptación (RN-65). |
| 2 | US-B02 | Lista de espera con relleno automático de huecos por cancelación | |
| 3 | US-B03 | Seña o pago por Mercado Pago al reservar | Sin integración de pagos en la v1. |
| 4 | US-B04 | Recall automático de controles periódicos | |
| 5 | US-B05 | API oficial de WhatsApp Business con envío automático de confirmaciones | Reemplazaría el envío semimanual de C-17. |
| 6 | US-B06 | Facturación ARCA, cobro y liquidación con obras sociales, contratos y documentación | El rol Administrativo existe en la v1 solo con permisos reservados. |
| 7 | US-B07 | Odontograma, periodontograma, presupuestos y planes de tratamiento | |
| 8 | US-B08 | Importación desde planilla o Google Calendar | Diferida, sin fecha. |

---

## Tabla resumen

| ID | Change | Fase | Dependencias | Governance | Agente |
|----|--------|------|--------------|------------|--------|
| C-01 | foundation-setup | 0 | — | BAJO | A |
| C-02 | core-models | 0 | C-01 | CRITICO | A |
| C-03 | auth-core | 1 | C-02 | CRITICO | A |
| C-04 | abac-policies | 1 | C-03 | CRITICO | A |
| C-05 | patient-account | 1 | C-03 | CRITICO | B |
| C-06 | agenda-config | 2 | C-03 | MEDIO | C |
| C-07 | turnos-core | 2 | C-04, C-06 | CRITICO | A |
| C-08 | patient-records | 2 | C-04, C-05 | ALTO | B |
| C-09 | availability-public-booking | 2 | C-05, C-07 | ALTO | A |
| C-10 | overbooking-authorization | 2 | C-07 | MEDIO | A |
| C-11 | frontend-shell-auth | 3 | C-05 | MEDIO | C |
| C-12 | frontend-admin-config | 3 | C-06, C-07, C-11 | BAJO | C |
| C-13 | frontend-staff-agenda | 3 | C-07, C-08, C-10, C-11 | MEDIO | C |
| C-14 | frontend-public-booking | 3 | C-09, C-11 | MEDIO | C |
| C-15 | notifications-outbox-sweep | 4 | C-05, C-07 | ALTO | B |
| C-16 | milestones-confirmation-release | 4 | C-09, C-15 | ALTO | B |
| C-17 | whatsapp-one-click | 4 | C-16 | MEDIO | B |
| C-18 | frontend-notifications-ops | 4 | C-13, C-15, C-16, C-17 | BAJO | C |
| C-19 | absenteeism-indicator | 5 | C-11, C-16 | BAJO | A |
| C-20 | deploy-hardening | 6 | C-14, C-18, C-19 | ALTO | A |
| C-21 | data-subject-rights (planificado para la segunda parte, DD-28; se detalla con `/opsx:propose`) | 7 | C-05, C-08 | a definir | a definir |

**Primer change recomendado**: `C-01` (foundation-setup), con el spike de infraestructura en paralelo (Agentes B y C). Para arrancar: `/opsx:propose C-01-foundation-setup`
