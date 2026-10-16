# Sistema de Turnos y Agenda Odontológica

Sistema web para que un consultorio odontológico de 2 a 5 profesionales reduzca las ausencias, automatice la confirmación de turnos y controle los sobreturnos.

Trabajo Práctico Integrador de la materia Metodología I (UTN), desarrollado en equipo.

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
- **En curso:** propuesta del primer change, `c-01-foundation-setup`, lista en `openspec/changes/`.
- **Código:** todavía no hay código ejecutable. El entorno local con Docker Compose se crea en el change C-01, y esta sección se completa ahí con los comandos reales.

## Stack tecnológico

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

## Cómo correr las pruebas del backend

Requisitos: [uv](https://docs.astral.sh/uv/) y Docker. Los comandos se ejecutan desde `backend/`.

```bash
# 1. Instalar las dependencias
uv sync

# 2. Pruebas unitarias (no necesitan base de datos)
uv run pytest -m "not integration"

# 3. Levantar un PostgreSQL descartable para las pruebas de integración
docker run --rm -d --name tpi-pg-test -e POSTGRES_PASSWORD=postgres -p 55432:5432 postgres:17

# 4. Pruebas de integración contra PostgreSQL real
export TEST_DATABASE_URL="postgresql+asyncpg://postgres:postgres@127.0.0.1:55432/postgres"
uv run pytest -m integration

# 5. Detener el contenedor al terminar
docker stop tpi-pg-test
```

Las pruebas de integración crean una base propia, le aplican las migraciones con `alembic upgrade head` y la eliminan al terminar. Si `TEST_DATABASE_URL` no está definida, fallan con un mensaje explícito: no se omiten.

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

## Verificación de un único head de Alembic

Desde `backend/`, sin conexión a PostgreSQL:

```bash
uv run python scripts/check_single_head.py
```

El comando imprime los heads y termina con código 0 solo si existe exactamente uno; las historias con dos heads se rechazan.

## Configuración del backend

`app.core.config.Settings` exige `DATABASE_URL`, `JWT_SECRET_KEY` y `APP_ENV` (`development`, `test` o `production`). La clave de firma debe ocupar al menos 32 bytes UTF-8. Los errores de validación nombran el campo sin mostrar valores sensibles.

Los secretos se leen del entorno o de archivos en `/run/secrets` (directorio configurable mediante `SECRETS_DIR`); el entorno tiene prioridad sobre los archivos. `REDIS_URL` es opcional y `APP_TIMEZONE` usa `America/Argentina/Buenos_Aires` por defecto.

`DatabaseSettings` carga únicamente la conexión, sin exigir la clave de firma ni `APP_ENV`: `migration_url` usa `MIGRATIONS_DATABASE_URL` cuando está definida y `DATABASE_URL` en otro caso. Alembic usa esta configuración al ejecutar las migraciones.

## Salud HTTP y logging

La aplicación se crea mediante `app.main:create_app` (`uvicorn --factory`). `GET /api/v1/health` responde `200` con `{"status": "ok"}` sin consultar la base; otros métodos no están habilitados.

Los registros de `app`, `tpi` y Uvicorn usan JSON con fecha UTC y redacción de secretos. `X-Request-ID` se devuelve en la respuesta y se incluye en los registros; se genera uno nuevo cuando falta o no es válido. La imagen del backend usa un usuario no root y el mismo punto de entrada de producción que verifican las pruebas del servidor.

## Frontend mínimo

Desde `frontend/`: `npm ci`, `npm test -- --run`, `npm run typecheck` y `npm run build`. La SPA de React con Vite muestra el nombre del sistema en español; todavía no implementa las pantallas de agenda. El Dockerfile ofrece etapas `dev` y `build`.

Las pruebas de migraciones usan PostgreSQL real y bases descartables propias. C-01 conserva la revisión existente de C-00 y su restricción contra solapamientos; no crea otra raíz ni borra los datos existentes.

## Secretos locales

Ejecutar `scripts/dev_secrets.sh` desde la raíz para crear `secrets/`; una segunda ejecución conserva los archivos existentes. `.env.example` contiene solo configuración no sensible. Copiarla a `.env` si todavía no existe. Los secretos y `.env` no se versionan.
