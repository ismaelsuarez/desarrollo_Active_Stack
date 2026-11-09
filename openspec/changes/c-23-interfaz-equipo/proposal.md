# Proposal

## Why

El equipo necesita una interfaz más clara y profesional: la navegación cambia entre pantallas y Mi cuenta no ofrece un regreso explícito. El usuario solicitó mejorar las nueve vistas del panel y su barra de navegación.

## What Changes

- Unificar visualmente navegación y contexto en Inicio, Mi cuenta, Agenda, Pacientes, Solicitudes, Notificaciones, Estado operativo, Configuración y Ausentismo, con adaptación a escritorio y celular.
- Mejorar jerarquía, tarjetas, formularios, listas, indicadores y estados existentes, sin añadir funciones ficticias ni cambiar permisos.
- Agregar un control Volver en Mi cuenta con destino seguro al panel del rol si no hay historial interno apropiado.

## Capabilities

### New Capabilities

### Modified Capabilities

- `frontend-session-shell`: navegación coherente del equipo y retorno desde Mi cuenta.

## Impact

Frontend React, estilos y componentes de navegación; pruebas y capturas. Sin cambios de backend ni dependencias nuevas; se conserva el sistema visual revisión 2 y la demostración local.
