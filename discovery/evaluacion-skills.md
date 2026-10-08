# Evaluación de skills para el stack y el proyecto

Fecha: 2026-10-08. Método: se leyeron los `SKILL.md` completos (y las referencias que citan) de unas 45 skills, medidas contra los 20 changes de `CHANGES.md` y contra las decisiones ya tomadas (PyJWT con Argon2, barrido en lugar de Celery, SPA con Vite, Strict TDD). Las instalaciones de skills.sh se tomaron solo como referencia, porque no miden el ajuste al proyecto. [V] indica que se verificó en la fuente.

## Veredicto final

### Instalar (6 nuevas)

| Skill | Fuente | Por qué | Aviso |
|---|---|---|---|
| `supabase-postgres-best-practices` | supabase/agent-skills | Reglas de bloqueos (`SKIP LOCKED`, candados), restricciones y tipos (`timestamptz`). Índice liviano de 64 líneas. | Ignorar las reglas de RLS con `auth.uid()`. No trata `EXCLUDE` ni `btree_gist`. |
| `postgresql-table-design` | wshobson/agents | Única que nombra el patrón `EXCLUDE USING gist (... WITH =, periodo WITH &&)` con `tstzrange` y `[)`. | No advierte que `btree_gist` hace falta para el `=` escalar. |
| `security-best-practices` | openai/skills | Guías específicas de React/TypeScript y de FastAPI: tokens fuera de `localStorage`, CSRF con cookies, CORS explícito, JWT con lista blanca de algoritmos. | Prefiere `SameSite=Lax`, que choca con la decisión abierta Q-28. |
| `docker-build-strategies` | docker/skills | Oficial de Docker: multi-stage, caché BuildKit, secretos de build, usuario no root. | El asset de Python usa `requirements.txt`; se adapta a `pyproject`. |
| `accessibility` | addyosmani/web-quality-skills | WCAG 2.2 AA concreto para la página pública de reserva. | Ejemplos con `lang="en"`; usar `es-AR`. |
| `typescript-react-reviewer` | dotneet | Trampas de React 19 y `noUncheckedIndexedAccess`. | Sugiere TanStack Query y Zustand, que no se eligieron. |

### Ya instaladas: conservar con aclaraciones

- `fastapi` (oficial): ignorar su regla que prefiere SQLModel (`SKILL.md:284`).
- `sqlalchemy`: su ruta principal es síncrona; el proyecto usa `asyncpg`. Sirve la nota de `expire_on_commit=False`.
- `alembic`: ignorar el paso de SQLite y `render_as_batch=True`. No menciona `EXCLUDE`.
- `python-testing-patterns`: sus ejemplos usan SQLite en memoria; el proyecto prueba contra PostgreSQL real.
- `vitest`, `react-testing` y `docker-compose-patterns`: sin conflictos relevantes.

### Quitar (3 instaladas)

- `tdd` (mattpocock): dice que el refactor no es parte del ciclo y exige confirmar los puntos de test con el usuario, lo que contradice el ciclo RED, GREEN, TRIANGULATE y REFACTOR del proyecto.
- `vercel-react-best-practices`: 19 de sus 70 reglas son de Next.js o componentes de servidor, y se dispara con cualquier componente React.
- `sql-job-queue`: 378 líneas para una cola con latidos y reparto equitativo, cuando C-15 es un barrido idempotente. Se puede abrir a mano para el paso de idempotencia.

### Opcionales o condicionales

- `security-and-hardening` (addyosmani) y `security-fastapi` (igorwarzocha): solapan con `security-best-practices`.
- `playwright-best-practices`: solo si se adopta Playwright, en C-20.
- `wrangler` (cloudflare/skills): solo si el disparador cron va en un Worker.
- `tanstack-query-best-practices`: solo si se decide TanStack Query.

### Descartadas con evidencia

- `access-control-rbac` (aj-geddes): su motor ABAC llama a `datetime.now()` dentro de la política y trae una regla de acceso total para el administrador, lo que contradice KB 11 y C-04.
- `auth-implementation-patterns` (wshobson): su contenido es JavaScript (`jsonwebtoken`, bcrypt de Node).
- `fastapi-templates`, `fastapi-patterns`, `fastapi-expert` y la `fastapi` de martinholovsky: enseñan `python-jose` con `passlib` y bcrypt, pruebas con SQLite y Pydantic v1.
- `python-background-jobs` (Celery), `python-resilience`, `redis-patterns`, `redis-connections`, `database-migration(s)`, `docker-patterns`, `neon-postgres`, `gdpr-data-handling` y otras: fuera del alcance verificado.

## Hallazgos técnicos que cambian el diseño

1. **Neon con pooler:** no soporta candados de sesión (`pg_try_advisory_lock`), `SET` ni `LISTEN/NOTIFY` [V]. El barrido de C-15 debe usar `pg_try_advisory_xact_lock` dentro de la transacción, o la conexión directa. Las migraciones y `pg_dump` van por la URL directa.
2. **asyncpg detrás de PgBouncer:** SQLAlchemy recomienda `prepared_statement_cache_size=0` o un `prepared_statement_name_func` único con `NullPool` [V].
3. **GitHub Actions como disparador:** intervalo mínimo de 5 minutos, puede demorarse y se desactiva tras 60 días sin actividad en repos públicos [V].
4. **Cloudflare Pages:** la guía oficial dice "Start new projects with Workers" y Workers con Static Assets admite el fallback de SPA con `not_found_handling` [V].

## Vacíos sin skill adecuada

Restricción de exclusión con `btree_gist`, `23P01` y pruebas de concurrencia; ABAC con funciones puras sobre los cuatro atributos; zona horaria y reloj inyectable; SMTP con `aiosmtplib`; PyJWT con pwdlib (solo en el tutorial oficial de FastAPI); Ley 25.326; cálculo de disponibilidad de agenda; UI de calendario y selector de fechas accesible; texto de interfaz en español de Argentina. Para el resto se usa Context7.

## Propuesta: skills propias del proyecto

Derivadas de la KB, densas y alineadas con las decisiones, algo que ninguna externa logra:

1. `turnos-abac`, desde KB 11: matriz rol, acción y atributo, firmas de política, códigos HTTP de rechazo, reloj inyectado y casos de prueba por atributo (C-04, C-07, C-08, C-10, C-19).
2. `postgres-turnos`: DDL de exclusión con `btree_gist` y `tstzrange '[)'`, traducción de `23P01`, candado `xact`, pooler y conexión directa en Neon, y configuración de asyncpg (C-02, C-07, C-15, C-20).
3. Opcional: `pg-test-harness`, con PostgreSQL real en contenedor y reloj simulado.
