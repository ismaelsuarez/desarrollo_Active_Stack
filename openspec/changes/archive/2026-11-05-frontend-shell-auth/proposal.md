# Proposal

## Why

La API ya ofrece autenticación y gestión de cuenta, pero el frontend solo muestra una pantalla inicial. Hace falta una base de navegación y sesión para que pacientes y personal puedan usarla y para habilitar las próximas funcionalidades del roadmap.

## What Changes

- Crear shell y rutas de la SPA, layouts por rol, guardas y estados accesibles de carga, error y acceso denegado.
- Implementar registro, consulta del aviso de privacidad vigente, verificación, reenvío, ingreso, recuperación, restablecimiento y gestión de la cuenta propia.
- Integrar la API de mismo origen, con token de acceso en memoria, renovación mediante cookie HttpOnly, proxy de desarrollo y tratamiento acotado de errores y arranque lento.
- Resolver rutas de enlaces de correo y preparar componentes reutilizables con composición contenedor/presentación. La confirmación de turnos tendrá su ruta y tratamiento del enlace existente; la reserva y demás pantallas de agenda corresponden a otros changes.
- Incorporar pruebas TDD de comportamiento y una comprobación real de cookies mediante el proxy local.

## Capabilities

### New Capabilities

- `frontend-session-shell`: navegación, sesión, guardas, layouts y comunicación de mismo origen de la SPA.
- `frontend-account-flows`: interacción de registro y cuenta, incluyendo enlaces de correo y privacidad.

### Modified Capabilities

Ninguna: los contratos existentes de la API se consumen sin alterar sus requisitos.

## Impact

- `frontend/`: aplicación React/TypeScript/Vite, dependencias de navegación y pruebas, configuración del proxy y componentes.
- API existente `/api/v1/auth/*`, `/api/v1/publico/aviso-privacidad` y `/api/v1/turnos/confirmar-por-enlace`.
- Entorno de desarrollo y distribución del build bajo el mismo origen. No se incluye implementación de agenda, reserva ni configuración de consultorio.
- Cambio visual: la política de diseño del proyecto y, cuando corresponda, sus aprobaciones y mockups deben resolverse antes de aplicar.
