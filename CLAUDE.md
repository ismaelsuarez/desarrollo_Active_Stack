# Sistema de Turnos y Agenda Odontológica — Instrucciones para Agentes

> Este archivo (y su copia `CLAUDE.md`) es lo PRIMERO que todo agente lee al entrar al repo.
> Generado a partir de `knowledge-base/` y `CHANGES.md`. No editar a mano sin re-sincronizar ambos archivos.

Sistema web para que un consultorio odontológico de 2 a 5 profesionales reduzca las ausencias, automatice la confirmación de turnos y controle los sobreturnos. Entrega en dos partes (DD-22, DD-33): la primera, el **2026-10-19**, es la del Trabajo de Integración: la fundación, el informe de Discovery y un único change, `crear-turno-sin-solapamientos`, llevado por el ciclo OPSX completo. La segunda parte son los changes C-01 a C-20 y C-21.

---

## Stack Tecnológico

Stack obligatorio (restricción del proyecto). Las versiones se fijan al crear el proyecto, en los archivos de dependencias.

| Capa | Tecnologías | Observaciones |
|------|-------------|---------------|
| Frontend | React, TypeScript, Vite | SPA. Idioma de la interfaz: español (Argentina). |
| Backend | Python, FastAPI | API REST. Documentación OpenAPI generada por FastAPI. |
| Autenticación | JWT (PyJWT, HS256) y pwdlib con Argon2 | Los claims incluyen el rol (también `paciente`) y `consultorio_id`; nunca la ficha ni el identificador del paciente (RN-06). |
| ORM | SQLAlchemy 2.x asíncrono (asyncpg) | Acceso a datos mediante repositorios. Migraciones con Alembic. |
| Base de datos | PostgreSQL (Neon en producción) | Restricción de exclusión para impedir solapamientos. |
| Trabajos programados | Barrido idempotente dentro de la API, con reclamación por fila en PostgreSQL | Recordatorios, liberación automática y envío de correo. Un disparador HTTP externo lo activa cada 5 minutos. Redis es opcional. |
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
| [05_reglas_de_negocio.md](knowledge-base/05_reglas_de_negocio.md) | Reglas codificadas (RN-01 a RN-65) |
| [06_funcionalidades.md](knowledge-base/06_funcionalidades.md) | Historias de usuario por épica |
| [07_flujos_principales.md](knowledge-base/07_flujos_principales.md) | Flujos extremo a extremo |
| [08_arquitectura_propuesta.md](knowledge-base/08_arquitectura_propuesta.md) | Patrones, estructura, trabajos en segundo plano, variables de entorno |
| [09_decisiones_y_supuestos.md](knowledge-base/09_decisiones_y_supuestos.md) | Decisiones confirmadas (DD), supuestos sin confirmar (SU) y riesgos |
| [10_preguntas_abiertas.md](knowledge-base/10_preguntas_abiertas.md) | ⚠️ Preguntas abiertas a resolver ANTES de codear lo que bloquean |
| [11_politicas_de_acceso_abac.md](knowledge-base/11_politicas_de_acceso_abac.md) | Cuatro atributos ABAC y matriz rol × acción × atributo |
| [12_devops_y_despliegue.md](knowledge-base/12_devops_y_despliegue.md) | Compose, hosting gratuito, SMTP, disparador del barrido |
| [13_aviso_de_privacidad_borrador.md](knowledge-base/13_aviso_de_privacidad_borrador.md) | Borrador del aviso de privacidad del registro (RN-65), pendiente de revisión legal |

> ⚠️ **Puerta de las preguntas Alta**: un change no se propone (`/opsx:propose`) mientras tenga abierta una pregunta de prioridad **Alta** de `10_preguntas_abiertas.md` que bloquea su propio alcance; primero se le pregunta al dueño del proyecto y se registra la decisión como `DD-NN`. Al 2026-10-12 ningún change que se construye en local tiene abierta una pregunta Alta que bloquee su propio alcance: Q-03 quedó resuelta por DD-32. Las que siguen abiertas (Q-23 a Q-27 y Q-29) conciernen al entorno publicado (proveedor, host, disparador externo y cuota de Neon) y bloquean solo C-20: en local y en CI PostgreSQL corre como superusuario y `btree_gist` funciona, el correo va a Mailpit, el barrido corre con su bucle propio y nada se aloja, así que C-01, C-05, C-07, C-14, C-15 y C-16 solo las mencionan como riesgo del despliegue y no esperan su respuesta. Las suposiciones `SU-NN` son hipótesis, salvo las que `09_decisiones_y_supuestos.md` marca como confirmadas o reemplazadas por una decisión.

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

