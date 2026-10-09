# Sistema de Turnos y Agenda Odontológica — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

Sistema web para que un consultorio odontológico de 2 a 5 profesionales reduzca las ausencias, automatice la confirmación de turnos y controle los sobreturnos. Entrega del MVP completo: **2026-10-19**.

---

## Stack Tecnológico

Stack obligatorio (restricción del proyecto). Las versiones se fijan al crear el proyecto, en los archivos de dependencias.

| Capa | Tecnologías | Observaciones |
|------|-------------|---------------|
| Frontend | React, TypeScript, Vite | SPA. Idioma de la interfaz: español (Argentina). |
| Backend | Python, FastAPI | API REST. Documentación OpenAPI generada por FastAPI. |
| Autenticación | JWT (PyJWT, HS256) y pwdlib con Argon2 | Los claims incluyen el rol (también `paciente`) y `consultorio_id`. |
| ORM | SQLAlchemy 2.x asíncrono (asyncpg) | Acceso a datos mediante repositorios. Migraciones con Alembic. |
| Base de datos | PostgreSQL (Neon en producción) | Restricción de exclusión para impedir solapamientos. |
| Trabajos programados | Barrido idempotente dentro de la API, con candado en PostgreSQL | Recordatorios, liberación automática y envío de correo. Un disparador HTTP externo lo activa cada 5 minutos. Redis es opcional. |
| Contenedores | Docker, Docker Compose | Entorno local; el despliegue usa servicios gratuitos. |
| Correo | SMTP de una cuenta existente (`aiosmtplib`) | Confirmaciones y recordatorios. |
| Presupuesto | Cero | Solo servicios gratuitos o con plan gratuito. |

Detalle completo: [knowledge-base/02_descripcion_general.md](knowledge-base/02_descripcion_general.md)

---

## Base de Conocimiento

La fuente de verdad del dominio vive en `knowledge-base/`. **Leé el archivo relevante ANTES de implementar.**

| Archivo | Cuándo leerlo |
|---------|---------------|
| [README.md](knowledge-base/README.md) | Índice, convenciones de códigos (`RN-NN`, `US-NNN`, `DD-NN`, `SU-NN`, `Q-NN`) y resumen ejecutivo |
| [01_vision_y_objetivos.md](knowledge-base/01_vision_y_objetivos.md) | Entender propósito y alcance |
| [02_descripcion_general.md](knowledge-base/02_descripcion_general.md) | Stack, arquitectura general, integraciones y API REST |
| [03_actores_y_roles.md](knowledge-base/03_actores_y_roles.md) | Auth, RBAC, permisos |
| [04_modelo_de_datos.md](knowledge-base/04_modelo_de_datos.md) | Entidades, ERD, migraciones |
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-01 a RN-58) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, trabajos en segundo plano, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones confirmadas (DD), supuestos sin confirmar (SU) y riesgos |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Preguntas abiertas a resolver ANTES de codear lo que bloquean |
| [11_politicas_de_acceso_abac.md](knowledge-base/11_politicas_de_acceso_abac.md) | Cuatro atributos ABAC y matriz rol × acción × atributo |
| [12_devops_y_despliegue.md](knowledge-base/12_devops_y_despliegue.md) | Compose, hosting gratuito, SMTP, disparador del barrido |

> ⚠️ Las preguntas de prioridad **Alta** de `10_preguntas_abiertas.md` se resuelven antes del change que bloquean: Q-01 (qué recortar si no hay plazo) y Q-03 a Q-06 afectan a la rebanada vertical (C-05 a C-10); Q-23 a Q-25 afectan a C-05, C-15 y C-20; Q-28 afecta a C-03, C-11 y C-20. Las suposiciones `SU-NN` no están confirmadas: tratarlas como hipótesis.

---

## Skills Disponibles

Fuente de verdad: `.atl/skill-registry.md` (generado por `skill-registry`). Esta tabla solo mapea skill → rol.

| Agente | Rol | Skills que carga |
|--------|-----|------------------|
| **Backend Core** | FastAPI, SQLAlchemy asíncrono, repositorios, casos de uso | `fastapi`, `sqlalchemy`, `python-testing-patterns` |
| **Datos y Migraciones** | Esquema PostgreSQL, restricción de exclusión, Alembic | `postgresql-table-design`, `supabase-postgres-best-practices`, `alembic` |
| **Backend Seguridad y Jobs** | Auth, JWT, ABAC, barrido idempotente | `security-best-practices` (solo ante pedido explícito de seguridad), `sql-job-queue` (solo referencia de idempotencia para C-15) |
| **Frontend** | React, TypeScript, Vite, pruebas de componentes, accesibilidad | `vercel-react-best-practices`, `typescript-react-reviewer`, `vitest`, `react-testing`, `accessibility` |
| **Infraestructura** | Docker, Compose, despliegue gratuito | `docker-compose-patterns`, `docker-build-strategies` |
| **Pruebas / TDD** | Ciclo de TDD estricto | `tdd` (cede ante el ciclo de TDD estricto del orquestador) |
| **Orquestación** | Fundación, SDD / OPSX, commits | `kb-creator`, `roadmap-generator`, `skill-registry`, `work-unit-commits`, `chained-pr` |

