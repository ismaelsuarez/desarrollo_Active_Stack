# Design

## Context

La API conserva el contrato anterior y acepta `limit` y `offset` opcionales. La pantalla actual carga ficha e historial en paralelo y descarta respuestas obsoletas por generación.

## Goals / Non-Goals

**Goals:** limitar la lectura y mantener accesible la ficha al navegar o ante errores.

**Non-Goals:** alterar permisos, modificar turnos o rediseñar la ficha.

## Decisions

- Solicitar 21 filas por página y mostrar 20; la fila adicional indica si existe página siguiente sin exigir conteo total ni cambiar el contrato de la API.
- Resetear página al abrir otra ficha; descartar respuestas antiguas y deshabilitar navegación durante la lectura.
- Ante error de página, mantener el historial previo y ofrecer reintento; no revelar datos de una ficha anterior al cambiar de paciente o identidad.

## Risks / Trade-offs

- [Altas o cambios durante la navegación] → orden estable por inicio e identificador; se documenta que offset no es una instantánea.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-09).
- Mockups: `mockups/`.
- Approval: approved (2026-11-09, by user).
- Preview: rendered (2026-11-09, `mockups/previews/mobile.png`, `mockups/previews/desktop.png`).
- Visual verify: differences (2026-11-09, `mockups/verify/README.md`).

