# Diseño

## Context

La reserva existente `GestionTurnos.crear` valida referencias, duración, grilla y bloqueos; guarda turno e historial y planifica hitos y avisos dentro de `UnidadDeTrabajoSQL`. `hay_solapamiento` ya consulta los estados ocupantes por consultorio y profesional. La exclusión PostgreSQL excluye `es_sobreturno`, pero `NuevoTurno` y su repositorio todavía no permiten fijar esa marca. Las lecturas de `ConsultarTurnos` ya separan acceso por rol y devuelven la marca. Ver propuesta y spec para alcance y aceptación.

## Goals / Non-Goals

**Goals:** conservar reglas de creación y transacción vigentes, agregar trazabilidad del aviso y respuesta con aislamiento por consultorio, y permitir lectura operativa sin filtrar información interna al paciente.

**Non-Goals:** interfaz de personal, correo al profesional, veto, límites nuevos ni modificar la restricción de exclusión.

## Decisions

1. Extender la creación existente con un camino explícito de sobreturno que reutilice validaciones, historial, hitos y avisos y exija un solapamiento activo; no invocar la reserva regular en una segunda transacción. Alternativa: duplicar la creación; se descarta por riesgo de divergencia en RN-29 y planificación.
2. Una tabla `autorizacion_sobreturno` con clave única por turno registra actor, instante, motivo, instante del aviso y respuesta. Se inserta en la misma unidad de trabajo que el turno y los hitos; el aviso es visible en la agenda, no un correo. Alternativa: guardar datos en historial; se descarta porque la respuesta es consultable y actualizable.
3. La respuesta consulta el turno por consultorio, resuelve profesional vinculado y aplica `SOBRETURNO_RESPONDER` existente; actualiza únicamente la autorización, sin tocar estado del turno. Las lecturas de agenda y turno agregan datos internos únicamente al personal autorizado. Alternativa: autorización en router o exponerlos al paciente; incumple las reglas de acceso y minimización.
4. La verificación de intersección utiliza el repositorio existente con intervalos semiabiertos y estados ocupantes. La exclusión parcial no cambia; el riesgo residual de carrera entre reserva regular y sobreturno ya está documentado en RN-17. No se promete serialización adicional que el sistema actual no provee.

## Risks / Trade-offs

- [Cancelación concurrente del turno que justificó la excepción] → documentar y probar la semántica transaccional; la verificación ocurre al crear y no constituye garantía permanente.
- [Datos internos expuestos a pacientes o consultorios ajenos] → filtrar en servidor por rol y consultorio y probar detalle, lista y agenda.
- [Fallo parcial] → una sola unidad de trabajo y pruebas de reversión real con PostgreSQL.
- [Carrera regular/sobreturno] → mantener explícito el riesgo residual existente de RN-17; no modificar la garantía de exclusión de regulares.

## Migration Plan

Agregar migración sobre el head vigente con tabla, restricciones y referencias; comprobar upgrade, downgrade y un único head. El downgrade elimina la tabla y su información de autorizaciones, por lo que requiere respaldo antes de usarse con datos reales.

## UI Mockups

Decision: no (no UI).
