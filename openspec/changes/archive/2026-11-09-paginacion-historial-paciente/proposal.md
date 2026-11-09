# Proposal

## Why

El historial de una ficha puede crecer sin límite y la pantalla solicita todos los turnos de una vez. La API ya admite páginas opcionales tras la corrección de la auditoría.

## What Changes

- Consultar el historial en páginas acotadas, con controles anterior y siguiente, y conservar la ficha visible durante carga o error.
- Mantener permisos, aislamiento y contrato compatible para clientes que no envían paginación.
- Revisar los controles en móvil y escritorio antes de aplicar.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `frontend-patient-records`: navegación por páginas del historial autorizado.

## Impact

Pantalla de fichas, sus pruebas y los parámetros opcionales `limit` y `offset` del endpoint existente. Sin dependencias nuevas.
