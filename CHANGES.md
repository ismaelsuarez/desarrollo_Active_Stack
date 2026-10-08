# CHANGES — Secuencia de Implementación

> Índice canónico de todos los changes del proyecto **Sistema de Turnos y Agenda Odontológica** (v1, entrega **2026-10-12**).
> Cada change es atómico: un agente puede implementarlo en una sesión (~4-6 horas).
> **Leer este archivo antes de ejecutar cualquier `/opsx:propose`.**
> Regenerado el **2026-10-08** (quedan cuatro días) a partir de la KB actualizada el 2026-10-06 y alineada el 2026-10-08. Se conservan los IDs `C-01` a `C-20`, sus dependencias y el orden de la rebanada vertical; solo cambia lo que exige la arquitectura sin worker persistente (barrido en la API, DD-13), PyJWT/Argon2 (DD-12) y SQLAlchemy asíncrono con migraciones de un solo head (DD-14).

---

## Cómo usar este documento

1. Identificar el change a implementar (verificar que sus dependencias están en `openspec/changes/archive/`).
2. Leer los docs de la knowledge-base indicados en "Leer antes".
3. Ejecutar `/opsx:propose <nombre-del-change>`.
4. Al terminar el change, archivarlo con `/opsx:archive <nombre-del-change>`.
5. Marcar el checkbox `[x]` en este archivo.

Reglas del proyecto que aplican a **todos** los changes:

