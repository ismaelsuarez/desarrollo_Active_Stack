# Propuesta: reserva pública y mis turnos

## Why

El backend ya permite consultar disponibilidad y gestionar turnos propios, pero el paciente todavía no dispone de una interfaz para hacerlo. C-14 completa esa rebanada sobre la sesión y las pantallas de cuenta de C-11.

## What Changes

- Permitir consultar consultorio, prestaciones, profesionales y horarios sin sesión, y conducir a ingreso o registro antes de reservar.
- Permitir a pacientes habilitados reservar y consultar, confirmar, cancelar o reprogramar sus turnos; mostrar acciones según la respuesta de la API y teléfono cuando corresponda.
- Presentar conflictos con alternativas, ausencia de ficha, límites, errores y estados de espera sin repetir automáticamente escrituras inciertas.
- Diseñar vistas adaptables y accesibles para celular y escritorio con el sistema visual aprobado y mockups sujetos a aprobación.
- Mantener la API como autoridad de identidad, permisos, plazos, zona horaria y disponibilidad; no incorporar datos clínicos ni cambios de esquema.

## Capabilities

### New Capabilities

- `frontend-patient-booking`: consulta pública, reserva y autogestión de turnos desde la interfaz de paciente.

### Modified Capabilities

Ninguna: las capacidades existentes del backend y de sesión se consumen sin alterar sus contratos.

## Impact

Frontend React y sus pruebas; rutas públicas y de paciente; clientes de `/api/v1/publico/*` y `/api/v1/turnos`. Depende de C-09 y C-11 archivados. No incluye despliegue ni cambios en la autorización efectiva de la API. El alcance visual requiere revisión de mockups antes de aplicar.
