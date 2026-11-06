# Tareas

## 1. Persistencia y creación atómica

- [x] 1.1 Crear modelo, migración y repositorio de autorización por consultorio con unicidad por turno y estados válidos; probar upgrade/downgrade, unicidad y aislamiento en PostgreSQL real.
- [x] 1.2 Implementar alta explícita de sobreturno con motivo y autorización, roles permitidos, validación de grilla, horario, bloqueos y solapamiento activo; probar 201, 403, 422 y bordes contiguos o estados finales.
- [x] 1.3 Integrar historial, hitos y avisos en la misma transacción; probar rollback ante fallo en autorización, historial y planificadores y coexistencia con exclusión de PostgreSQL.

## 2. Respuesta y lecturas

- [x] 2.1 Implementar respuesta aprobado/rechazado del profesional o administrador con agenda propia mediante ABAC; probar roles, agenda ajena, consultorio ajeno y que el estado del turno no cambia.
- [x] 2.2 Mostrar autorización y respuesta en lecturas de personal autorizadas, sin campos internos para pacientes; probar agenda, detalle y aislamiento.

## 3. Integración

- [x] 3.1 Ejecutar pruebas relevantes y suite completa disponible, validación OpenSpec estricta y único head Alembic; registrar evidencia TDD y limitaciones reales. Ver [evidencia](evidence.md).

## Workflow follow-up

- Revisar y archivar el change tras completar y verificar las tareas.
