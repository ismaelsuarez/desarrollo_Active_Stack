# Design: C-06 agenda-config

## Context

See `proposal.md` for motivation. C-02/03/05 provide the consultorio, users, authentication and request dependencies. C-05 is archived; Alembic currently has one head, `0006_intento_registro`. Domain time uses the injected `Reloj`, and API schemas reject undeclared fields.

## Goals / Non-Goals

**Goals:** Make agenda configuration the persisted source for later booking and availability changes; preserve tenant isolation, history, and a single migration head.

**Non-Goals:** Create or calculate appointments, expose patient-facing availability, or build management screens. C-07 and C-09 consume the configured schedule later. Feriados are entered manually; Q-13 does not add an external calendar integration.

## Decisions

1. **One Alembic revision after the current head.** Add box, profesional, horario_semanal, bloqueo_agenda, prestación constraints and indexes in a reversible revision. Keep one head and verify on PostgreSQL from an empty database. This avoids creating divergent histories.
2. **Tenant scope comes from Principal.** Repositories and writes receive the authenticated `consultorio_id`; request bodies cannot choose a tenant. Every relevant uniqueness and lookup is tenant scoped. Route authorization uses `requiere_rol("administrador")`.
3. **Weekly blocks use local wall-clock times.** `dia_semana` is ISO weekday 1–7 and `hora_inicio < hora_fin`. Validate same-day overlaps in the application transaction because a weekly interval is not a timestamp range. Compare a replacement before writing and preserve the prior schedule on failure.
4. **Exceptions use zoned instants.** Resolve day boundaries and display/validation with `consultorio.zona_horaria`; persist as timestamptz supplied using the injected clock. A global exception has null `profesional_id`. Before saving, query affected active turns. If any exist, return their identifiers and leave both exception and turns untouched; require resolving those turns before retry. This satisfies RN-16 without adding cancellation behavior to C-06.
5. **Seed only an empty catalog.** Insert the nine source-defined suggested prestations when a consultorio has none. On reruns do not reset, overwrite, or reactivate entries changed by staff. Keep suggested durations visibly provisional in docs/API data; Q-09 remains for professionals to confirm.
6. **Keep layers aligned.** Add SQLAlchemy models, repositories, application services and FastAPI routes with strict Pydantic schemas. The catalog edits affect future appointments; stored appointments retain their copied duration. Validate consultorio settings in API and with the existing PostgreSQL checks.
7. **Strict TDD and real PostgreSQL.** For each behavior, run the focused test red before production code, then green, at least one distinct edge case, and refactor with tests. Repository, constraint, migration and seed checks use the PostgreSQL test container, never SQLite.

## Risks / Trade-offs

- [Suggested durations may not match local practice] → mark them as suggestions and preserve edits; Q-09 is non-blocking.
- [Urgent blocks may need Reception access] → C-06 authorizes Administrator only as scoped in CHANGES; Q-12 remains open and no role expansion is assumed.
- [Adding an exception over booked time interrupts setup] → return the affected appointments without storing the block or changing appointments; C-07 can extend explicit resolution later.
- [Deactivating linked users or professionals could hide historical records] → use active flags, preserve foreign-key references, and test inactive records remain readable where the API contract allows.

## Migration Plan

Apply one descendant revision with `alembic upgrade head`; verify a single head and upgrade/downgrade/re-upgrade on a disposable PostgreSQL database. The seed runs after migration and is safe to repeat. A rollback drops only the new tables/constraints; it must not drop consultorio, user or appointment data. Do not deploy until the migration and seed integration checks pass.

## UI Mockups

Decision: no (no UI). C-06 adds backend API and persistence only; management screens are outside this change.