Cargá la skill correspondiente al contexto ANTES de escribir código. Las [aclaraciones de uso](#aclaraciones-de-uso-de-las-skills) de más abajo **mandan sobre el `SKILL.md`** cuando se contradicen.

Huecos sin skill madura (usar el MCP de Context7 y [la KB 11](knowledge-base/11_politicas_de_acceso_abac.md)): restricción de exclusión con `btree_gist` y `23P01`, ABAC con funciones puras, reloj inyectado y zona horaria, `aiosmtplib`, PyJWT con pwdlib, Ley 25.326 y cálculo de disponibilidad de agenda.

### Aclaraciones de uso de las skills

Mandan sobre el `SKILL.md`. Viven en este archivo, que está versionado, porque `.atl/skill-registry.md` se regenera automáticamente y las pierde.

| Skill | Ignorar o tener en cuenta |
|-------|---------------------------|
| `fastapi` | Ignorar su preferencia por SQLModel (`SKILL.md:284` y `references/other-tools.md:68-70`): el proyecto usa SQLAlchemy 2.x asíncrono con asyncpg. |
| `sqlalchemy` | Su camino principal es síncrono (psycopg); el proyecto es asíncrono con asyncpg. Mantener `expire_on_commit=False`. Detrás de PgBouncer o del pooler de Neon, usar `prepared_statement_cache_size=0` o `NullPool`. |
| `alembic` | Ignorar el paso de SQLite y `render_as_batch=True`. Inicializar en modo asíncrono (`alembic init -t async`, DD-14) aunque la skill prefiera el síncrono. No cubre `EXCLUDE`: crear la restricción de exclusión a mano tras `CREATE EXTENSION btree_gist`. Ante dos heads la skill propone `alembic merge`: el proyecto no fusiona, rebasa la revisión nueva sobre el head existente (regla dura 8). |
| `sql-job-queue` | Describe otro diseño de cola (378 líneas). Usar solo su paso de idempotencia "al menos una vez" como referencia del barrido de C-15; no cargarla en otros casos. |
| `python-testing-patterns` | Sus ejemplos usan SQLite en memoria y `freezegun`. Las pruebas del proyecto corren contra PostgreSQL real e inyectan el reloj con el puerto `Reloj`. |
| `tdd` | **Conflicto con el TDD estricto**: dice que el refactor no es parte del ciclo y pide confirmar los puntos de prueba con el usuario. Gana el ciclo RED, GREEN, TRIANGULATE, REFACTOR del orquestador. |
| `docker-compose-patterns` | Prefiere `compose.yaml`; el proyecto usa `docker-compose.yml` y manda el proyecto. |
| `vercel-react-best-practices` | 19 de sus 70 reglas son de Next.js o de componentes de servidor: ignorar las reglas `server-*` (SPA con Vite). |
| `supabase-postgres-best-practices` | Ignorar las reglas de RLS con `auth.uid()`. Su regla de advisory locks enseña candados de sesión: en el pooler de Neon no usarlos; el proyecto usa la reclamación por fila con `FOR UPDATE SKIP LOCKED` (regla dura 9). |
| `postgresql-table-design` | No dice que `btree_gist` hace falta para el `=` escalar en restricciones de exclusión GiST: agregarlo a mano (ver `alembic`). |
| `security-best-practices` | Prefiere `SameSite=Lax`; el proyecto usa `SameSite=Strict` para la cookie de renovación porque el frontend y la API comparten origen (DD-26), y manda el proyecto. Usarla solo ante un pedido explícito de seguridad. |
| `accessibility` | Sus ejemplos usan `lang="en"`; el idioma de la interfaz es `es-AR`. |

Sin aclaraciones: `docker-build-strategies`, `vitest`, `react-testing` y `typescript-react-reviewer`.

> Los compact rules de cada skill los resuelve el orquestador desde `.atl/skill-registry.md` (generado por `skill-registry` y versionado en el repo). Esta tabla solo mapea skill→rol.

---

## Roadmap de Changes

El plan de implementación completo está en [CHANGES.md](CHANGES.md). Resumen:

- **Primera entrega**: un único change, `C-00` (`crear-turno-sin-solapamientos`), con el ciclo OPSX completo (DD-33).
- **Segunda parte**: 20 changes (`C-01` a `C-20`) en 7 fases, más `C-21` (derechos de la Ley 25.326, DD-28).
- **Camino crítico** (10): `C-01 → C-02 → C-03 → C-06 → C-07 → C-09 → C-16 → C-17 → C-18 → C-20`. Ordena las dependencias; no es un compromiso de fecha (DD-22).
- **Orden de construcción de la segunda parte (DD-31)**: C-01, C-02, C-03; C-04, C-05 y C-06; C-07; C-08 y C-09; C-15 y C-16; C-11 y C-14; C-10 y C-13; y después, si alcanza el tiempo, C-12, C-17, C-18, C-19 y C-20.
- **Primer change**: `C-00` (`crear-turno-sin-solapamientos`). `C-01` (`foundation-setup`) es el primero de la segunda parte.
- **Qué va primero**: autenticación y roles (C-03 a C-05), horarios (C-06), agenda sin solapamientos (C-07) y reserva pública (C-09); enseguida recordatorios y liberación automática (C-15, C-16), que son el motivo del proyecto; después las pantallas (C-11, C-14, C-10, C-13) y, si alcanza el tiempo, el resto.
- **Flujo de trabajo**: Spec-Driven Development con OpenSpec (ciclo OPSX: explore, propose, apply, verify, archive). No se agregan al repositorio otros flujos ni artefactos de proceso.

**Antes de cualquier `/opsx:propose`**: leé [CHANGES.md](CHANGES.md), identificá las dependencias del change y los archivos de "Leer antes".

---

## Reglas Duras

> Reglas **globales** ya definidas en `~/.claude/CLAUDE.md` (orquestador, governance, TDD estricto, Engram, CodeGraph, commits convencionales sin co-autoría de IA, herramientas `bat`/`rg`/`fd`/`sd`): el proyecto las **hereda**, no se repiten acá.

Reglas específicas de este proyecto, confirmadas con el usuario. Son contrato; romperlas es un defecto.

1. NUNCA tomar `consultorio_id` del cliente → leerlo del `Principal` del token cuando hay token. Sin token la regla es por tipo de flujo: una ruta que recibe un token enviado por correo o de renovación (verificación de correo, restablecimiento de contraseña, `POST /turnos/confirmar-por-enlace`, `/auth/refresh`) lo toma de la fila a la que apunta el token; las demás (`/auth/login`, `/auth/registro`, reenvío de verificación, recuperación de contraseña y las lecturas `/publico/*`) lo resuelve el servidor desde su configuración (`CONSULTORIO_ACTIVO_ID`, variable obligatoria) con una única dependencia (RN-55, RN-59).
2. NUNCA escribir código de producción sin un test que falle antes → ciclo RED, GREEN, TRIANGULATE, REFACTOR, con tests de comportamiento (RN-NN y US-NNN).
3. NUNCA mockear la base en tests de repositorios ni de restricciones → PostgreSQL real en contenedor, no SQLite.
4. NUNCA usar `datetime.now()` ni `utcnow()` en dominio o políticas → el puerto `Reloj`, `timestamptz` y zona `America/Argentina/Buenos_Aires`.
5. NUNCA usar `python-jose`, `passlib` ni `bcrypt` → PyJWT (HS256) y pwdlib con Argon2.
6. NUNCA autorizar ad hoc dentro de un router → RBAC como dependencias y ABAC como funciones puras con el reloj inyectado ([KB 11](knowledge-base/11_politicas_de_acceso_abac.md)).
7. NUNCA confiar en el autogenerate para la restricción anti-solapamiento → crearla a mano tras `CREATE EXTENSION IF NOT EXISTS btree_gist`, con un test de dos turnos solapados, y traducir `23P01` a "horario ocupado".
8. NUNCA dejar más de un head de Alembic → rebasar antes de archivar y usar `alembic upgrade head`, nunca `heads`.
9. NUNCA crear un worker persistente ni usar Celery → barrido idempotente en la API con reclamación por fila (`SELECT ... FOR UPDATE SKIP LOCKED`, estado intermedio `enviando` y envío fuera de la transacción; resultado escrito solo si la fila sigue `enviando` con la reclamación propia; entrega al menos una vez, RN-61); nunca candados de sesión como `pg_try_advisory_lock` (no funcionan en el pooler de Neon) ni un candado global del barrido; Redis solo opcional.
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
