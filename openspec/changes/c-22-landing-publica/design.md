# Design

## Context

La aplicación ya ofrece consulta pública de consultorio y prestaciones y un flujo de reserva accesible sin sesión. La raíz actualmente conduce al ingreso. El público de la nueva portada incluye pacientes y docentes; la identidad del consultorio aún es provisional.

## Goals / Non-Goals

- Presentar una entrada comprensible y accesible, con acciones de reserva e ingreso visibles aun si faltan datos.
- Explicar el flujo del paciente y las funciones reales del equipo sin prometer funcionalidades o resultados no verificados.
- No cambiar permisos, backend, funciones de agenda ni publicar la aplicación.

## Decisions

- `/` mostrará la portada sin sesión; sesión cargando conserva su estado y sesión activa redirige al panel de su rol. `/ingresar` mantiene el formulario y la redirección de sesión activa.
- Los datos del consultorio y prestaciones provendrán de los endpoints públicos existentes; cada fallo o ausencia se representará sin inventar datos y sin ocultar acciones. Los límites del servidor se respetarán al reintentar.
- La composición usa tokens de revisión 2, logo provisional local y diagramas tipográficos, sin fotografías no autorizadas ni cifras o testimonios inventados.
- La vista separará presentación y carga de datos; la navegación por teclado, foco y títulos tendrán pruebas.

## Risks / Trade-offs

- El nombre, logo, prestaciones y datos de contacto del mockup son ilustrativos; producción deberá mostrar datos realmente servidos por la API.
- La aplicación es SPA: metadatos básicos no garantizan indexación de contenido dinámico.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-09).
- Mockups: `mockups/`.
- Approval: approved (2026-11-09, by user).
- Preview: rendered (2026-11-09, `mockups/previews/landing-mobile.png`, `landing-desktop.png`, `estados-mobile.png`, `estados-desktop.png`).
- Visual verify: differences (2026-11-09, `mockups/verify/README.md`).
