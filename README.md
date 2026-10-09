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

Queda fuera de la v1 (backlog): auditoría y consentimiento de datos conforme a la Ley 25.326, lista de espera, seña por Mercado Pago, recall automático, API oficial de WhatsApp, facturación ARCA y obras sociales, odontograma y presupuestos, e importación desde planilla. El detalle está en [`knowledge-base/06_funcionalidades.md`](knowledge-base/06_funcionalidades.md).

## Estado del proyecto

- **Entrega del MVP completo:** 2026-10-19.
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

Las skills del proyecto están versionadas en [`.claude/skills/`](.claude/skills/), con su `SKILL.md` completo, para que queden en el repositorio remoto. El mapa de qué skill carga cada rol de agente está en [`AGENTS.md`](AGENTS.md).

**Skills de la fundación (Active-Stack)**, usadas para armar el proyecto:

| Skill | Fuente | Uso |
|-------|--------|-----|
| `active-orchestrator` | Group-Active-IA/active-orchestrator | Orquesta las fases de la fundación |
| `discovery-research` | Group-Active-IA/discovery-research | Descubrimiento de producto y de mercado |
| `kb-creator` | Group-Active-IA/kb-creator | Base de conocimiento de 13 archivos |
| `roadmap-generator` | Group-Active-IA/roadmap-generator | `CHANGES.md` con los 20 changes |
| `find-skill` | vercel-labs/skills | Búsqueda de skills para el stack |
| `skill-registry` | JuanCruzRobledo/skill-registry | Registro de skills con sus reglas compactas |
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
├── knowledge-base/              Fuente de verdad del dominio (13 archivos)
├── discovery/                   Descubrimiento de producto, análisis de mercado y exploración técnica
├── openspec/                    Changes de SDD (propuestas, especificaciones, diseño y tareas)
└── .claude/
    ├── skills/                  23 skills del proyecto, versionadas
    └── commands/                Comandos de OpenSpec (/opsx:*)
```

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [`knowledge-base/README.md`](knowledge-base/README.md) | Índice de la base de conocimiento y convenciones de códigos (`RN-NN`, `US-NNN`, `DD-NN`, `SU-NN`, `Q-NN`) |
| [`knowledge-base/01_vision_y_objetivos.md`](knowledge-base/01_vision_y_objetivos.md) | Propósito, alcance y casos de uso |
| [`knowledge-base/05_reglas_de_negocio.md`](knowledge-base/05_reglas_de_negocio.md) | Reglas de negocio RN-01 a RN-58 |
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
