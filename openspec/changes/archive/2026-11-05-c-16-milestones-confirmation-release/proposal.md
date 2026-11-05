# Proposal

## Why

C-15 dejó operativo el despacho durable, pero las reservas todavía usan `PlanificadorSinEfectos`: no programan solicitudes ni recordatorios y el barrido no libera ni marca turnos. C-16 completa ese ciclo para reducir ausencias sin liberar automáticamente a quien no recibió una solicitud de confirmación de su ciclo actual (RN-25 a RN-32, RN-60).

## What Changes

- Programar hitos email desde el inicio y los parámetros del consultorio, dentro de la transacción de reserva/reprogramación; conservar la confirmación anticipada de RN-29 y omitir comunicaciones que dejaron de corresponder.
- Emitir enlaces de confirmación de un solo uso, ligados a turno y ciclo, y aceptar `POST /api/v1/turnos/confirmar-por-enlace` sin sesión. El consultorio sale del token; el enlace solo confirma.
- Evaluar T-12 h en el barrido existente: liberar únicamente pendientes futuros sin marca cuya solicitud email del ciclo actual esté `enviada`; en los otros casos marcar para Recepción una sola vez por ciclo. Estado, historial y aviso se confirman juntos.
- Incorporar `GET /api/v1/turnos?sin_confirmar=true`, conservando los contratos y acciones existentes sin el filtro.
- Programar resumen de reserva y cancelación por el paciente; conservar su contenido histórico y la vigencia de los avisos de hechos consumados.
- Proponer soporte explícito para enlaces de pacientes sin cuenta: permitir `token_usuario.usuario_id` nulo solo para confirmación de turno, con restricciones por tipo. `token_usuario.ciclo` ya existe desde la revisión 0002: no se agrega otra vez.

## Capabilities

### New Capabilities

- `appointment-confirmation`: programación temporal, confirmación por enlace, recordatorios y decisión automática/manual de turnos sin confirmar.

### Modified Capabilities

- `appointment-lifecycle`: omisión transaccional de hitos anteriores al reprogramar y de hitos del ciclo vigente al cancelar/liberar.
- `appointment-agenda`: consulta exclusiva de pendientes marcados para Recepción/Administrador.
- `notification-dispatch`: ventanas de hitos, contenido dinámico mínimo, registro condicionado de fechas de envío y avisos de reserva/cancelación del paciente.
- `notification-sweep`: integrar la evaluación de liberación en el barrido acotado de C-15.
- `core-data-models`: formalizar tokens por turno/ciclo, incluyendo confirmación sin cuenta y conservación de tokens de cuenta.

## Impact

Backend: `GestionTurnos`, `CicloTurnos`, puertos de hitos/notificaciones y unidad de trabajo, repositorios SQL, `DespacharNotificacion`, `EjecutarBarrido`, composición y routers de turnos. Una revisión Alembic sobre `0009_notifications_outbox_sweep` ajustará la nulabilidad y las restricciones del token; no cambia la exclusión de solapamientos. Pruebas de tiempo con reloj inyectado, PostgreSQL y Mailpit reales para integración/concurrencia.

Sin frontend, preparación de WhatsApp (C-17), proveedores nuevos, worker, Redis obligatorio ni despliegue. Q-07 mantiene el supuesto RN-30; Q-25/Q-27 y SU-38 son riesgos del entorno publicado, no bloqueos del trabajo local (AGENTS.md, DD-22/DD-31). Governance **ALTO**: propuesta y diseño pendientes de revisión humana antes de apply; las decisiones de compatibilidad y discrepancias están detalladas en `design.md`.