Cargá la skill correspondiente al contexto ANTES de escribir código. La columna **Ignore / Conflict** del registro **manda sobre el `SKILL.md`**: por ejemplo, `fastapi` ignora su preferencia por SQLModel, y `alembic` ignora el modo batch de SQLite.

Huecos sin skill madura (usar el MCP de Context7 y [la KB 11](knowledge-base/11_politicas_de_acceso_abac.md)): restricción de exclusión con `btree_gist` y `23P01`, ABAC con funciones puras, reloj inyectado y zona horaria, `aiosmtplib`, PyJWT con pwdlib, Ley 25.326 y cálculo de disponibilidad de agenda.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry`; no versionado — no está en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Total**: 20 changes (`C-01` a `C-20`) en 7 fases.
- **Camino crítico** (10): `C-01 → C-02 → C-03 → C-06 → C-07 → C-09 → C-16 → C-17 → C-18 → C-20`, con margen acotado hasta la entrega.
- **Primer change**: `C-01` (`foundation-setup`).
- **Rebanada vertical primero**: autenticación y roles (C-03 a C-05), horarios (C-06), agenda sin solapamientos (C-07) y reserva pública (C-09). Después recordatorios y liberación (C-15 a C-18), indicador de ausentismo (C-19) y cierre con despliegue (C-20).
- **Si el plazo aprieta**: el orden de recortes está en la sección correspondiente de `CHANGES.md`; la decisión es del Product Owner (Q-01).

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD estricto, Engram, CodeGraph, commits convencionales sin co-autoría de IA, herramientas `bat`/`rg`/`fd`/`sd`): el proyecto las **hereda**, no se repiten acá.

Reglas específicas de este proyecto, confirmadas con el usuario. Son contrato; romperlas es un defecto.

1. NUNCA tomar `consultorio_id` del cliente → leerlo siempre del `Principal` del token (RN-55).
2. NUNCA escribir código de producción sin un test que falle antes → ciclo RED, GREEN, TRIANGULATE, REFACTOR, con tests de comportamiento (RN-NN y US-NNN).
3. NUNCA mockear la base en tests de repositorios ni de restricciones → PostgreSQL real en contenedor, no SQLite.
4. NUNCA usar `datetime.now()` ni `utcnow()` en dominio o políticas → el puerto `Reloj`, `timestamptz` y zona `America/Argentina/Buenos_Aires`.
5. NUNCA usar `python-jose`, `passlib` ni `bcrypt` → PyJWT (HS256) y pwdlib con Argon2.
6. NUNCA autorizar ad hoc dentro de un router → RBAC como dependencias y ABAC como funciones puras con el reloj inyectado ([KB 11](knowledge-base/11_politicas_de_acceso_abac.md)).
7. NUNCA confiar en el autogenerate para la restricción anti-solapamiento → crearla a mano tras `CREATE EXTENSION IF NOT EXISTS btree_gist`, con un test de dos turnos solapados, y traducir `23P01` a "horario ocupado".
8. NUNCA dejar más de un head de Alembic → rebasar antes de archivar y usar `alembic upgrade head`, nunca `heads`.
9. NUNCA crear un worker persistente ni usar Celery → barrido idempotente en la API con `pg_try_advisory_xact_lock` o `SELECT ... FOR UPDATE SKIP LOCKED`; nunca candados de sesión (no funcionan en el pooler de Neon); Redis solo opcional.
10. NUNCA compartir una `AsyncSession` entre tareas → una sesión por solicitud, `expire_on_commit=False`, y detrás de un pooler `prepared_statement_cache_size=0` o `NullPool`.
11. NUNCA aceptar un esquema Pydantic de entrada sin `extra='forbid'` → rechazar los campos no declarados.
12. NUNCA usar `any` en TypeScript → tipado estricto, componentes en PascalCase con contenedor, presentacional y átomos (SU-04).
13. NUNCA registrar ni devolver DNI, contacto u obra social sin necesidad → minimizar y enmascarar en logs y respuestas (Ley 25.326).
14. NUNCA sumar dependencias o servicios con costo, ni funciones del backlog dentro de un change de la v1 → presupuesto cero y solo lo que define `CHANGES.md`.

---

## Flujo de Trabajo

```
1. Leer la KB relevante (knowledge-base/)        → entender el dominio
2. Identificar el change en CHANGES.md           → respetar dependencias
3. /opsx:propose C-NN-nombre                     → proposal + design + specs + tasks
4. Implementar las tasks (cargando skills)       → respetando las reglas duras
5. /opsx:archive C-NN-nombre + marcar [x]        → cerrar el change
```

Aplicar TODAS las reglas duras en cada paso. Ante conflicto entre la KB y este archivo, las reglas duras prevalecen.
