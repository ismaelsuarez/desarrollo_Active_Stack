# Design

## Context

La aplicación dispone del sistema visual aprobado revisión 2. Los cambios afectan estados de reserva, turnos, cuenta, navegación, notificaciones e indicador; no cambian las API ni la identidad visual.

## Goals / Non-Goals

**Goals:** mantener los datos esenciales disponibles, mejorar el feedback y preservar accesibilidad y responsive.

**Non-Goals:** landing, nuevas funciones comerciales o cambios a reglas de negocio.

## Decisions

- Mantener componentes existentes y tokens compartidos, con mensajes visibles para carga, error y reintento.
- Separar la carga de turnos propios de catálogos complementarios para no ocultar datos válidos.
- Conservar control de respuestas obsoletas y no repetir escrituras de resultado incierto.
- Usar la zona del consultorio y esperar su carga antes de fijar fechas iniciales.
- Gestionar foco por navegación de ruta, no por cada render.

## Risks / Trade-offs

- [Respuestas obsoletas o reintentos] → pruebas con peticiones diferidas y control de generación.
- [Demoras o límites de API] → respetar Retry-After y mantener instrucciones claras.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-09).
- Mockups: `mockups/`.
- Approval: approved (2026-11-09, by user).
- Preview: rendered (2026-11-09, `mockups/previews/mobile.png`, `mockups/previews/desktop.png`); la aprobación del usuario fue previa y se obtuvo con el HTML para revisión manual.
- Visual verify: differences (2026-11-09, `mockups/verify/README.md`); capturas inspeccionadas en 390 × 844 y 1440 × 900. Las diferencias mayores se corrigieron; quedan dos diferencias menores. No se automatizó la revisión con lector de pantalla.

