# Sistema de Turnos y Agenda Odontológica

Sistema web para que un consultorio odontológico de 2 a 5 profesionales reduzca las ausencias, automatice la confirmación de turnos y controle los sobreturnos.

Trabajo Práctico Integrador de la materia Metodología I (UTN), desarrollado en equipo.

## TP de Skills y MCP — Parte 2

[Aplicación y resultados](docs/skills-mcp/aplicacion.md) · [Configuración reproducible de Context7](docs/skills-mcp/context7.md) · [Revisión crítica e inventario de cambios](docs/skills-mcp/revision-critica.md) · [Evidencias y pendientes](docs/skills-mcp/evidencias/README.md).

Al preparar este TP, C-07 tenía planificación validada y 36 tareas pendientes. La implementación posterior quedó completada y archivada: 36/36 tareas y 906 pruebas aprobadas. Su evidencia se registra en [las tareas del change archivado](openspec/changes/archive/2026-11-03-c-07-turnos-core/tasks.md); el informe del TP conserva su contexto documental original. La guía de Context7 contiene ejemplos sin credenciales y no requiere regenerar la fundación.

## Equipo

| Integrante |
|------------|
| Avalos, Pablo |
| Blangetti, Sofia |
| Suarez, Ismael |

## El problema

Hoy el consultorio lleva la agenda en papel, planilla o Google Calendar, y confirma los turnos a mano por WhatsApp y por teléfono. El resultado son turnos perdidos por ausencias y sobreturnos que se dan sin control y complican la atención.

## Qué incluye la primera versión (v1)

- Agenda por profesional, con un box fijo por profesional, duración según la prestación, horarios semanales y bloqueos.
- Prevención de solapamientos y sobreturnos autorizados por Recepción, con aviso al profesional.
- Reserva online por enlace público, con cuenta de paciente: el paciente reserva, confirma, cancela y reprograma por su cuenta hasta 24 horas antes.
- Confirmación 48 horas antes, recordatorio 24 horas antes y liberación automática del turno sin confirmar 12 horas antes.
- Correo automático y mensaje de WhatsApp preparado por el sistema, que Recepción envía con un clic.
- Cinco roles con permisos (administrador, recepción, profesional, paciente y administrativo) y autorización por atributos.
- Indicador de ausentismo para el administrador.

Queda fuera de la v1 (backlog): auditoría de accesos y circuito de derechos de la Ley 25.326 (change C-21 de la segunda parte; el aviso de privacidad y su aceptación ya están en la v1), lista de espera, seña por Mercado Pago, recall automático, API oficial de WhatsApp, facturación ARCA y obras sociales, odontograma y presupuestos, e importación desde planilla. El detalle está en [`knowledge-base/06_funcionalidades.md`](knowledge-base/06_funcionalidades.md).

## Estado del proyecto

