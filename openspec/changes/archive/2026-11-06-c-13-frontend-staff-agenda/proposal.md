# Propuesta

## Why

Recepción y profesionales necesitan operar la agenda y las fichas desde la aplicación, con los permisos y reglas ya implementados en la API. Actualmente las rutas del personal son espacios reservados y no ofrecen esos recorridos.

## What Changes

- Agenda diaria por profesional, estados y sobreturnos, con vista propia del profesional y filtro de agenda propia del administrador cuando corresponda.
- Alta, movimiento, confirmación, cancelación y marcado de turnos; alta de ficha en el contexto del turno; autorización y respuesta a sobreturnos.
- Búsqueda, detalle y edición de fichas, historial y gestión de solicitudes de vinculación, desvinculación y reactivación según rol.
- Estados de espera, vacío, errores y conflictos, con control por las acciones que devuelve el servidor.
- Extensión mínima de lectura autenticada para identificar la agenda propia y devolver acciones operativas calculadas por el servidor. Sin cambios en autorización efectiva, reglas de negocio ni despliegue; sin pantalla operativa para el rol Administrativo.

## Capabilities

### New Capabilities

- `frontend-staff-agenda`: agenda diaria, gestión de turnos y respuesta a sobreturnos por el personal.
- `frontend-patient-records`: consulta y gestión de fichas y solicitudes de vinculación desde el frontend.
- `staff-agenda-context`: identificación de la agenda propia y acciones operativas autorizadas para la interfaz.

### Modified Capabilities

Ninguna; las capacidades backend y de sesión mantienen sus contratos.

## Impact

SPA React y cliente HTTP, rutas protegidas, lecturas backend y pruebas. Consume endpoints existentes de agenda, turnos, sobreturnos, pacientes y solicitudes; amplía lecturas para identidad y acciones. No requiere migración ni nueva dependencia obligatoria. Usa el sistema visual aprobado revisión 2 y mockups por revisar antes de aplicar.