- **TDD estricto** en la fase apply: cada change se implementa test primero (RED, GREEN, TRIANGULATE, REFACTOR), con red de seguridad previa si modifica archivos existentes. Los tests describen comportamiento (reglas `RN-NN` y criterios de aceptación `US-NNN`), no implementación. Los bullets "Tests primero" de cada scope son el punto de partida de los casos RED. Lo que depende de PostgreSQL (exclusión de solapamientos, `UNIQUE`, candado del barrido) se prueba contra PostgreSQL real en contenedor, nunca con dobles.
- **`consultorio_id`** en toda tabla que pertenece a un consultorio, desde la primera migración. Los repositorios lo reciben del `Principal` (el token), nunca del cliente (RN-55). Hay un único consultorio activo en la v1.
- **Stack fijo**: Python, FastAPI, PyJWT (HS256) y pwdlib con Argon2, SQLAlchemy 2.x asíncrono (asyncpg, `expire_on_commit=False`), Alembic, PostgreSQL (Neon en producción), `aiosmtplib`; React, TypeScript, Vite (Cloudflare Pages en producción). Docker Compose es entorno local/dev y alternativa en una VM. Presupuesto cero.
- **Sin worker persistente y sin Redis obligatorio**: ningún change crea un proceso aparte ni exige Redis. Lo programado es un barrido idempotente dentro de la API (C-15), con candado en PostgreSQL, disparado por `POST /internal/barrido` o por un bucle `asyncio` local. Redis es opcional y solo auxiliar (límites de intentos); sin `REDIS_URL` todo funciona con PostgreSQL.
- **Migraciones en paralelo con un único head**: varios changes crean migraciones Alembic a la vez. Antes de archivar, cada change rebasa su migración sobre la única cabeza vigente (`alembic heads` debe devolver una sola; el CI lo exige) y se aplica con `alembic upgrade head`, nunca `heads`. El autogenerate de Alembic no detecta restricciones `EXCLUDE`: se revisa cada migración generada. Las migraciones se numeran en el orden en que se archivan los changes.
- **Preguntas abiertas como riesgo explícito**: Q-23 a Q-29 (proveedor de correo, host de la API, quién opera el disparador, `btree_gist`, cuota de Neon, cookie entre dominios, stack completo) figuran en el campo **Riesgos / bloqueado por** de cada change afectado y se resumen en [Preguntas abiertas que afectan al plan](#preguntas-abiertas-que-afectan-al-plan). Siguen abiertas: ningún change las resuelve por su cuenta.
- **Plazo**: el alcance completo de la v1 entra antes del 2026-10-12, con holgura cero en el camino crítico (ver [Si el plazo aprieta](#si-el-plazo-aprieta)). La decisión de recorte es del Product Owner (Q-01 en `knowledge-base/10_preguntas_abiertas.md`), no de este documento.
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
              │     └── C-08 patient-records
              │           └── C-13 frontend-staff-agenda   (+ C-07, C-10, C-11)
              │
              ├── C-05 patient-account
              │     └── C-11 frontend-shell-auth
              │
              └── C-06 agenda-config                (→ C-07, C-12)

C-14 + C-18 + C-19  ──►  C-20 deploy-hardening   (cierre de la v1)
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
| C-08 | C-04 |
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
  → C-08 patient-records                     [Agente B — si C-04 ✓]
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
> Nota sobre el spike: mientras A cierra C-01 a C-03, B y C no tienen changes desbloqueados. Ese tiempo se usa para un **spike de infraestructura** (no es un change y no genera código de producto): crear el proyecto en Neon y comprobar `CREATE EXTENSION btree_gist` (Q-26), elegir el host de la API y probar desde él una salida SMTP real o una API HTTPS de correo (Q-23, Q-24), publicar una página mínima en Cloudflare Pages y probar la cookie `HttpOnly` entre dominios (Q-28) y probar el disparador externo contra una ruta de ejemplo (Q-25). El resultado se registra en el diseño de C-20. Si no se hace, esas incógnitas aparecen recién el último día.

### Camino crítico (10 changes — mínimo irreducible)

```
C-01 → C-02 → C-03 → C-06* → C-07 → C-09 → C-16 → C-17 → C-18 → C-20
```

`*` C-04, C-05 y C-06 están a la misma profundidad (todos dependen solo de C-03) y se ejecutan en paralelo en GATE 3; los tres son prerrequisito de C-07/C-09 (C-04 y C-06 para C-07, C-05 para C-09). El primero de los tres en retrasarse pasa a ser el crítico. C-15 (barrido) corre en paralelo con C-09 y debe terminar antes de C-16: si C-15 se atrasa, pasa a ser el crítico.

Diez sesiones secuenciales de 4 a 6 horas no caben con holgura en cuatro días: el camino crítico no tiene margen. Palancas honestas, de menor a mayor costo funcional: ejecutar C-01 y C-02 en una misma sesión; y, solo si el Product Owner lo decide, sacar C-17 del camino (ver [Si el plazo aprieta](#si-el-plazo-aprieta)).

### Plan óptimo con 3 agentes

> Supuesto: dos sesiones por agente y por día (mañana y tarde), del 2026-10-08 al 2026-10-12. C-20 cae en la tarde del día de entrega: no hay holgura.

```
Paso │ Agente A (Backend Core)        │ Agente B (Backend Aux)             │ Agente C (Frontend / config)         │ Fecha objetivo
─────┼────────────────────────────────┼────────────────────────────────────┼──────────────────────────────────────┼───────────────
  1  │ C-01 foundation-setup          │ Spike: Neon, host, correo (Q-23/24/26) │ Spike: Pages, cookie, disparador (Q-25/28) │ 10-08 mañana
  2  │ C-02 core-models               │ Spike (cierre y registro)          │              —                       │ 10-08 tarde
  3  │ C-03 auth-core                 │              —                     │              —                       │ 10-09 mañana
  4  │ C-04 abac-policies             │ C-05 patient-account               │ C-06 agenda-config                   │ 10-09 tarde
  5  │ C-07 turnos-core               │ C-08 patient-records               │ C-11 frontend-shell-auth             │ 10-10 mañana
  6  │ C-09 availability-public-bkg   │ C-15 notifications-outbox-sweep    │ C-12 frontend-admin-config           │ 10-10 tarde
  7  │ C-10 overbooking-authorization │ C-16 milestones-confirm-release    │ C-14 frontend-public-booking         │ 10-11 mañana
  8  │ (holgura: adelantar C-20)      │ C-17 whatsapp-one-click            │ C-13 frontend-staff-agenda           │ 10-11 tarde
  9  │ C-19 absenteeism-indicator     │              —                     │ C-18 frontend-notifications-ops      │ 10-12 mañana
 10  │ C-20 deploy-hardening          │              —                     │ (apoyo en E2E y ajustes de UI)       │ 10-12 tarde
```

Los pasos 1 a 3 son una cadena lineal inevitable (cimientos, modelos, auth): el paralelismo real empieza en GATE 3. La rebanada vertical completa (auth y roles, horarios, agenda sin solapamientos, reserva pública y estados del turno) queda cerrada al terminar el paso 7. En el paso 8, el Agente A puede preparar la parte de C-20 que no depende de código nuevo (workflow del disparador, variables y secretos del host, comprobación del E2E local); no cambia la dependencia formal de C-20.

### Si el plazo aprieta

> Lista priorizada de qué simplificar o recortar **primero** sin romper la rebanada vertical (agenda, reserva pública, estados del turno), ordenada de menor a mayor pérdida funcional. **No es una decisión**: el orden de recorte lo fija el Product Owner (Q-01). Ninguna opción toca las reglas RN-01 a RN-58 ni agrega alcance.

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

## FASE 0 — Cimientos

### [C-01] `foundation-setup`
- **Estado**: `[ ]` pendiente
- **Scope**: Scaffolding del monorepo e infraestructura base (local/dev; sin worker)
  - Estructura: `backend/` en capas (`app/domain`, `app/application`, `app/infrastructure`, `app/api` con `internal/`, `app/core`), `frontend/` (Vite + React + TypeScript), `docker-compose.yml`, `.env.example`
  - `docker-compose.yml` **sin clave `version`**, con servicios `db` (PostgreSQL con volumen y healthcheck), `migrate` (`alembic upgrade head` y termina), `api` (healthcheck, `restart: unless-stopped`), `frontend`, `redis` (opcional, perfil `redis`) y `mailpit` (perfil `dev`); `depends_on` con `service_healthy` y `service_completed_successfully`; secretos montados en `/run/secrets/<nombre>` (la carpeta `secrets/` no se versiona). No hay servicio `worker`
  - Endpoint de salud de la API (`GET /api/v1/health`; el nombre se confirma al implementar, `12` lo cita como `/health`) usado por el healthcheck
  - `core/config.py`: lee las variables de `08` (y los archivos de `/run/secrets` cuando existen), falla al arrancar sin las obligatorias; `REDIS_URL` opcional; logging estructurado con identificador de solicitud, sin secretos
  - Alembic inicializado con `alembic init -t async` (`env.py` asíncrono, `compare_type=True`, `alembic/versions/`); migración base con `CREATE EXTENSION IF NOT EXISTS btree_gist`
  - pytest con PostgreSQL en contenedor para los tests de integración; Vitest + Testing Library en el frontend
  - CI gratuito: tests de backend y frontend, build de imágenes, `alembic upgrade head` sobre una base vacía y **verificación de un único head** (`alembic heads`) en cada cambio
  - Tests primero: `/health` responde 200; la configuración rechaza un arranque sin `DATABASE_URL`/`JWT_SECRET_KEY` y acepta los valores desde un archivo de secreto; el logger no emite valores de variables sensibles; el chequeo de heads falla con dos revisiones del mismo padre (fixture) y pasa con una; `docker compose config` valida y el archivo no contiene la clave `version`
- **Dependencias**: ninguna
- **Governance**: BAJO
- **Riesgos / bloqueado por**: Q-26 (la migración base falla si el proveedor de PostgreSQL no permite `btree_gist`; Neon figura como soportado, verificar en el spike). Q-29 (si se exige el stack completo con Redis y proceso persistente, el mismo Compose se despliega en una VM; no cambia este change).
- **Leer antes**:
  - `knowledge-base/01_vision_y_objetivos.md`
  - `knowledge-base/02_descripcion_general.md` §Stack tecnológico
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios, §Persistencia y migraciones, §Variables de entorno, §Estrategia de pruebas
  - `knowledge-base/12_devops_y_despliegue.md` §Servicios de Docker Compose, §Migraciones, respaldo y recuperación, §Integración continua

---

### [C-02] `core-models`
- **Estado**: `[ ]` pendiente
- **Scope**: Modelos base con `consultorio_id`, sesión asíncrona, unidad de trabajo y semilla inicial
  - Modelos SQLAlchemy 2.x tipados (`DeclarativeBase`, `Mapped[...]`, `mapped_column`) y migración de identidad: `consultorio` (parámetros `modo_liberacion`, `horas_confirmacion`/`recordatorio`/`liberacion`/`limite_paciente`), `usuario` (rol enum de cinco valores, `email_verificado`, `intentos_fallidos`, `bloqueado_hasta`), `token_usuario`, `refresh_token`, `paciente`
  - `consultorio_id` NOT NULL con índice en todas las tablas salvo `consultorio`; `UNIQUE (consultorio_id, nombre_usuario)`, `UNIQUE (consultorio_id, email)`, `UNIQUE (consultorio_id, dni)`, `UNIQUE (usuario_id)` en `paciente`
  - Acceso asíncrono: `create_async_engine("postgresql+asyncpg://...")`, `async_sessionmaker(engine, expire_on_commit=False)` y `engine.dispose()` al cerrar la aplicación
  - Base de infraestructura: mixin de timestamps, repositorio base que **siempre** filtra por el `consultorio_id` que recibe (el `Principal` lo entrega en C-03; nunca viene del cliente), `UnitOfWork`, puerto `Reloj` (reloj del sistema y reloj simulado)
  - Value object `Dni`; sin borrado físico (`activo`)
  - Semilla idempotente: consultorio inicial (48/24/12/24 h, modo automático, zona `America/Argentina/Buenos_Aires`) y administrador desde `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD` con correo verificado
  - Tests primero: un repositorio no devuelve filas de otro consultorio; las claves únicas rechazan duplicados dentro del consultorio y los admiten entre consultorios; la semilla corrida dos veces no duplica; el reloj simulado avanza de forma determinista; un objeto cargado sigue accesible tras el `commit` (`expire_on_commit=False`) sin recarga implícita; `alembic upgrade head` sobre base vacía deja un solo head
- **Dependencias**: C-01
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: ninguno abierto.
- **Leer antes**:
  - `knowledge-base/04_modelo_de_datos.md` §Principios, §consultorio, §usuario, §token_usuario, §refresh_token, §paciente, §Datos semilla
  - `knowledge-base/05_reglas_de_negocio.md` §Multiconsultorio y protección de datos (RN-55 a RN-58)
  - `knowledge-base/08_arquitectura_propuesta.md` §Patrones aplicados, §Capas del backend, §Persistencia y migraciones
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-14 y supuestos SU de modelado

---

## FASE 1 — Identidad y acceso

### [C-03] `auth-core`
- **Estado**: `[ ]` pendiente
- **Scope**: Autenticación JWT (PyJWT) y RBAC base
  - `POST /api/v1/auth/login` — JWT de acceso HS256 con PyJWT (`JWT_SECRET_KEY`, `JWT_ALGORITHM`) y claims `sub`, `consultorio_id`, `rol`, `jti` emitidos solo por el servidor; refresh con rotación
  - `POST /api/v1/auth/refresh` — rotación, el token reutilizado revoca la cadena; `POST /api/v1/auth/logout`; `GET /api/v1/auth/me`
  - Hash de contraseña **solo Argon2 con pwdlib** (sin elección de algoritmo; nunca en logs ni respuestas, RN-04); si el usuario no existe se verifica contra un hash ficticio para igualar tiempos; mensaje de error idéntico para usuario inexistente y contraseña incorrecta
  - Objeto `Principal` (usuario, `consultorio_id`, rol) construido desde el token validado; es la única fuente del `consultorio_id` para los repositorios
  - Bloqueo temporal por intentos fallidos (RN-09) con `intentos_fallidos`/`bloqueado_hasta` en PostgreSQL detrás de un puerto de límites; el adaptador Redis es opcional y no se construye salvo que se despliegue Redis; umbrales y TTL en configuración (`LOGIN_MAX_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`, `JWT_*_TTL`)
  - Token de renovación en cookie `HttpOnly`, `Secure` y `SameSite` configurables por entorno, con protección CSRF en el endpoint de renovación; el valor de `SameSite`/dominio queda a la espera de Q-28
  - Un paciente con correo sin verificar no ingresa (RN-02)
  - RBAC como **fábricas de dependencias** de FastAPI: `usuario_actual`, `requiere_rol(...)` con denegación por defecto (matriz de `03`)
  - Tests primero: login correcto e incorrecto; no distingue la causa; con usuario inexistente se ejecuta igualmente la verificación contra el hash ficticio; bloqueo tras N intentos y desbloqueo con reloj simulado; token expirado; token con otro algoritmo o sin firma rechazado; rotación y reutilización de refresh; rol sin permiso responde 403; los claims o el `consultorio_id` enviados por el cliente se ignoran
- **Dependencias**: C-02
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: Q-28 (cookie de renovación con frontend y API en dominios distintos: `SameSite=None; Secure` o dominio común, no verificado; si falla, la sesión del navegador no persiste y afecta C-11 y C-20). Q-16 (políticas de cuenta a fijar en el diseño).
- **Leer antes**:
  - `knowledge-base/03_actores_y_roles.md` §RBAC — Matriz de permisos
  - `knowledge-base/05_reglas_de_negocio.md` §Cuentas y autenticación (RN-01 a RN-09)
  - `knowledge-base/07_flujos_principales.md` Flujo 2
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-12 y SU-27; `knowledge-base/10_preguntas_abiertas.md` Q-16 y Q-28

---

### [C-04] `abac-policies`
- **Estado**: `[ ]` pendiente
- **Scope**: Los cuatro atributos ABAC como funciones de política puras en el dominio
  - Dominio puro (sin frameworks): entidad `Turno` mínima, `EstadoTurno`, tabla de transiciones de RN-18, `Intervalo`
  - `domain/policies`: `mismo_consultorio` (A2, siempre primero), `es_dueno_de_agenda` y `es_titular_del_turno` (A1), `turno_es_modificable` y `transicion_permitida` (A3), `dentro_de_ventana_paciente` y `hora_de_inicio_alcanzada` (A4), `puede_autorizar_sobreturno`, `puede_ver_paciente`, `puede_ver_ausentismo`
  - Punto de entrada `acceso.autorizar(usuario, accion, recurso, ahora)` invocado desde los casos de uso (RBAC ya se aplicó en el endpoint con C-03), con denegación por defecto; el instante `ahora` se inyecta
  - Traducción en la API: rechazo de política a 403 y recurso ajeno o de otro consultorio a 404; el rechazo se registra con usuario, acción y motivo, sin datos personales
  - Rol `administrativo` con permisos reservados y sin acceso funcional
  - Tests primero: tabla rol × acción × atributo con caso permitido y denegado por cada política; límites exactos de la ventana de 24 h (en el límite y a ±1 segundo); `atendido` inmutable ni para el administrador; `cancelado` y `liberado` finales; consultorio ajeno siempre denegado
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
  - `POST /api/v1/auth/registro` — crea `usuario` rol `paciente` y su ficha de `paciente`; si el DNI ya tiene ficha sin cuenta no la vincula (RN-49) e informa
  - `POST /api/v1/auth/verificar-email`, `POST /api/v1/auth/reenviar-verificacion`
  - `POST /api/v1/auth/recuperar-password` (respuesta idéntica exista o no el correo), `POST /api/v1/auth/restablecer-password` (revoca sesiones activas)
  - Cambio de contraseña con la actual y actualización de teléfono/correo del paciente; cambiar el correo exige verificarlo de nuevo (US-005)
  - `token_usuario`: aleatorio, guardado hasheado, un solo uso, con vencimiento (`EMAIL_VERIFICATION_TTL_HOURS`, `PASSWORD_RESET_TTL_MINUTES`)
  - Puerto `EnviadorCorreo` + adaptador SMTP con `EmailMessage` de la biblioteca estándar y `aiosmtplib` (587 con STARTTLS, `SMTP_*`; sin `fastapi-mail`) + plantillas de verificación y recuperación sin datos sensibles
  - Tabla `notificacion` (migración) donde se programa cada correo (`verificacion_email`, `recuperacion_password`) y caso de uso idempotente `DespacharNotificacion` que reclama la fila con una transición condicional (`UPDATE ... WHERE estado = 'programada'`); aquí se invoca como tarea en segundo plano de FastAPI justo después de programar, para que el correo de verificación no espere al próximo barrido de 5 minutos. C-15 reutiliza el mismo caso de uso para lo que quede `programada`
  - Tope diario de correos: contador de envíos del día (`EMAIL_DAILY_LIMIT`, 500 por defecto) y alerta al 80 % (`EMAIL_DAILY_ALERT_RATIO`) dentro del despacho
  - Límite de solicitudes sobre registro, recuperación y reenvío detrás de un puerto de límites: PostgreSQL por defecto (conteo de tokens y notificaciones recientes, sin tabla nueva si es posible), Redis solo si se despliega
  - Tests primero: token usado, vencido o inexistente rechazado; no enumeración de cuentas; DNI existente no vincula; sesiones revocadas al restablecer; el correo se prueba con un doble del puerto y el adaptador SMTP contra `mailpit`; un doble despacho de la misma notificación envía una sola vez; al llegar al 80 % del tope se emite la alerta y al 100 % el envío queda diferido en `programada`; contraseña nunca en logs
- **Dependencias**: C-03
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: Q-23 (SMTP saliente o API HTTPS de correo permitida desde el host elegido; Render gratuito bloquea 25, 465 y 587, y la contraseña de aplicación de Gmail no existe con Protección Avanzada ni con cuentas de trabajo). Los tests no dependen del proveedor, pero sin Q-23 no hay verificación de correo real en producción: si resulta necesaria una API HTTPS, se agrega como segundo adaptador del mismo puerto (alcance acotado, registrado en C-20). Tensión de la KB: el Flujo 1 de `07` dice que el barrido envía la verificación; este change la intenta enviar de inmediato por el mismo caso de uso para no sumar hasta 5 minutos de espera (decisión de diseño a validar).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 1 (US-001 a US-005)
  - `knowledge-base/05_reglas_de_negocio.md` §Cuentas (RN-01 a RN-05), §Pacientes (RN-47 a RN-49)
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
  - `GET/POST /api/v1/usuarios`, `PATCH /api/v1/usuarios/{id}` — el Administrador crea y desactiva personal con un único rol; un usuario `profesional` se asocia a un profesional (US-006)
  - `GET/POST /api/v1/boxes`, `GET/POST /api/v1/profesionales`, `PATCH /api/v1/profesionales/{id}` — un box fijo por profesional; desactivar conserva el historial
  - `GET/PUT /api/v1/profesionales/{id}/horario-semanal` — varios bloques por día, rechaza bloques superpuestos del mismo día
  - `GET/POST /api/v1/profesionales/{id}/bloqueos`, `DELETE /api/v1/bloqueos/{id}` — feriado, vacaciones, ausencia, bloqueo
  - `GET/POST /api/v1/prestaciones`, `PATCH /api/v1/prestaciones/{id}` — semilla del catálogo inicial de 9 prestaciones con duraciones sugeridas; cambiar una duración no altera turnos creados (RN-15)
  - `GET/PATCH /api/v1/consultorio` — `modo_liberacion`, plazos en horas y teléfono del consultorio
  - Tests primero: bloques superpuestos rechazados; segundo profesional con el mismo box rechazado; solo el Administrador escribe (403 para otros roles); desactivar no borra; el catálogo semilla se carga una sola vez; el `consultorio_id` de cada recurso sale del `Principal`
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
  - Migración: `turno` (con `ciclo_confirmacion` y columnas de hitos), `turno_historial` (solo inserta). La restricción `turno_sin_solapamiento` (`EXCLUDE USING gist` sobre `consultorio_id`, `profesional_id`, `tstzrange(inicio, fin, '[)')`, con `where` que excluye sobreturnos y estados `cancelado`/`liberado`) se declara en el modelo con `ExcludeConstraint` y se **crea a mano en la migración** (`CREATE EXTENSION IF NOT EXISTS btree_gist` primero, luego la restricción con `op.create_exclude_constraint` u `op.execute`): el autogenerate de Alembic no la detecta
  - Casos de uso: crear turno por Recepción/Administrador (valida horario, bloqueos y duración de la prestación; nace `pendiente` o `confirmado`, RN-23), reprogramar atómico (reserva el nuevo antes de liberar el anterior, vuelve a `pendiente`, incrementa el ciclo, RN-32 y RN-37), cancelar con motivo, confirmar, liberar manual, `atendido`, `ausente` y corrección `ausente` a `atendido`
  - Cada transición escribe en `turno_historial` (actor, estados, fecha); todas pasan por `acceso.autorizar` de C-04
  - Violación de la restricción de exclusión (SQLSTATE `23P01`, leído de la excepción del driver) traducida en el adaptador del repositorio a un error de dominio "horario ocupado" y en la API a 409; el dominio no conoce el código SQL
  - `GET/POST /api/v1/turnos`, `GET /api/v1/turnos/{id}`, `PATCH /api/v1/turnos/{id}`, `POST /api/v1/turnos/{id}/{confirmar|cancelar|liberar|atendido|ausente}`, `GET /api/v1/turnos/{id}/historial`, `GET /api/v1/agenda?profesional_id=&fecha=` (el Profesional solo ve su agenda)
  - Lecturas de pacientes derivadas de turnos: `GET /api/v1/pacientes/{id}/turnos` (US-038) y adaptador del puerto de C-08 que acota la búsqueda del Profesional a pacientes de su agenda (RN-50)
  - RN-16: crear un bloqueo sobre un período con turnos devuelve la lista de turnos afectados y exige resolverlos de forma explícita (extiende el endpoint de C-06)
  - Tests primero (integración contra PostgreSQL real): **dos turnos solapados del mismo profesional insertados en la base son rechazados por la restricción y el error trae `23P01`** (este test valida la expresión `tstzrange` con `&&`, que la documentación de SQLAlchemy no ejemplifica, y confirma SU-39); turnos contiguos (`fin` = `inicio` del siguiente) sí se aceptan; otro profesional y otro consultorio no chocan; `cancelado`/`liberado` no ocupan el hueco; dos reservas concurrentes del mismo hueco, solo una prospera; reprogramación fallida deja el original intacto; `atendido` inmutable; `ausente` antes de la hora de inicio rechazado; el Profesional no marca turnos ajenos
- **Dependencias**: C-04, C-06
- **Governance**: CRITICO
- **Riesgos / bloqueado por**: Q-26 (`btree_gist` en el PostgreSQL elegido; si no se puede habilitar, la regla central de no solapamiento no se garantiza en la base). SU-39 (el código `23P01` se confirma con el propio test). Q-04 y Q-20 se leen en C-10.
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
  - `GET /api/v1/pacientes` — búsqueda por apellido, DNI o teléfono, paginada; `POST /api/v1/pacientes` — ficha mínima (nombre, apellido, teléfono, correo, DNI obligatorios; obra social y notas opcionales); DNI duplicado responde 409
  - `GET/PATCH /api/v1/pacientes/{id}`; sin borrado físico (RN-58)
  - Vinculación manual cuenta-ficha tras verificar identidad, registrada; una ficha ya vinculada no se vincula a otra cuenta (US-039)
  - ABAC: Recepción y Administrador ven todos los pacientes del consultorio; el Paciente solo su ficha; el Profesional se acota mediante un puerto cuyo adaptador entrega C-07
  - Tests primero: DNI único por consultorio; búsqueda por cada criterio; Paciente no accede a la ficha de otro (404); doble vinculación rechazada; la ficha creada en el momento sirve para dar un turno
- **Dependencias**: C-04
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-05 (vinculación de un paciente que se registra con un DNI ya cargado), Q-10; no frenan la implementación.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 8 (US-036 a US-039)
  - `knowledge-base/05_reglas_de_negocio.md` §Pacientes (RN-47 a RN-51), RN-58
  - `knowledge-base/04_modelo_de_datos.md` §paciente
  - `knowledge-base/11_politicas_de_acceso_abac.md` §Matriz de decisión (acciones de paciente)

---

### [C-09] `availability-public-booking`
- **Estado**: `[ ]` pendiente
- **Scope**: Disponibilidad pública y autogestión del turno por el paciente
  - Servicio de dominio puro `disponibilidad`: horario semanal − excepciones − turnos activos, duración de la prestación elegida, granularidad de inicio configurable y zona horaria del consultorio; un turno nunca se parte entre bloques (RN-14)
  - `GET /api/v1/publico/consultorio`, `/publico/prestaciones`, `/publico/profesionales`, `/publico/disponibilidad` — sin ingreso, sin datos de otros pacientes, con límite de solicitudes (adaptador en memoria por proceso para estas lecturas; Redis opcional)
  - Paciente verificado: `POST /api/v1/turnos` con origen `online` (solo para su propia ficha, nace `pendiente`), `GET /api/v1/turnos` (solo los propios, con acciones según estado y plazo), confirmar desde la cuenta
  - Cancelar y reprogramar propios hasta 24 h antes (`horas_limite_paciente`); pasado el plazo la respuesta incluye el teléfono del consultorio
  - Conflicto de reserva responde 409 con horarios alternativos cercanos (RN-24)
  - Puerto `ProgramadorHitos` (implementación nula; la real llega en C-16) invocado al reservar y reprogramar. No confundir con el puerto `Planificador` del barrido (C-15), que solo oculta el disparador
  - Tests primero: disponibilidad con horario, bloqueo, turno existente y duraciones distintas; reserva sin verificar rechazada; el paciente no ve ni opera turnos ajenos; cancelación a 24 h exactas y a 23 h 59 min con reloj simulado; reprogramar a un horario ocupado mantiene el original
- **Dependencias**: C-05, C-07
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-06 y Q-11 (granularidad y anticipación a fijar en el diseño).
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` Épica 4 (US-013 a US-018)
  - `knowledge-base/05_reglas_de_negocio.md` RN-11 a RN-14, RN-17, RN-24, RN-33, RN-35, RN-37
  - `knowledge-base/07_flujos_principales.md` Flujos 3 y 6
  - `knowledge-base/10_preguntas_abiertas.md` Q-06 y Q-11 (granularidad y anticipación a fijar en el diseño)
  - `knowledge-base/11_politicas_de_acceso_abac.md` A4 (ventana temporal)

---

### [C-10] `overbooking-authorization`
- **Estado**: `[ ]` pendiente
- **Scope**: Sobreturnos con autorización registrada
  - Migración `autorizacion_sobreturno` (`UNIQUE (turno_id)`, respuesta del profesional `sin_respuesta`/`aprobado`/`rechazado`)
  - `POST /api/v1/turnos/{id}/sobreturno` — solo Recepción o Administrador, con autorización explícita y motivo; `es_sobreturno = true` queda fuera de la restricción de exclusión; respeta horario semanal y bloqueos (RN-43); los pacientes nunca lo generan
  - Registro de autorizante, fecha, motivo y `profesional_notificado_en`; aviso al profesional visible en su agenda
  - `POST /api/v1/sobreturnos/{id}/respuesta-profesional` — el Profesional afectado aprueba o rechaza (solo en su agenda); la respuesta se registra y no bloquea el otorgamiento (RN-40)
  - Sobreturnos marcados en `GET /agenda` y en las vistas del turno
  - Tests primero: sobreturno sin autorización o sin motivo rechazado; fuera de horario o sobre bloqueo rechazado; el paciente recibe 403; el profesional no responde un aviso ajeno; el sobreturno no bloquea ni es bloqueado por la restricción de exclusión (se inserta uno encima de un turno regular en PostgreSQL real)
- **Dependencias**: C-07
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: Q-04 (¿el profesional puede vetar o solo se le avisa?) y Q-20 (máximo de sobreturnos y horario); el diseño sigue la suposición de RN-40.
- **Leer antes**:
  - `knowledge-base/06_funcionalidades.md` US-024 y US-029
  - `knowledge-base/05_reglas_de_negocio.md` §Sobreturnos (RN-39 a RN-43)
  - `knowledge-base/07_flujos_principales.md` Flujo 7
  - `knowledge-base/04_modelo_de_datos.md` §autorizacion_sobreturno
  - `knowledge-base/10_preguntas_abiertas.md` Q-04 y Q-20

---

## FASE 3 — Frontend de la rebanada vertical

> Agente C trabaja en estas pantallas mientras los agentes A y B avanzan en el backend. El flujo completo de reserva y gestión funciona de punta a punta al terminar C-14 y C-13.

### [C-11] `frontend-shell-auth`
- **Estado**: `[ ]` pendiente
- **Scope**: Esqueleto del frontend y pantallas de cuenta
  - `src/app` con enrutado, proveedores y guardas por rol; layouts por rol (paciente, recepción, profesional, administrador); las rutas de los enlaces de correo (`/verificar-email`, confirmación de turno) las resuelve el router de la SPA
  - `src/services`: cliente HTTP con `VITE_API_BASE_URL` (variable de compilación pública; el build estático se publica en Cloudflare Pages), token de acceso en memoria y renovación por cookie `HttpOnly` con `credentials: 'include'`, manejo de 401/403/404; reintento acotado con aviso en las lecturas cuando la API está dormida y responde lento o con error de arranque
  - Diseño atómico base (`atoms`, `molecules`, `organisms`, `templates`) y patrón contenedor/presentacional
  - `features/auth`: registro, verificación de correo, reenvío, ingreso, recuperación y restablecimiento de contraseña, cuenta del usuario
  - Tests primero (Vitest + Testing Library): componentes presentacionales con props; contenedores con la API simulada; la guarda de rol redirige; el token no se persiste en `localStorage`; una API que tarda o falla en el arranque muestra el aviso y reintenta sin romper la pantalla
- **Dependencias**: C-05
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: Q-28 (estrategia de la cookie de renovación entre el dominio de Pages y el de la API; hasta resolverla, la renovación se prueba solo contra un API simulada o en el mismo origen local).
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Estructura de directorios (frontend), §Patrones aplicados, §Seguridad
  - `knowledge-base/12_devops_y_despliegue.md` §Cookie de renovación y dominios
  - `knowledge-base/03_actores_y_roles.md` §Rutas públicas, §Rutas privadas por rol
  - `knowledge-base/06_funcionalidades.md` Épica 1
  - `knowledge-base/07_flujos_principales.md` Flujos 1 y 2

---

### [C-12] `frontend-admin-config`
- **Estado**: `[ ]` pendiente
- **Scope**: Pantallas de configuración del Administrador
  - `features/configuracion`: usuarios del personal, profesionales con su box, editor de horario semanal por bloques, excepciones y bloqueos (muestra la lista de turnos afectados y exige resolverlos), catálogo de prestaciones, parámetros del consultorio (modo de liberación, plazos, teléfono)
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
  - `features/agenda`: vista diaria por profesional con estado de cada turno y sobreturnos marcados; el Profesional ve solo la propia
  - `features/turnos`: dar turno (buscar o crear ficha en el momento), mover, cancelar con motivo, confirmar por el paciente, marcar atendido y ausente
  - `features/pacientes`: búsqueda, ficha, historial de turnos, vinculación de cuenta
  - Autorizar sobreturno con motivo y aviso/respuesta del profesional
  - Tests primero: el 409 de horario ocupado se muestra con alternativas; las acciones no permitidas por estado no se renderizan; el Profesional no ve acciones de creación
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
  - El sitio estático siempre responde aunque la API esté dormida: pantalla de espera "el servicio está iniciando" con reintento antes de mostrar un error
  - Diseño responsive (el paciente usa el celular)
  - Tests primero: las acciones se ocultan fuera de ventana; el flujo registro, verificación y reserva con la API simulada; los errores 409 y 403 se muestran sin romper la pantalla; una API lenta muestra la espera y luego los datos
- **Dependencias**: C-09, C-11
- **Governance**: MEDIO
- **Riesgos / bloqueado por**: Q-24 (cuánto tarda en despertar el host elegido; define el tiempo de espera de la pantalla) y Q-28 (cookie entre dominios).
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
  - `POST /internal/barrido` fuera de `/api/v1`, excluido del OpenAPI público, autenticado con `SWEEP_SHARED_SECRET` comparado en tiempo constante; sin secreto configurado o con uno incorrecto no ejecuta nada; responde con el resumen del barrido (conteos y si obtuvo el candado)
  - Candado en PostgreSQL contra ejecuciones simultáneas: `FOR UPDATE SKIP LOCKED` sobre las filas del lote y/o `pg_try_advisory_lock`; si no obtiene el candado, termina sin hacer nada. Transacciones cortas y condicionales por fila. Sin Redis
  - Despacho de notificaciones de correo `programada` vencidas con el caso de uso `DespacharNotificacion` de C-05, reintentos acotados (`NOTIFICATION_MAX_ATTEMPTS`) y estado final `fallida`; un fallo no cambia el estado del turno (RN-31)
  - Limpieza periódica de tokens vencidos de `token_usuario` y `refresh_token` como tarea del barrido
  - Migración: columna `ciclo` y `UNIQUE (turno_id, tipo, canal, ciclo)` en `notificacion` (los correos de cuenta con `turno_id` nulo no se deduplican por esta clave: PostgreSQL trata los nulos como distintos); los correos de cuenta de C-05 siguen el mismo despacho
  - Aviso al paciente cuando el personal cancela o reprograma su turno (US-034), disparado desde los casos de uso de C-07
  - `GET /api/v1/notificaciones?estado=fallida` para Recepción y Administrador
  - Indicadores operativos mínimos: cantidad de `fallida`, antigüedad de la `programada` más vieja, estado del último barrido y envíos del día frente al tope de 500 con alerta al 80 % (almacenamiento de la marca del último barrido a decidir en el diseño)
  - Plantillas de correo con solo nombre, fecha, hora, profesional, consultorio y acción (RN-54)
  - Tests primero (reloj simulado, PostgreSQL real): doble barrido no duplica envíos; **dos barridos simultáneos: solo uno procesa y el otro termina sin trabajo**; un barrido tras 3 horas de servicio dormido procesa lo vencido sin duplicar; SMTP simulado que falla reintenta N veces y deja `fallida`; el sistema completo funciona sin `REDIS_URL`; `POST /internal/barrido` sin secreto o con secreto incorrecto responde 401/403 y no despacha; el endpoint no aparece en el OpenAPI; la plantilla no contiene datos de salud; el bucle propio ejecuta el mismo caso de uso que el endpoint
- **Dependencias**: C-05, C-07
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-25 (quién opera el disparador externo y rota el secreto; local y tests no dependen de él, producción sí). Q-27 (100 CU-h mensuales de Neon frente a un barrido cada 5 minutos con suspensión a los 5: puede mantener el cómputo casi siempre activo; si no alcanza, subir el intervalo y aceptar menor precisión de los hitos). Q-24 (con la API dormida el barrido no corre hasta que el disparador la despierta; SU-38 sin verificar). Q-23 (el despacho real depende del correo saliente). A verificar en Neon: los candados de sesión pueden no ser fiables detrás de un pooler de transacciones, por eso se prefiere `SKIP LOCKED` dentro de la transacción (no verificado).
- **Leer antes**:
  - `knowledge-base/08_arquitectura_propuesta.md` §Trabajos en segundo plano, §Seguridad (endpoint interno)
  - `knowledge-base/04_modelo_de_datos.md` §notificacion
  - `knowledge-base/05_reglas_de_negocio.md` RN-31, RN-54
  - `knowledge-base/12_devops_y_despliegue.md` §Trabajos programados en el despliegue, §Consecuencias y riesgos de la arquitectura base, §Configuración de correo (SMTP)
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-13, SU-01, SU-26, SU-38
  - `knowledge-base/06_funcionalidades.md` US-034 y US-035

---

### [C-16] `milestones-confirmation-release`
- **Estado**: `[ ]` pendiente
- **Scope**: Hitos de 48/24/12 horas, confirmación por enlace y liberación automática o manual (procesados por el barrido de C-15)
  - Implementación real de `ProgramadorHitos`: al reservar o reprogramar calcula los hitos desde `inicio` y programa las notificaciones en `notificacion`; reprogramar incrementa `ciclo_confirmacion` y pasa las notificaciones pendientes del ciclo anterior a `omitida` (RN-32)
  - Barrido T-48 h: solicitud de confirmación por correo a turnos `pendiente`, con enlace de un solo uso (`token_usuario` tipo `confirmar_turno`)
  - Barrido T-24 h: recordatorio a `pendiente` y `confirmado`; para `pendiente` advierte la liberación
  - Barrido T-12 h: modo automático pasa `pendiente` a `liberado` con `UPDATE ... WHERE estado = 'pendiente'` y avisa al paciente; modo manual fija `marcado_sin_confirmar_en` sin liberar (RN-27, RN-28)
  - RN-29: los hitos ya vencidos al crear o reprogramar se omiten y el turno queda "sin confirmar" para que decida Recepción (decisión de Q-03 registrada en el diseño)
  - Los hitos tienen una precisión de la frecuencia del disparador (5 minutos) y toleran un retraso del barrido: nunca duplican y nunca se pierden (están en PostgreSQL)
  - `POST /api/v1/publico/confirmar-turno` con token — solo confirma; turno ya `liberado` se rechaza y ofrece reservar de nuevo
  - `GET /api/v1/turnos?sin_confirmar=true` para Recepción; confirmar, cancelar y liberar reutilizan los casos de uso de C-07
  - Correo de resumen del turno al reservar (US-014)
  - Tests primero (reloj simulado, tablas de tiempo): solicitud a 48 h exactas y no antes; idempotencia ante barridos repetidos y simultáneos; reserva con 10 h de anticipación; modo manual no libera; enlace usado o vencido rechazado; reprogramar reinicia el ciclo; un `confirmado` nunca se libera; un barrido tardío (reloj adelantado tras un corte del disparador) procesa lo vencido una sola vez
- **Dependencias**: C-09, C-15
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-03 y Q-07 (hitos ya vencidos y enlace de un solo uso, a validar con el Product Owner). SU-38 y Q-25 (la liberación a las 12 h depende de que el disparador sea puntual y confiable). Si el barrido se retrasa más allá de un hito siguiente, el comportamiento exacto se registra en el diseño (extiende Q-03).
- **Leer antes**:
  - `knowledge-base/05_reglas_de_negocio.md` §Confirmación, recordatorio y liberación (RN-25 a RN-32) y la línea de tiempo del turno
  - `knowledge-base/07_flujos_principales.md` Flujos 4 y 5
  - `knowledge-base/04_modelo_de_datos.md` §turno (hitos), §token_usuario, §notificacion
  - `knowledge-base/06_funcionalidades.md` US-016, US-025, US-030 a US-032
  - `knowledge-base/10_preguntas_abiertas.md` Q-03 y Q-07

---

### [C-17] `whatsapp-one-click`
- **Estado**: `[ ]` pendiente
- **Scope**: WhatsApp semimanual preparado por el sistema y enviado por Recepción
  - Value object `Telefono` con normalización internacional (código de país de Argentina por defecto, RN-53)
  - Constructor de mensaje sin datos de salud (RN-54) y enlace `wa.me` con teléfono y texto prellenados
  - Los hitos T-48 h y T-24 h de C-16 y los avisos por cambios del personal (US-034) crean además, en el mismo barrido, una notificación canal `whatsapp` en estado `preparada`
  - `GET /api/v1/notificaciones?canal=whatsapp&estado=preparada`, `GET /api/v1/notificaciones/{id}/whatsapp`, `POST /api/v1/notificaciones/{id}/marcar-enviada` (estado `enviada_manual` y quién la marcó)
  - Sin API oficial de WhatsApp Business (backlog)
  - Tests primero: normalización con prefijos locales y formatos variados; el mensaje no incluye prestación detallada ni datos de salud; marcar enviada registra al usuario; solo Recepción y Administrador acceden; un turno cancelado no deja mensajes `preparada` activos; un barrido repetido no duplica el mensaje preparado
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
  - Panel de estado operativo para el Administrador con los indicadores de C-15: último barrido, antigüedad de la notificación `programada` más vieja, `fallida` y envíos del día frente al tope de 500 (alerta visible al 80 %)
  - Tests primero: marcar enviada actualiza la lista; el enlace usa el `wa.me` entregado por la API; acciones de la lista respetan los permisos; vista vacía y de error; la alerta del tope aparece al 80 % y no antes; un último barrido viejo se muestra como advertencia
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
  - Topología de producción (DD-13): frontend estático en **Cloudflare Pages** (build Vite con `VITE_API_BASE_URL`), API como servicio web gratuito (contenedor del `Dockerfile` del backend, host por decidir, Q-24), PostgreSQL en **Neon** (`DATABASE_URL` con `postgresql+asyncpg`, `btree_gist` verificado), sin proceso persistente aparte y sin Redis obligatorio
  - Migraciones (`alembic upgrade head`, un único head) y semilla idempotente como paso de despliegue; HTTPS, `CORS_ORIGINS` y `FRONTEND_BASE_URL` del dominio público; `OPENAPI_DOCS_ENABLED=false` (`/docs` y `/openapi.json` deshabilitados); secretos (`JWT_SECRET_KEY`, `SWEEP_SHARED_SECRET`, `SMTP_PASSWORD`, `DATABASE_URL`) solo en el almacén de secretos del host
  - Disparador externo cada 5 minutos a `POST /internal/barrido` con `SWEEP_SHARED_SECRET` (por ejemplo `schedule` de GitHub Actions o cron trigger de Cloudflare Workers; quién lo opera y cómo se rota el secreto, Q-25); comprobar que el último barrido es reciente y medir su puntualidad (SU-38)
  - Correo real desde el host: SMTP con `aiosmtplib` (587 con STARTTLS) o, si el host bloquea los puertos, un segundo adaptador de `EnviadorCorreo` sobre una API HTTPS de correo (Q-23); contador diario con tope de 500 y alerta al 80 % verificado
  - Cookie de renovación probada entre el dominio de Pages y el de la API (`SameSite=None; Secure` o dominio común, Q-28)
  - Docker Compose solo para local/dev y como alternativa en una VM si se exige el stack completo (Q-29): sin clave `version`, healthchecks, `restart: unless-stopped`, `mailpit` en perfil `dev`, Redis en perfil `redis`
  - `pg_dump` programado fuera de la base y restauración probada (los respaldos contienen datos personales: acceso restringido, no se versionan, RN-58)
  - Prueba E2E de la rebanada completa contra el stack local de Compose con reloj simulado: registro, verificación, reserva, solicitud a 48 h, recordatorio a 24 h, liberación a 12 h, indicador; más una prueba de humo contra el despliegue real (sin reloj simulado)
  - Recorrer la lista de verificación previa a publicar el enlace público (`12`); confirmar con el consultorio nombre, teléfono y duraciones de prestaciones
  - Tests primero / verificaciones: humo del arranque con `docker compose up`; `POST /internal/barrido` sin secreto responde 401/403 y con secreto 200; `/docs` responde 404 en producción; `alembic heads` devuelve uno solo; el despliegue deja un barrido reciente
- **Dependencias**: C-14, C-18, C-19
- **Governance**: ALTO
- **Riesgos / bloqueado por**: Q-23 (correo saliente), Q-24 (host de la API; la API se duerme por inactividad), Q-25 (operador del disparador), Q-26 (`btree_gist` en el proveedor), Q-27 (horas de cómputo de Neon frente al intervalo del barrido), Q-28 (cookie entre dominios) y Q-29 (si se exige el stack completo, este change se resuelve con Compose en una VM: la alternativa está documentada en `12`). Todas siguen abiertas: el spike de GATE 0 busca cerrarlas antes del último día; si no se cierran, este change es donde fallan.
- **Leer antes**:
  - `knowledge-base/12_devops_y_despliegue.md` (completo, §Lista de verificación previa a publicar el enlace público)
  - `knowledge-base/08_arquitectura_propuesta.md` §Seguridad, §Variables de entorno, §Trabajos en segundo plano
  - `knowledge-base/09_decisiones_y_supuestos.md` DD-10, DD-13, §Riesgos, SU-27, SU-37, SU-38
  - `knowledge-base/10_preguntas_abiertas.md` Q-02, Q-09, Q-18, Q-23 a Q-29

---

## Preguntas abiertas que afectan al plan

> Siguen abiertas en `knowledge-base/10_preguntas_abiertas.md`. Esta tabla solo indica dónde pegan; no las resuelve.

| Pregunta | Tema | Changes afectados | Efecto si no se resuelve |
|----------|------|-------------------|--------------------------|
| Q-23 | Correo saliente o API HTTPS de correo permitida desde el host | C-05, C-15, C-20 | Sin correo automático en producción (único canal automático) |
| Q-24 | Servicio web gratuito para la API | C-14, C-15, C-20 | Define suspensión, tiempo de arranque, puertos y secretos |
| Q-25 | Quién opera el disparador externo y rota el secreto | C-15, C-16, C-20 | Sin disparador no hay recordatorios ni liberación; al volver procesa lo vencido sin duplicar |
| Q-26 | `btree_gist` en el PostgreSQL elegido | C-01, C-07, C-20 | No se garantiza el no solapamiento en la base |
| Q-27 | 100 CU-h de Neon frente al intervalo del barrido | C-15, C-20 | Hay que subir el intervalo y los hitos pierden precisión |
| Q-28 | Cookie de renovación entre dominios | C-03, C-11, C-14, C-20 | La sesión del navegador no persiste |
| Q-29 | Si se exige el stack completo | C-01, C-20 | Despliegue con Compose en una VM propia |
| Q-01 | Orden de recorte si el plazo no alcanza | todos | Ver [Si el plazo aprieta](#si-el-plazo-aprieta) |

---

## BACKLOG (fuera de la v1)

> No generan changes ni entran en el plazo del 2026-10-12. Orden de prioridad acordado en `knowledge-base/06_funcionalidades.md` Épica 10. Cuando se planifiquen, se agregan como changes nuevos (`C-21` en adelante) sin alterar los de la v1.

| Prioridad | ID | Funcionalidad diferida | Nota |
|-----------|----|------------------------|------|
| 1 | US-B01 | Auditoría y consentimiento de datos conforme a la Ley 25.326 | Feature planificada, diferida. Riesgo registrado: se almacenan datos personales desde la v1 (RN-58). |
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
| C-08 | patient-records | 2 | C-04 | ALTO | B |
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

**Primer change recomendado**: `C-01` (foundation-setup), con el spike de infraestructura en paralelo (Agentes B y C). Para arrancar: `/opsx:propose C-01-foundation-setup`
