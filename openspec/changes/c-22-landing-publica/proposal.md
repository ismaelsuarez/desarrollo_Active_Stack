# Proposal

## Why

La entrada actual muestra el ingreso y no presenta el consultorio ni descubre la reserva pública. El equipo quiere una portada profesional para pacientes y para explicar el proyecto durante la defensa.

## What Changes

- Presentar una landing pública en `/` a visitantes sin sesión, con acceso destacado a reserva, ingreso y registro.
- Mostrar datos públicos disponibles del consultorio y prestaciones; explicar brevemente los flujos existentes para pacientes y equipo.
- Mantener `/ingresar` como formulario y la redirección al panel correspondiente para sesiones activas.
- Mantener accesos incluso ante carga o fallos y adaptar la página a teclado y pantallas móviles.

## Capabilities

### New Capabilities

- `public-landing`: portada pública informativa, datos disponibles y navegación hacia los flujos existentes.

### Modified Capabilities

- `frontend-session-shell`: entrada raíz y ruta de ingreso para visitantes y sesiones activas.

## Impact

Frontend React, rutas y metadatos; utiliza los endpoints públicos existentes. Sin servicios nuevos, publicación ni datos reales; identidad visual provisional y sistema visual revisión 2.
