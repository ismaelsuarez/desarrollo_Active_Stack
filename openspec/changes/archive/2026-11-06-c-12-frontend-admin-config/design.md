# Diseño: configuración administrativa

## Context

La SPA ya cuenta con `Guard`, sesión renovable y navegación del personal. Las API existentes ofrecen gestión del personal, prestaciones, parámetros, boxes, profesionales, horarios y bloqueos; las escrituras validan permisos en servidor. El POST de bloqueos responde 409 con `detail.turnos_afectados` (IDs) y no crea el bloqueo. Las rutas de consulta y acciones de turnos ya existen. Ver propuesta y especificación del cambio.

## Goals / Non-Goals

**Goals:** Integrar los flujos administrativos en la SPA sin duplicar reglas de autoridad; preservar datos de formularios ante errores y ofrecer rutas claras de resolución de conflictos.

**Non-Goals:** Cambiar políticas de permisos, inventar operaciones de box no presentes en la API, cancelar turnos en lote, añadir migraciones o nuevas dependencias.

El usuario solicitó posteriormente Playwright para verificar teclado; se agrega como dependencia de desarrollo, sin afectar las dependencias de producción.

## Decisions

1. Agregar rutas bajo guarda `administrador` y navegación específica, reutilizando shell y cliente de sesión. Alternativa de controles ocultos sin guarda descartada: no protege acceso directo, aunque la API siga autorizando.
2. Separar formularios y adaptadores tipados por dominio; usar respuestas reales y errores de campo 422/409. Mantener la autoridad y aislamiento en servidor, sin enviar `consultorio_id` ni confiar solo en validación local.
3. El editor comprueba intervalos del mismo día con semántica de extremos contiguos; envía el conjunto completo solo al ser válido. El servidor vuelve a validar y confirma el estado. No se realiza guardado optimista.
4. Un 409 de bloqueo muestra los IDs devueltos y permite ir a la agenda o al detalle existente para resolver cada turno explícitamente. El formulario conserva el intervalo y ofrece reintento manual: el servidor vuelve a comprobar concurrencia. No hay acción global de cancelación ni confirmación ficticia.
5. Las escrituras no se reintentan automáticamente; ante respuesta incierta se solicita consultar el estado. Las listas se actualizan con respuesta confirmada o una lectura posterior.
6. Por elección del usuario, las cuentas de personal se identifican por usuario y correo; el alta también solicita contraseña inicial y rol. Nombre y apellido corresponden a la ficha de profesional, no a la cuenta de personal.

## Risks / Trade-offs

- [IDs de turnos sin detalles] → Obtener detalles autorizados mediante API existente cuando resulte posible; presentar ID y enlace útil si la lectura falla, sin inventar datos.
- [Concurrencia entre resolver y bloquear] → El 409 del servidor sigue siendo fuente de verdad y el usuario reintenta expresamente.
- [Cambios de configuración afectan reservas] → Validar y presentar consecuencias y errores del servidor; no alterar datos históricos.
- [No todas las operaciones de boxes existen] → Ofrecer solo lista y alta soportadas; no prometer edición o baja inexistente.

## Migration Plan

Desplegar frontend junto con la API actual; no requiere migración. Revertir el build anterior si fuera necesario, sin revertir datos ya confirmados por el servidor.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-06).
- Mockups: `mockups/`; fuentes: `design-system/`, KB 06 US-006 y US-008 a US-012, `CHANGES.md` C-12.
- Approval: approved (2026-11-06, by user). La revisión separa la creación del bloqueo de su ejemplo de conflicto. El usuario también aprobó la revisión anterior de bloqueos y el formulario de personal con usuario y correo.
- Preview: manual (2026-11-06; `mockups/index.html`). Playwright no pudo iniciar: Chrome configurado no se encuentra. No se generaron capturas ni se inspeccionó el render automáticamente; abrir el HTML y revisar a 390×844 y 1440×900.
- Visual verify: manual (2026-11-06). El navegador no está disponible en este entorno; no se inspeccionó la implementación ni se generaron capturas. Revisar con el [checklist](mockups/verify/README.md).
