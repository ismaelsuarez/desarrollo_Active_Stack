# Tasks

## 1. Persistence and seed

- [x] 1.1 Add models and one reversible Alembic revision for boxes, professionals, weekly blocks, exceptions and services; verify checks, tenant-scoped uniqueness, upgrade/downgrade/re-upgrade and one head on PostgreSQL.
- [x] 1.2 Extend seed to create the nine suggested services only for an empty catalog; verify fresh seed, rerun, and preservation of a customized or deactivated service.

## 2. Staff and agenda API

- [x] 2.1 Implement staff create/list/update/deactivate and professional association; verify role allowlist, patient-role rejection, tenant isolation, Administrator-only writes and preserved history with API and PostgreSQL tests.
- [x] 2.2 Implement boxes and professionals management; verify one box per professional, one professional per account, same-consultorio references, and deactivation without deletion.
- [x] 2.3 Implement weekly schedule read and replacement; verify multiple blocks per day, valid ISO weekdays, half-open adjacency, overlap rejection, and atomic preservation of the prior schedule against PostgreSQL.
- [x] 2.4 Implement exception create/list/delete with local timezone conversion; verify global and professional scope, interval/type validation, cross-tenant rejection, and affected-active-turn response without writing when appointments overlap.

## 3. Service catalog and clinic settings

- [x] 3.1 Implement service list/create/update/deactivate; verify positive duration and tenant-scoped unique name, and that edits do not alter stored appointment duration.
- [x] 3.2 Implement clinic configuration read/update; verify Administrator-only writes, extra-field rejection, and API validation matching PostgreSQL checks for hours, release mode, phone, grid, anticipation and active-booking limits.

## 4. Integration and documentation

- [x] 4.1 Verify all new routes derive consultorio from Principal, use strict schemas, and document statuses and error responses in OpenAPI; run API and authorization tests for every route.
- [x] 4.2 Run migration/seed tests and the complete backend suite on PostgreSQL; run OpenAPI/schema validation, `alembic heads` and `git diff --check`; record the test totals and update README with setup and the suggested nature of initial durations.
