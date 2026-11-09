# Design

## Context

La navegación del inicio de rol y la de las pantallas del personal son componentes distintos; Mi cuenta no muestra la segunda. Las nueve vistas mezclan patrones de formularios, paneles y estados. El proyecto usa sistema visual revisión 2, aprobado.

## Goals / Non-Goals

- Unificar jerarquía visual, navegación y adaptación a escritorio y celular para las nueve vistas solicitadas.
- Hacer visible Volver en Mi cuenta sin perder una ruta segura al panel del rol cuando no haya historia interna.
- Mantener los permisos, las acciones existentes y estados de carga, vacío, errores y confirmaciones. Los datos del mockup son sintéticos.
- No alterar lógica de negocio, crear gráficos con cifras inventadas ni agregar módulos o proveedores.

## Decisions

- Navegación de equipo común por rol en todas las vistas, incluida Mi cuenta e Inicio; elemento activo identificable sin depender solo del color. Controles accesibles y diseño móvil sin ocultar destinos.
- Paneles, tipografía y estados derivados de tokens de revisión 2, con niveles de información y foco visible. Componentes de administración, paciente y operaciones mantienen sus datos y acciones reales.
- Volver desde Mi cuenta regresa al contexto interno anterior cuando sea identificable; de lo contrario abre el inicio del rol autenticado, sin depender de una URL externa.
- El mockup muestra nueve pantallas seleccionables para revisión como administrador; la implementación limitará enlaces por rol según permisos actuales. La vista móvil presenta menú desplegable accesible.

## Risks / Trade-offs

- La reorganización de navegación puede afectar foco y permisos; cubrir con pruebas de roles, teclado y rutas. Formularios complejos y errores necesitan revisarse además de los estados representativos del mockup.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-09).
- Mockups: `mockups/`.
- Approval: approved (2026-11-09, by user).
- Preview: rendered (2026-11-09, `mockups/previews/`, nueve pantallas en móvil y escritorio y menú móvil abierto).
- Visual verify: differences (2026-11-09, `mockups/verify/README.md`).
