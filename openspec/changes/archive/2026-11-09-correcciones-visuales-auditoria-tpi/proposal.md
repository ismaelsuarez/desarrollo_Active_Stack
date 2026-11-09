# Proposal

## Why

La auditoría identificó mensajes engañosos y estados incompletos de carga, error y accesibilidad que dificultan la demostración y el uso de la aplicación.

## What Changes

- Mostrar búsqueda activa, reintento de catálogos y turnos propios aun si faltan datos complementarios (F-02 a F-04).
- Gestionar el foco al navegar, distinguir errores inciertos al restablecer contraseña y usar la fecha del consultorio en el indicador (F-05 a F-07).
- Corregir mensajes de bienvenida y WhatsApp (F-08 y F-10).
- Revisar los estados visuales en móvil y escritorio antes de implementarlos. La landing queda fuera de este cambio.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `frontend-patient-booking`: estados de carga, recuperación y disponibilidad parcial.
- `frontend-account-flows`: resultado incierto al restablecer la contraseña.
- `frontend-session-shell`: foco al navegar y bienvenida coherente con las funciones disponibles.
- `frontend-notification-operations`: mensaje claro al fallar un enlace de WhatsApp.
- `absenteeism-indicator`: fechas iniciales según la zona del consultorio.

## Impact

Componentes, estilos y pruebas de frontend; sin nuevas dependencias ni cambios de API. Usa el sistema visual aprobado, revisión 2.
