# Proposal

## Why

Recepción necesita preparar avisos por WhatsApp sin redactarlos ni exponer información clínica. El sistema ya programa correos y conserva el ciclo del turno, pero aún no prepara ni permite gestionar esos mensajes manuales.

## What Changes

- Normalizar teléfonos internacionales con Argentina como país predeterminado y generar mensajes mínimos y enlaces `wa.me` codificados.
- Preparar una notificación WhatsApp para los hitos y avisos de liberación y cambios del personal, con idempotencia y vigencia por ciclo.
- Incorporar filtro por canal a la bandeja existente y operaciones autorizadas para obtener un enlace y marcar el envío manual.
- Conservar separación entre preparación, apertura y envío manual: el sistema no verifica entrega.
- Mantener correos, decisiones de liberación RN-60 y aislamiento por consultorio; la interfaz corresponde a C-18 y la API oficial de WhatsApp queda fuera de alcance.

## Capabilities

### New Capabilities

- `whatsapp-manual-notifications`: preparación, enlace y registro manual de avisos WhatsApp por turno.

### Modified Capabilities

- `notification-operations`: filtro adicional por canal en la bandeja existente, preservando su proyección mínima y compatibilidad.

## Impact

Backend de notificaciones, barrido, avisos de turno, políticas y esquemas HTTP; pruebas unitarias y contra PostgreSQL real. C-16 archivado es dependencia. No se incorpora interfaz ni envío automático externo. Gobierno MEDIO según C-17; mantener control de acceso existente y no ampliar privilegios.
