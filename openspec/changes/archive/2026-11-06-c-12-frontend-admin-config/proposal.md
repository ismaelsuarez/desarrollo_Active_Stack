# Propuesta: configuración del administrador

## Why

El administrador dispone de API de configuración, pero todavía no tiene pantallas para gestionar el consultorio y sus agendas. C-12 completa esa operación desde la aplicación con validaciones y sin reemplazar las autorizaciones del servidor.

## What Changes

- Incorporar navegación y páginas exclusivas del administrador para personal, profesionales y boxes, horarios, excepciones, prestaciones y parámetros.
- Mostrar validaciones locales y errores del servidor, estados de carga, vacío y error, y resultados claros para escrituras.
- Ante bloqueos con turnos afectados, presentar los turnos devueltos y exigir su resolución explícita antes de reintentar; no modificar turnos silenciosamente.
- Mantener las restricciones de rol, consultorio y negocio de las API existentes, sin ampliar permisos ni alterar turnos históricos.

## Capabilities

### New Capabilities

- `frontend-admin-configuration`: interfaz administrativa para gestionar personal, agenda, catálogo y parámetros.

### Modified Capabilities

Ninguna: las especificaciones existentes de API mantienen sus contratos.

## Impact

Frontend React/TypeScript, navegación de administrador y pruebas de componentes e integración. Consume las API existentes de usuarios, boxes, profesionales, horarios, bloqueos, prestaciones, consultorio y turnos. No se prevén dependencias nuevas ni migraciones; cualquier brecha de API que impida cumplir el alcance deberá señalarse antes de ampliar contratos. El diseño requiere mockups aprobados conforme a la revisión 2 del sistema visual.