- **Entrega en dos partes:** la primera el 2026-10-19, con los changes completos y verificados a esa fecha; la segunda, con el resto. Se entrega el repositorio de GitHub.
- **Fundación terminada:** descubrimiento de producto, base de conocimiento, roadmap de 20 changes, skills y reglas del proyecto.
- **C-00 completado:** creación de turnos sin solapamientos, archivada e integrada a `main`.
- **C-01 completado y archivado:** entorno local, salud HTTP, configuración, logging y frontend mínimo integrados a `main`, con las 22 tareas completadas y seis especificaciones sincronizadas. El change está en [`2026-10-15-c-01-foundation-setup`](openspec/changes/archive/2026-10-15-c-01-foundation-setup/). La [ejecución de CI de `2c463ad`](https://github.com/ismaelsuarez/desarrollo_Active_Stack/actions/runs/38834034577) pasó los cuatro jobs.
- **C-02 completado y archivado:** modelos troncales con `consultorio_id`, migración de identidad `0002_core_models`, puerto `Reloj`, Value Object `Dni` y servicio de semilla con Argon2 integrados a `main`, con las 23 tareas completadas y cuatro especificaciones sincronizadas. El change está en [`2026-10-30-c-02-core-models`](openspec/changes/archive/2026-10-30-c-02-core-models/).
- **C-03 completado y archivado:** autenticación JWT HS256 con PyJWT, hash Argon2 con pwdlib, rotación atómica de refresh tokens en cookies HttpOnly SameSite=Strict, RBAC con dependencias FastAPI, rate limiting contra tabla `intento_ingreso` con mitigación de timing attacks dummy, e integración con puerto `Reloj` inyectado, con las 15 tareas completadas y especificaciones sincronizadas. El change está en [`2026-10-30-c-03-auth-core`](openspec/changes/archive/2026-10-30-c-03-auth-core/).
- **C-05 completado y archivado en el workspace:** cuenta de paciente, aviso versionado, verificación, recuperación y autoservicio, con SMTP y despacho durable. Las 21 tareas y seis especificaciones están cerradas en [`2026-11-03-c-05-patient-account`](openspec/changes/archive/2026-11-03-c-05-patient-account/). Verificación: 465 pruebas completas en Linux y 265 unitarias/API en Windows, sin omisiones. Sin commit ni push de esta sesión.
- **Próximo change:** C-06 (`agenda-config`), según el orden de construcción de [`CHANGES.md`](CHANGES.md).
- **Código ejecutable:** backend de C-00, entorno de C-01, modelos y semilla de C-02, autenticación de C-03, políticas ABAC de C-04 y cuenta/correo de C-05. Aún no hay pantallas de agenda ni despliegue publicado.

## Stack tecnológico

### Cuenta del paciente y correo de C-05

Para instalar las dependencias desde `backend/`, ejecutar `uv sync --locked`. En Windows incluye `tzdata`, que permite resolver la zona del consultorio sin depender de una instalación manual de datos horarios.

En desarrollo, `.env.example` apunta al servicio Mailpit: `SMTP_HOST=mailpit`, `SMTP_PORT=1025` y `SMTP_STARTTLS=false`. Para SMTP externo, configurar host, usuario, remitente y `SMTP_PASSWORD` mediante entorno o archivo de secreto, con `SMTP_PORT=587` y `SMTP_STARTTLS=true`. `SMTP_PASSWORD` se oculta en la configuración y en logs. Esto no agrega secretos obligatorios a `seed` ni a las migraciones.

Los enlaces usan `FRONTEND_BASE_URL`. Verificación vence a las 24 horas y recuperación a los 30 minutos. `EMAIL_DAILY_LIMIT=500` y `EMAIL_DAILY_LIMIT_ACCOUNT=150` reservan parte del cupo para turnos; el cupo de cuenta debe ser menor al total. `EMAIL_DAILY_ALERT_RATIO=0.8` configura la alerta.

Registro admite `REGISTRATION_LIMIT_PER_ORIGIN=10`, `REGISTRATION_LIMIT_GLOBAL=50` y `REGISTRATION_LIMIT_WINDOW_MINUTES=60` (máximo 1440). Recuperación/reenvío usan `ACCOUNT_EMAIL_LIMIT=3` y `ACCOUNT_EMAIL_WINDOW_MINUTES=15`, por cuenta y propósito. `NOTIFICATION_MAX_ATTEMPTS=3`, `NOTIFICATION_CLAIM_TTL_SECONDS=120` y `SMTP_TIMEOUT_SECONDS=30` controlan reintentos: el timeout total de envío debe ser menor que el TTL. Todos los umbrales son positivos y la fracción de alerta debe estar entre cero exclusivo y uno inclusive.

Verificación de la configuración desde `backend/`: `uv run pytest tests/unit/test_account_config.py tests/unit/test_config.py tests/unit/test_logging.py -q`. Las pruebas de persistencia y SMTP real requieren PostgreSQL y Mailpit en contenedores; no se reemplazan por SQLite ni por mocks de la base.

Endpoints de cuenta (prefijo `/api/v1`):

| Ruta | Contrato |
|------|----------|
| `GET /publico/aviso-privacidad` | Texto y versión vigente; completa los datos del consultorio. En producción rechaza un aviso que conserva marcadores. |
| `POST /auth/registro` | Cuenta paciente, ficha o solicitud de vinculación, aceptación y versión del aviso; respuesta 201 idéntica para DNI nuevo o existente. El intento se confirma antes de validar el cuerpo; exceso responde 429. |
| `POST /auth/verificar-email` | Cuerpo con `token`; verifica y consume el enlace una vez. El consultorio sale de la fila del token. |
| `POST /auth/reenviar-verificacion` | Cuerpo con `email`; respuesta genérica, con límite durable de envíos. |
| `POST /auth/recuperar-password` | Cuerpo con `email`; respuesta genérica exista o no, solo envía a cuentas activas verificadas. |
| `POST /auth/restablecer-password` | Cuerpo con `token` y `password`; consume el enlace y revoca todas las sesiones renovables de esa cuenta. |
| `PATCH /auth/cambiar-password` | JWT y cuerpo con `password_actual` y `password_nueva`. |
| `PATCH /auth/actualizar-cuenta` | JWT de paciente y cuerpo con `telefono` y/o `email`; correo diferente exige verificar de nuevo. |

Las entradas rechazan campos no declarados. Los enlaces llevan el token en el fragmento (`#token=`), y sus hashes se almacenan en `token_usuario`. Cambiar el correo invalida los enlaces de verificación y recuperación pendientes enviados a la dirección anterior. Los JWT nunca incluyen la ficha; el vínculo vigente se obtiene de la base. La revocación afecta los refresh tokens; un access token emitido conserva su vencimiento de hasta 15 minutos.

El correo se programa en la misma transacción de la cuenta y se intenta despachar después del commit, con una sesión propia. Una falla SMTP deja trabajo durable para reintento. La reclamación por fila y el resultado condicionado impiden que un envío tardío pise otro resultado; una caída después de enviar puede repetir el correo (entrega al menos una vez). El barrido periódico que retomará esas filas pertenece a C-15.

Las pruebas SMTP reciben `SMTP_TEST_HOST`, `SMTP_TEST_PORT` y `MAILPIT_API_URL`. Sus valores locales son `127.0.0.1`, `11025` y `http://127.0.0.1:18025`; CI usa los puertos `1025/8025`. Mailpit no entrega correo a destinatarios reales. El aviso sigue siendo un borrador que requiere la revisión indicada en KB 13 antes de usarse con pacientes reales.

| Capa | Tecnologías |
|------|-------------|
| Frontend | React, TypeScript, Vite |
| Backend | Python, FastAPI, SQLAlchemy 2.x asíncrono (asyncpg), Alembic |
| Autenticación | JWT (PyJWT) y pwdlib con Argon2 |
| Base de datos | PostgreSQL |
| Trabajos programados | Barrido idempotente dentro de la API, activado por un disparador HTTP externo. Redis es opcional |
| Infraestructura | Docker y Docker Compose en local; servicios gratuitos para el despliegue |
| Correo | SMTP de una cuenta existente |

Presupuesto cero: solo servicios gratuitos o con plan gratuito.

## Cómo trabajamos

Trabajamos en equipo con una metodología guiada por especificaciones (SDD) sobre estas herramientas:

| Herramienta | Para qué la usamos |
|-------------|--------------------|
| **Active-Stack** | Flujo de fundación del proyecto: base de conocimiento, roadmap, skills y reglas para los agentes |
| **SDD con OpenSpec** | Cada change se planifica y se cierra con `/opsx:propose`, `/opsx:apply` y `/opsx:archive` |
| **Engram** | Memoria persistente del trabajo con el agente. Es local y no se versiona (`.engram/` está ignorado) |
| **Claude Code** | Asistente de desarrollo por línea de comandos |
| **Linux Ubuntu** | Entorno de desarrollo, siempre desde terminales CLI |

Flujo de cada change:

1. Leer la base de conocimiento relevante en [`knowledge-base/`](knowledge-base/).
2. Identificar el change en [`CHANGES.md`](CHANGES.md) y respetar sus dependencias.
3. `/opsx:propose <change>` genera la propuesta, el diseño, las especificaciones y las tareas.
4. Implementar con TDD estricto: primero el test que falla, después el código.
5. `/opsx:archive <change>` cierra el change y se marca como hecho en `CHANGES.md`.

Los cambios van en ramas propias y se integran a `main` mediante pull request. Los commits siguen Conventional Commits.

## Skills utilizadas

Las skills del proyecto están versionadas en [`.agents/skills/`](.agents/skills/), con sus bundles completos y sin depender de instalaciones globales. `.claude/skills/` conserva enlaces relativos de compatibilidad. Antes de consumir el registro, ejecutar `python3 .agents/skills/skill-registry/scripts/refresh.py`: [`.atl/skill-registry.md`](.atl/skill-registry.md) contiene las rutas locales relativas y se deben leer los `SKILL.md` completos. El mapa de qué skill carga cada rol de agente está en [`AGENTS.md`](AGENTS.md).

**Skills de la fundación (Active-Stack)**, usadas para armar el proyecto:

| Skill | Fuente | Uso |
|-------|--------|-----|
| `active-orchestrator` | Group-Active-IA/active-orchestrator | Orquesta las fases de la fundación |
| `discovery-research` | Group-Active-IA/discovery-research | Descubrimiento de producto y de mercado |
| `kb-creator` | Group-Active-IA/kb-creator | Base de conocimiento de 13 archivos |
| `roadmap-generator` | Group-Active-IA/roadmap-generator | `CHANGES.md` con los 20 changes |
| `find-skill` | vercel-labs/skills | Búsqueda de skills para el stack |
| `skill-registry` | JuanCruzRobledo/skill-registry | Índice de rutas locales para cargar las skills completas |
| `agent-instruction` | JuanCruzRobledo/agent-instruction | `AGENTS.md` y `CLAUDE.md` |

**Skills del stack**, elegidas tras evaluar unas 45 candidatas (ver [`discovery/evaluacion-skills.md`](discovery/evaluacion-skills.md)):

| Skill | Fuente | Uso en el proyecto |
|-------|--------|--------------------|
| `fastapi` | fastapi/fastapi | API REST (se ignora su preferencia por SQLModel) |
| `sqlalchemy` | bm629/agent-skills | ORM y repositorios |
| `alembic` | bm629/agent-skills | Migraciones |
| `sql-job-queue` | bm629/agent-skills | Referencia de idempotencia del barrido |
| `postgresql-table-design` | wshobson/agents | Esquema y restricción de exclusión |
| `supabase-postgres-best-practices` | supabase/agent-skills | Buenas prácticas de PostgreSQL |
| `python-testing-patterns` | wshobson/agents | Pruebas con pytest |
| `tdd` | mattpocock/skills | Desarrollo guiado por tests |
| `security-best-practices` | openai/skills | Revisión de seguridad |
| `docker-compose-patterns` | docker/skills | Docker Compose |
| `docker-build-strategies` | docker/skills | Imágenes Docker |
| `vercel-react-best-practices` | vercel-labs/agent-skills | React |
| `typescript-react-reviewer` | dotneet/claude-code-marketplace | Revisión de React y TypeScript |
| `vitest` | antfu/skills | Pruebas del frontend |
| `react-testing` | affaan-m/ecc | Pruebas de componentes |
| `accessibility` | addyosmani/web-quality-skills | Accesibilidad de la reserva pública |

Cada skill tiene aclaraciones de uso donde contradice una decisión del proyecto, registradas en `.active-orchestrator-state.json` (sección `skills.notes`).

## Estructura del repositorio

```text
.
├── README.md                    Este archivo
├── AGENTS.md / CLAUDE.md        Instrucciones y reglas duras para los agentes (copias idénticas)
├── CHANGES.md                   Roadmap: 20 changes, dependencias y camino crítico
├── knowledge-base/              Fuente de verdad del dominio (14 archivos)
├── discovery/                   Descubrimiento de producto, análisis de mercado y exploración técnica
├── openspec/                    Changes de SDD (propuestas, especificaciones, diseño y tareas)
├── backend/                     API en capas (dominio, aplicación, infraestructura), migraciones y pruebas
├── .agents/skills/              Bundles canónicos completos de las skills del proyecto
├── .atl/skill-registry.md       Índice versionado de rutas locales relativas
└── .claude/
    ├── skills/                  Enlaces relativos de compatibilidad a .agents/skills/
    └── commands/                Comandos de OpenSpec (/opsx:*)
```

## Desarrollo local con Docker Compose

Requisitos: Docker Engine con Docker Compose v2 o posterior y Python 3 para los scripts locales. Para las pruebas fuera de contenedores: `uv`, Node.js 24 y npm. Ejecutar desde la raíz del repositorio:

```bash
scripts/dev_secrets.sh
test -f .env || cp .env.example .env
docker compose up --build -d --wait
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health').status)"
```

Frontend: `http://localhost:5173`. Salud de la API: `http://localhost:8000/api/v1/health` (responde `200` con `{"status": "ok"}`, sin consultar PostgreSQL). Compose aplica `alembic upgrade head` antes de iniciar la API. Se conserva la migración y la restricción de no solapamiento de C-00; C-01 no crea otra raíz ni requiere una revisión vacía.

`.env` contiene solo configuración no sensible. Los secretos se generan una vez en `secrets/` y se montan en `/run/secrets`; no se imprimen ni sobrescriben. La carpeta tiene modo `0700`; los archivos son legibles por el proceso no root del contenedor mediante sus montajes. `.env` y `secrets/` están ignorados por Git. Si se personalizan `POSTGRES_USER` o `POSTGRES_DB`, exportar esos mismos valores al generar los secretos y usarlos en `.env`; no regenerar credenciales sobre un volumen ya inicializado.

La configuración de la API exige `DATABASE_URL`, `JWT_SECRET_KEY` y `APP_ENV` (`development`, `test` o `production`). La clave de firma debe ocupar al menos 32 bytes UTF-8; los errores de validación nombran los campos sin mostrar valores sensibles. El entorno tiene prioridad sobre los archivos de secreto; `SECRETS_DIR` permite cambiar su directorio. `REDIS_URL` es opcional y `APP_TIMEZONE` usa `America/Argentina/Buenos_Aires` por defecto.

Servicios opcionales, sin trabajador de aplicación separado:

```bash
docker compose --profile dev up -d mailpit
python3 -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8025').status)"
docker compose --profile redis config --services
```

Mailpit captura los correos locales; su interfaz está en `http://localhost:8025`. Redis es opcional y no se necesita para arrancar C-01. El frontend de C-01 solo muestra el nombre del sistema; no implementa aún pantallas ni el proxy de C-11.

Verificación integrada en un único comando:

```bash
scripts/smoke_compose.sh
```

El smoke test construye y levanta un proyecto Compose con nombre único y volúmenes nuevos, comprueba migraciones, salud, usuario no root y Mailpit, y elimina **solo esos recursos descartables**. No reutiliza ni elimina los volúmenes del entorno habitual. Para detener el entorno habitual conservando sus datos:

```bash
docker compose --profile dev --profile redis down
```

Nunca usar una reversión completa de migraciones para deshacer solo C-01 en una base con datos de C-00. Las pruebas de reversión completa usan bases temporales propias.

## Pruebas y compilación del frontend

Desde `frontend/`:

```bash
npm ci
npm test -- --run
npm run typecheck
npm run build
```

## Verificación de migraciones y CI

Desde `backend/` (el chequeo de heads no necesita una conexión a la base):

```bash
uv run alembic heads
uv run python scripts/check_single_head.py
```

Las migraciones cargan únicamente la configuración de conexión: usan `MIGRATIONS_DATABASE_URL` si está definida y `DATABASE_URL` en otro caso, sin exigir `APP_ENV` ni `JWT_SECRET_KEY`. Sus valores también pueden proceder de archivos de secreto. Las pruebas aíslan sus URL para no seguir conexiones heredadas del entorno.

`.github/workflows/ci.yml` define verificaciones gratuitas de backend con PostgreSQL real, frontend, imágenes y arranque de Compose en cada push y pull request a `main`. La [ejecución de C-01 para `2c463ad`](https://github.com/ismaelsuarez/desarrollo_Active_Stack/actions/runs/38834034577) terminó correctamente en los jobs `backend`, `frontend`, `images` y `compose-smoke`. La validación local del workflow no sustituye GitHub Actions; cada cambio posterior requiere su propia comprobación.

## Cómo correr las pruebas del backend

### API de turnos por personal

`POST /api/v1/turnos` requiere un token de Recepción o Administrador. Ejemplo con identificadores sintéticos:

```json
{
  "paciente_id": 1,
  "profesional_id": 1,
  "prestacion_id": 1,
  "inicio": "2026-11-09T10:00:00-03:00",
  "duracion_min": 45,
  "confirmar": false
}
```

`duracion_min` y `confirmar` son opcionales. Sin ajuste, se conserva la duración del catálogo; un ajuste debe ser positivo y múltiplo de la grilla. El intervalo completo debe caber en un bloque semanal y evitar bloqueos. El consultorio y el fin los resuelve el servidor: enviarlos, o enviar otro campo desconocido, produce 422.

La respuesta 201 contiene identificadores operativos, inicio/fin, estado, indicador de sobreturno y ciclo de confirmación. La fila y su historial ya están confirmados al responder. Una ficha sin cuenta puede reservar y el personal puede superar los límites de anticipación y cantidad del paciente. A menos de 48 horas —o del umbral configurado— el turno nace confirmado; en el umbral exacto queda pendiente, salvo confirmación manual. El historial distingue ambos motivos.

Errores: 401 sin autenticación; 403 por rol; 404 por referencias inexistentes o ajenas; 409 por horario ocupado; 422 por entrada o agenda inválidas. Dos reservas regulares concurrentes del mismo hueco dejan un solo turno con su historial y un conflicto 409. Un regular también rechaza un sobreturno activo existente; la carrera de alta simultánea con sobreturnos conserva el riesgo residual documentado. La reserva pública se implementa en C-09.

### Reprogramación y acciones del turno

`PATCH /api/v1/turnos/{id}` admite `inicio` con zona y, opcionalmente, `duracion_min`. Recepción o Administrador pueden mover un turno modificable conservando el identificador y su duración actual salvo ajuste explícito. El destino se valida contra bloques, grilla, excepciones y turnos activos. Al confirmar el cambio se incrementa el ciclo una sola vez, se limpian las marcas e hitos anteriores y se aplica el umbral temporal de confirmación. Un conflicto 409 o un fallo del historial revierte todos los valores del movimiento.

Las acciones `POST /api/v1/turnos/{id}/{confirmar|cancelar|liberar|atendido|ausente}` reciben un objeto vacío, salvo `cancelar`, que admite `motivo` opcional. También admiten omitir el cuerpo; los campos extra producen 422. Confirmar sólo acepta pendientes. Liberar requiere pendiente y modo manual o marca sin confirmar. Cancelar conserva fila, actor, fecha y motivo y libera el hueco.

Recepción, Administrador y Profesional de la propia agenda pueden marcar atendido o ausente desde el instante exacto de inicio (`ahora >= inicio`); antes reciben 403. La acción `atendido` sobre un ausente es una corrección reservada a Recepción/Administrador, registrada como `corregir` sin cambiar hechos anteriores. Atendido es inmutable. Los estados o roles inválidos producen 403, el turno ajeno 404, y una lectura obsoleta 409. Cada transición y su historial se confirman o revierten juntos.

El puerto de planificación de hitos se invoca dentro de esa misma unidad de trabajo al crear o reprogramar. Su implementación de C-07 no tiene efectos; el contrato permite a C-15/C-16 sumar escrituras transaccionales y exige revertir el turno si el colaborador falla. En este change no programa hitos, ni omite avisos, ni ejecuta barridos, ni envía SMTP o WhatsApp.

### Consultas de turnos y agenda

| Ruta GET | Resultado |
| --- | --- |
| `/api/v1/turnos` | Turnos ordenados por inicio e identificador. |
| `/api/v1/turnos/{id}` | Detalle operativo del turno. |
| `/api/v1/turnos/{id}/historial` | Actor, acción, estados y fecha de los hechos, en orden. |
| `/api/v1/agenda?profesional_id=<id>&fecha=AAAA-MM-DD` | Agenda del día local del consultorio, con marca de sobreturno. |
| `/api/v1/pacientes/{id}/turnos` | Turnos pasados y futuros de una ficha, incluso sin cuenta vinculada. |

Recepción y Administrador leen su consultorio; el Profesional ve únicamente su agenda y sus propios turnos de una ficha compartida. Un turno, historial o ficha fuera de alcance devuelve 404; la agenda de un colega del mismo consultorio devuelve 403 y un profesional de otro consultorio, 404. La fecha de agenda abarca de medianoche a medianoche en `zona_horaria`, no el día UTC. Identificadores, fechas o parámetros adicionales inválidos producen 422; el consultorio siempre proviene del Principal.

Las lecturas incluyen identificadores, nombres operativos del paciente y de la prestación, horario, estado y marcas. Excluyen DNI, contacto, obra social, notas y cuenta; el historial tampoco expone JSON arbitrario de detalle. Esos datos privados no se incluyen en logs de lecturas ni rechazos. El historial sólo ofrece GET, sin modificación ni borrado. El adaptador `pacientes_de_profesional` restringe la carga de fichas por agenda para C-08 sin adelantar su CRUD.

Desactivar una prestación o un profesional conserva las lecturas de turnos y agendas existentes con el mismo alcance de rol y consultorio (RN-15, US-008). Las nuevas altas siguen rechazando referencias inactivas. Un intervalo que desborda la representación de fecha/hora se rechaza con 422, sin fijar un máximo nuevo de duración ni persistir efectos parciales.

Los bloqueos globales o propios de C-06 que interceptan turnos activos devuelven 409 con `turnos_afectados`, sin guardar el bloqueo ni cambiar los turnos. En un hueco libre se guardan con 201. Esto no amplía la garantía a una carrera simultánea entre bloqueo y alta. Verificación: `uv run pytest tests/integration/test_c07_agenda.py -q` con PostgreSQL descartable.

### Migración de Turnos Core (C-07)

`0008_turnos_core` sucede a `0007_agenda_config`: conserva identificadores, intervalos y la exclusión de C-00. Inicializa el ciclo en 1 y deja nulos el origen, actor y fechas históricas desconocidas; no fabrica eventos anteriores. `creado_en` pierde el default SQL: las nuevas escrituras reciben la fecha desde `Reloj`.

El upgrade aborta con un diagnóstico de tabla y columna si encuentra referencias huérfanas en turno, tokens o notificaciones. No borra ni reasigna registros: cualquier corrección de datos requiere un procedimiento revisado antes de reintentar.

Para verificarlo, usar exclusivamente un servidor PostgreSQL descartable en `TEST_DATABASE_URL` y ejecutar desde `backend/`:

```bash
uv run pytest tests/integration/test_c07_migration.py tests/integration/test_migracion.py tests/integration/test_account_models.py tests/integration/test_migrations.py -q
uv run alembic heads
```

Las pruebas crean y eliminan sus propias bases e incluyen upgrade desde C-06 con filas sintéticas y downgrade a `0007_agenda_config` seguido de upgrade. Debe existir un único head, `0008_turnos_core`. El downgrade elimina el historial y las columnas nuevas: el upgrade posterior no recupera esa información. Requiere revisión humana antes de usarse en un entorno con datos; se prefiere una corrección hacia adelante. Esta verificación no ejecutó restauraciones ni migraciones sobre datos reales.

En Windows, las pruebas de esta migración se ejecutaron en un contenedor Linux con Python 3.13 y uv 0.13.1, contra PostgreSQL 17 sin volumen persistente. Se usó una copia descartable de las fuentes, con los scripts en LF según `.gitattributes`; el repositorio original se montó en solo lectura. No se copiaron secretos, `.env`, `.git`, `node_modules` ni el entorno virtual de Windows.

Requisitos: [uv](https://docs.astral.sh/uv/) y Docker. Los comandos se ejecutan desde `backend/`.

```bash
# 1. Instalar las dependencias
uv sync

# 2. Pruebas unitarias (no necesitan base de datos)
uv run pytest -m "not integration"

# 3. Levantar un PostgreSQL descartable para las pruebas de integración
docker run --rm -d --name tpi-pg-test -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:17

# 4. Levantar Mailpit para las pruebas SMTP
docker run --rm -d --name tpi-mailpit -p 11025:1025 axllent/mailpit:latest

# 5. Pruebas de integración contra PostgreSQL real y Mailpit
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/postgres"
export SMTP_TEST_PORT=11025
uv run pytest -m integration

# 6. Detener los contenedores al terminar
docker stop tpi-pg-test tpi-mailpit
```

Las pruebas de integración crean una base propia, le aplican las migraciones con `alembic upgrade head` y la eliminan al terminar. Si `TEST_DATABASE_URL` no está definida, fallan con un mensaje explícito: no se omiten.

La semilla agrega nueve prestaciones sugeridas solo cuando el catálogo del consultorio está vacío: primera consulta y diagnóstico (30 min), control de rutina (20), limpieza dental (40), restauración (45), endodoncia (60), extracción simple (30), blanqueamiento (60), control de ortodoncia (20) y urgencia o consulta por dolor (30). Son valores iniciales orientativos; cada consultorio debe confirmarlos con sus profesionales. La semilla no los repone ni modifica si el equipo cambió o desactivó alguno.

Verificación de C-06 (2026-11-03): suite completa del backend en Linux, **512 pruebas aprobadas**; regresión focalizada de agenda, migración, seed y rutas C-06, **313 aprobadas**; contratos OpenAPI tras los últimos ajustes, **2 aprobadas**. PostgreSQL 17 y Mailpit se ejecutaron en contenedores temporales.

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [`knowledge-base/README.md`](knowledge-base/README.md) | Índice de la base de conocimiento y convenciones de códigos (`RN-NN`, `US-NNN`, `DD-NN`, `SU-NN`, `Q-NN`) |
| [`knowledge-base/01_vision_y_objetivos.md`](knowledge-base/01_vision_y_objetivos.md) | Propósito, alcance y casos de uso |
| [`knowledge-base/05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) | Reglas de negocio RN-01 a RN-65 |
| [`knowledge-base/08_arquitectura_propuesta.md`](knowledge-base/08_arquitectura_propuesta.md) | Arquitectura, patrones y variables de entorno |
| [`knowledge-base/10_preguntas_abiertas.md`](knowledge-base/10_preguntas_abiertas.md) | Preguntas abiertas que bloquean changes concretos |
| [`CHANGES.md`](CHANGES.md) | Plan de implementación y orden de recortes si el plazo aprieta |
| [`discovery/`](discovery/) | Análisis de 24 sistemas competidores y exploración técnica verificada |

## Reglas del proyecto

Las reglas duras que deben respetar tanto el equipo como los agentes están en [`AGENTS.md`](AGENTS.md). Algunas de las más importantes:

- El `consultorio_id` siempre sale del token, nunca del cliente.
- Tests de repositorios y restricciones contra PostgreSQL real, sin mocks de base de datos.
- Sin worker persistente: los recordatorios corren como barrido idempotente en la API.
- Sin dependencias ni servicios con costo, y sin funciones del backlog dentro de un change de la v1.

## API de fichas de pacientes (C-08)

`POST /api/v1/pacientes` permite a Recepción y Administrador crear una ficha sin cuenta: `nombre`, `apellido`, `telefono`, `email` y `dni` obligatorios; `obra_social` y `notas` opcionales. Normaliza espacios exteriores y correo, acepta DNI sin puntos ni espacios internos y devuelve `201 {"id": ...}`. DNI duplicado en el mismo consultorio responde 409; formato, datos faltantes o extras responden 422. Nunca recibe `consultorio_id`, `usuario_id` ni `activo`, ni crea una cuenta automáticamente.

`GET /api/v1/pacientes/{id}` devuelve la ficha autorizada. Recepción y Administrador reciben además `cuenta: {id, nombre_usuario, email, email_verificado}` o null. El Profesional sólo lee pacientes de su agenda y el Paciente su ficha vigente; ambos reciben la ficha sin la propiedad `cuenta`. Una ficha ajena o inexistente responde 404 y los valores nulos de teléfono/correo de fichas antiguas se conservan. No se exponen hashes ni tokens. El detalle OpenAPI enumera 401/403/404/409/422 aplicables.

`POST /api/v1/solicitudes-vinculacion/{id}/vincular` recibe únicamente `{"paciente_id": ...}` y está reservado a Recepción y Administrador. El personal elige la ficha después de verificar la identidad; el DNI declarado no obliga a elegir una coincidencia. Se bloquea primero la ficha del consultorio y se actualizan condicionalmente solicitud y ficha en una sola transacción. Admite solicitud pendiente o rechazada, correo verificado y ficha activa sin cuenta; responde 200 al confirmar, 404 para referencias ajenas/inexistentes, 409 por conflicto y 422 por extras. Dos cuentas sobre una ficha o una solicitud sobre dos fichas dejan un ganador y un 409, sin prioridad ni reintento automático.

Los repositorios de fichas, vínculos y cuentas comparten la sesión de la unidad de trabajo. Fallos del cuerpo, flush o commit revierten todos los efectos y cierran sus recursos antes de responder. Se traducen selectivamente las unicidades esperadas y los errores PostgreSQL `40P01`/`40001` a 409; otras restricciones no se disfrazan de conflicto de vínculo. C-08 conserva el esquema y el único head `0008_turnos_core`.

`GET /api/v1/solicitudes-vinculacion` está reservado a Recepción y Administrador. Admite `estado=pendiente|vinculada|rechazada`, `limit` entre 1 y 100 (20 por defecto) y `offset>=0`; omitir estado incluye también las resueltas. Devuelve `{items, total, limit, offset}` dentro del consultorio del Principal. Cada solicitud incluye DNI declarado, correo y verificación de cuenta, ficha coincidente mínima y última resolución; `ficha_vinculada` sólo presenta un vínculo vigente en las vinculadas. No devuelve usuario completo, hash ni tokens. Filtros o extras inválidos responden 422 y roles no habilitados 403.

`GET /api/v1/pacientes` permite filtrar por `apellido`, `dni` y `telefono`, combinados con AND. Apellido/teléfono se buscan como subcadena literal (los caracteres `%` y `_` no son comodines), y DNI por coincidencia exacta tras quitar espacios exteriores. Usa `limit=20` (1–100) y `offset>=0`, orden apellido/nombre/id y envelope `{items,total,limit,offset}`. El total se calcula después de aplicar el alcance del rol y consultorio. La lista sólo incluye id/nombre/apellido/teléfono/activo; el Profesional ve pacientes de su agenda y el Paciente su ficha vigente, o lista vacía sin ficha.

`POST /api/v1/solicitudes-vinculacion/{id}/rechazar` acepta `motivo` opcional y puede omitir el cuerpo. Sólo el personal habilitado resuelve una solicitud pendiente, guardando actor/fecha; repetir o resolver una ya cambiada devuelve 409. Con cuenta verificada programa un solo correo `vinculacion_rechazada` en la misma transacción y solicita despacho después del commit; sin verificar no programa correo. La plantilla sólo pide comunicarse con el consultorio, sin motivo, DNI ni datos de salud. Fallar la inserción de la notificación revierte la resolución; fallar SMTP conserva la resolución y el trabajo durable para reintento. Se reutiliza el despachador C-05: entrega al menos una vez, sin barrido nuevo ni garantía de una sola entrega SMTP.

`PATCH /api/v1/pacientes/{id}` tiene dos contratos. Recepción y Administrador corrigen nombre, apellido, teléfono, correo, DNI, obra social y notas de la ficha; los campos omitidos se conservan y sólo obra social/notas admiten `null`. Cambiar el contacto de la ficha por esta vía no cambia el correo de login, su verificación, la contraseña ni los turnos. El Paciente sólo puede enviar teléfono y/o correo de su ficha vigente; cualquier otro campo responde 422 sin cambios parciales. Un correo propio diferente actualiza cuenta y ficha, quita verificación, invalida enlaces anteriores y programa una nueva verificación que se despacha después del commit; uno equivalente tras trim/minúsculas conserva la verificación sin correo adicional. Un correo ocupado responde 409; un vínculo cambiado entre lectura y escritura responde 404, sin editar la ficha nueva. El núcleo transaccional se comparte con `/auth/actualizar-cuenta`, cuyo contrato C-05 se conserva.

`POST /api/v1/pacientes/{id}/desvincular` exige `{"motivo": "Corrección verificada"}` no vacío y sólo admite Recepción/Administrador. Quita la cuenta condicionalmente, conserva datos y turnos, deja su solicitud `rechazada` con ficha de origen, actor, fecha y motivo, y revoca todos sus refresh tokens en una transacción. Si no había solicitud, la crea usando el DNI actual de la ficha; si existía, conserva el DNI declarado original y exige que estuviera vinculada. No envía correo. El bloqueo y la recarga del usuario serializan con refresh en vuelo: también se revoca un reemplazo creado antes del commit. Sin cuenta responde 409; ficha ajena/inexistente 404; motivo inválido o extras 422; otros roles 403. Un access JWT anterior continúa vigente hasta vencer, pero la antigua ficha devuelve 404 de inmediato porque cada solicitud consulta el vínculo actual. Una vinculación posterior permite acceder a la ficha nueva con ese mismo JWT, sin incluir identificadores de ficha en sus claims.

`POST /api/v1/pacientes/{id}/reactivar` permite cuerpo ausente, `null` o `{}` y sólo personal habilitado. Reactiva una ficha inactiva sin tocar sus otros campos ni turnos, sin correo ni registro propio; una ficha activa responde 409, una ajena/inexistente 404 y campos de negocio 422. No existe la operación inversa: ni DELETE ni PATCH con `activo` permiten borrar o desactivar fichas. La leyenda de notas y su presentación corresponden a la UI de C-13 (RN-65); C-08 no agrega datos de salud ni afirma una revisión legal.

Los cuatro recorridos manuales de RN-63 usan las mismas acciones, después de verificar la identidad con el consultorio:

1. **Vínculo equivocado:** consultar cuenta/solicitud, desvincular la ficha equivocada y vincular la cuenta con la correcta, creando una ficha mínima si corresponde. Ambas fichas conservan sus turnos.
2. **Ficha correcta ocupada:** verificar a quién corresponde; rechazar la solicitud si pertenece a la cuenta actual, o desvincular esa cuenta y resolver la solicitud correcta. La cuenta desplazada conserva su solicitud rechazada y puede vincularse después.
3. **Ficha correcta inactiva:** reactivar y resolver su solicitud con el vínculo normal; no crear una ficha duplicada por DNI.
4. **Tercero registrado primero con DNI nuevo:** consultar el vínculo, gestionar manualmente las cancelaciones que correspondan con C-07 antes de corregir el contacto, desvincular, corregir la ficha y vincular a la persona correcta. Los turnos y su historial permanecen; C-08 no los cancela automáticamente.

La resolución guarda únicamente el último actor/fecha, sin auditoría histórica nueva ni recuperación automática. Las carreras se resuelven con conexiones independientes, bloqueos de fila y escrituras condicionales: no se promete un ganador entre acciones distintas. Los conflictos PostgreSQL `40P01`/`40001` del nuevo PATCH propio y de las resoluciones se traducen a 409 con rollback; esto no amplía la corrección a rutas anteriores de C-05. Las pruebas y la trazabilidad están en [la evidencia del change C-08 archivado](openspec/changes/archive/2026-11-05-c-08-patient-records/evidence.md).

## Disponibilidad y reserva online (C-09)

C-09 quedó completado y archivado el 2026-11-05, con 33/33 tareas y sus especificaciones sincronizadas. Las pruebas y la trazabilidad están en [la evidencia del change C-09 archivado](openspec/changes/archive/2026-11-05-c-09-availability-public-booking/evidence.md).

Sin sesión: `GET /api/v1/publico/consultorio`, `/prestaciones`, `/profesionales` y `/disponibilidad` (los cuatro bajo `/api/v1/publico`). Consultorio muestra nombre, dirección, teléfono y zona; catálogos sólo recursos activos del consultorio configurado, sin cuentas ni fichas. Disponibilidad recibe únicamente `profesional_id`, `prestacion_id` y `fecha=AAAA-MM-DD`. Extras, incluido `consultorio_id`, responden 422; referencias ajenas/inactivas 404; un día sin huecos devuelve `[]`.

El algoritmo puro ancla cada grilla en el comienzo de un bloque semanal y avanza `minutos_granularidad`, sin redondear la duración. Cada intervalo completo debe caber en ese bloque. Se restan excepciones globales/propias y ocupación semiabierta `[inicio,fin)`, incluidos sobreturnos activos; cancelados/liberados no ocupan. Los extremos contiguos son válidos. Sólo ofrece inicios futuros hasta hoy local + `dias_anticipacion_maxima`, con último día incluido. Usa la zona del consultorio incluso cerca de medianoche UTC y devuelve orden determinista sin modificar datos. Las consultas cargan ocupación por intervalo, sin una consulta por candidato.

Las cuatro lecturas comparten 60 solicitudes por origen en una ventana de 60 segundos por proceso. Un exceso responde 429 con `Retry-After`; otro origen conserva cuota independiente. El adaptador poda ventanas vencidas y limita memoria a 10000 orígenes activos; no expulsa un origen activo para renovar su cuota. Usa la resolución de origen/HMAC existente y `TRUSTED_PROXY_HOPS`, sin confiar directamente en `X-Forwarded-For`, ni registrar IP cruda. No requiere Redis. Reiniciar un proceso reinicia la cuota y varias réplicas no comparten este límite.

Paciente: `POST /api/v1/turnos` sólo recibe `{"profesional_id":1,"prestacion_id":1,"inicio":"2026-11-09T10:00:00-03:00"}`. El servidor resuelve la ficha vigente y el origen `online`. Exige cuenta actual con correo verificado; sin ficha devuelve 403 pidiendo contactar al consultorio sin revelar DNI ni solicitud. Campos `paciente_id`, `duracion_min`, `confirmar`, `origen`, `fin` y `consultorio_id`, incluso `null`, se rechazan con 422. El personal conserva su entrada anterior y las exenciones de horizonte y cantidad; todos respetan la grilla y agenda.

La reserva bloquea la ficha por consultorio/usuario vigente antes de contar e insertar. Cuenta únicamente futuros pendientes/confirmados, incluidos los creados por personal. Un exceso devuelve 409 indicando el máximo configurado; cancelar libera cupo. Dos reservas online no consumen simultáneamente el último cupo. El personal puede superar ese máximo por RN-64(e), de modo que no se garantiza el límite frente a una creación de personal concurrente. El orden de bloqueo ficha → cuenta coincide con la desvinculación C-08.

`GET /api/v1/turnos`, detalle e historial consultan siempre el vínculo actual, sin añadir ficha a JWT. Sin ficha, listado vacío; identificadores ajenos o de una ficha desvinculada responden 404. Las respuestas del paciente añaden `acciones_permitidas` calculadas con las mismas políticas/reloj de ejecución; las del personal conservan su contrato. Confirmar requiere pendiente; cancelar y reprogramar exigen pendiente/confirmado y `ahora <= inicio - horas_limite_paciente`. Fuera del plazo, 403 con teléfono del consultorio; un ajeno recibe primero 404.

`PATCH /api/v1/turnos/{id}` del paciente sólo admite `{"inicio":"2026-11-10T10:00:00-03:00"}`. Conserva id y duración actual, incluso 45 minutos ajustados previamente por personal, sin consumir otro cupo ni recalcular duración del catálogo. Respeta horizonte/grilla y excluye el propio turno de ocupación. Reinicia ciclo, limpia marca y aplica RN-29: pendiente a 48 horas exactas, confirmado con menos anticipación. Turno, historial y puerto `PlanificadorDeHitos` comparten transacción; fallar historial, planificación o commit revierte todo. El adaptador nulo no agrega notificaciones: correo real y enlaces corresponden a C-16, barrido a C-15.

La ocupación online responde 409 con `{"detail":{"motivo":"horario ocupado","alternativas":[{"inicio":"…","fin":"…"}]}}`. Se termina el rollback antes de abrir una lectura nueva. Ofrece hasta tres intervalos del mismo profesional desde el inicio pedido, ordenados dentro del horizonte, con duración del catálogo al crear y duración conservada al mover. `[]` es válido sin alternativas; no se muestran ocupantes ni se garantiza permanencia del hueco. El 409 de máximo conserva su mensaje propio sin alternativas. La aplicación excluye sobreturnos existentes; una alta regular simultánea con un sobreturno conserva el riesgo residual RN-17.

## Barrido y operación del correo (C-15)

El barrido reutiliza el despacho durable de C-05, con reclamación por fila y SMTP fuera de la transacción. `POST /internal/barrido` usa el consultorio configurado y exige `X-Sweep-Secret`; no admite cuerpo ni query y no aparece en OpenAPI. Sin secreto configurado o con uno incorrecto responde 403 sin ejecutar trabajo. Devuelve `ejecucion_id`, `reclamadas`, `enviadas`, `reintentadas`, `omitidas` y `fallidas`; un fallo de infraestructura devuelve 503 genérico. Para una prueba local, configurar un secreto de prueba propio y enviar ese mismo valor en el encabezado, nunca en la URL:

```bash
curl -X POST http://localhost:8000/internal/barrido -H "X-Sweep-Secret: $SWEEP_SHARED_SECRET"
```

El bucle opcional usa el mismo caso de uso: `SWEEP_IN_PROCESS_ENABLED=true`, intervalo positivo `SWEEPER_INTERVAL_SECONDS=300`. Está deshabilitado por defecto y un secreto HTTP vacío no impide usarlo. Al apagar la API cancela y espera su tarea antes de liberar el engine que creó. No requiere worker ni Redis. Procesa hasta 100 filas de cada uno de cuatro grupos (programadas/vencidas × cuenta/turno); cada ID se trata una vez por ejecución y los reintentos esperan el próximo barrido. Entrega al menos una vez: una caída después de SMTP puede repetir un correo. La reclamación vencida se revalida antes de reintentar y el resultado tardío no pisa una reclamación nueva.

Recepción y Administrador pueden consultar `GET /api/v1/notificaciones`, con `estado` opcional, `limit=50` (1–100), `offset>=0` y orden por ID descendente. Devuelve sólo ID, turno, tipo, canal, estado, intentos y fechas, sin contacto, mensaje ni error original. `GET /api/v1/notificaciones/indicadores` muestra fallidas, antigüedades de programadas/enviando, uso diario, límites/alerta y la última ejecución iniciada durable por consultorio. Cero filas produce cantidades cero y antigüedades nulas. Una ejecución interrumpida queda observable como en curso; una finalización antigua no sustituye la marca posterior. No hay reenvío manual ni pantalla nueva.

Cancelar o reprogramar por personal programa un aviso de datos mínimos dentro de la misma transacción de turno e historial. El contenido captura el horario de ese hecho; fallar SMTP no revierte el cambio. Sin email utilizable se conserva el cambio y se registra sólo un evento técnico, sin inventar destinatario ni exigir cuenta vinculada. Los hitos, resúmenes de reserva y cancelación del paciente pertenecen a C-16.

La revisión `0009_notifications_outbox_sweep` añade ciclo nullable, deduplicación por turno/tipo/canal/ciclo y metadatos del último barrido. No infiere ciclos históricos ni elimina datos legados. La purga periódica elimina tokens con `expira_en <= ahora` e intentos anteriores a 24 horas, conservando igualdad y otros consultorios. Un rollback de aplicación puede conservar el esquema aditivo; el downgrade de esquema pierde ciclo/metadatos y sólo se probó en una BD desechable. La evidencia de implementación está en [C-15](openspec/changes/archive/2026-11-05-c-15-notifications-outbox-sweep/evidence.md).
