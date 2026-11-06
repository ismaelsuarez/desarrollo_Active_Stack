# Propuesta: operación de notificaciones

## Why

Recepción no dispone de una pantalla para gestionar WhatsApp preparado, fallos de correo y turnos sin confirmar; Administración tampoco visualiza la salud del barrido. C-15 a C-17 ya ofrecen las operaciones necesarias para incorporarlas a la interfaz.

## What Changes

- Bandejas de WhatsApp preparado y correos fallidos, con carga, vacío, error y paginación; abrir el enlace entregado por la API y registrar explícitamente el envío manual.
- Lista de turnos sin confirmar con acciones autorizadas por el servidor y acceso al detalle existente.
- Accesos e indicadores operativos de Recepción y panel administrativo de salud del barrido y cuota de correo.
- Manejo de permisos, conflictos y resultados inciertos, sin duplicar escrituras ni exponer datos innecesarios.

## Capabilities

### New Capabilities

- `frontend-notification-operations`: interfaz de operación de notificaciones, turnos sin confirmar y salud del barrido.

### Modified Capabilities

Ninguna; los contratos de backend existentes se reutilizan.

## Impact

Frontend React/TypeScript, cliente API y navegación de personal; pruebas de componentes y de integración. Consume endpoints existentes de notificaciones, indicadores y agenda. No automatiza el envío de WhatsApp ni incorpora proveedor externo.
