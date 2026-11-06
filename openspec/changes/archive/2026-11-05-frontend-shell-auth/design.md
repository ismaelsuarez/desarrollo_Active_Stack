# Design

## Context

El frontend actual es un punto de entrada mínimo de React y Vite; tiene Vitest y Testing Library, pero no router ni cliente de sesión. La API ya implementa `/auth/login`, `/refresh`, `/logout`, `/me`, el aviso y operaciones de cuenta; la cookie de refresh rota en cada renovación. `backend/app/main.py` aún no sirve el build y Compose aún no define el destino del proxy. Ver `proposal.md` para el alcance.

## Goals / Non-Goals

**Goals:** una base componible y comprobable para flujos públicos, sesión y layouts de rol, con DD-26 y contratos actuales.

**Non-Goals:** rediseñar autorización del backend, implementar agenda o reserva, incluir datos clínicos, ni agregar un sistema de diseño sin resolver primero la política visual del proyecto.

## Decisions

1. **Router de SPA y árbol por rol.** Usar una biblioteca de enrutado compatible con el React del proyecto y separar rutas públicas, sesión y layouts. Componentes de página conectan servicios y estado; componentes presentacionales reciben props. La alternativa de navegación manual exige reproducir gestión de historial, enlaces y rutas protegidas. El rol administrativo sin pantallas v1 recibe estado explícito.
2. **Tokens efímeros y refresh serializado.** El proveedor conserva el access token solo en memoria; al iniciar intenta `POST /auth/refresh` y consulta `/auth/me`. Una única promesa compartida evita rotaciones simultáneas que la API detectaría como reuso. Tras 401 protegido se renueva una sola vez y se reintenta la solicitud original como máximo una vez solo si la respuesta 401 confirma que fue rechazada antes de procesarse; la propia renovación no se intercepta. No se reintentan escrituras por errores de red o tiempo agotado. Cierre limpia memoria aunque falle la red; avisar que no pudo confirmarse la revocación. Alternativa de localStorage descartada por exposición persistente.
3. **Mismo origen.** Base pública relativa `/api/v1`; Vite reenvía `/api` a `VITE_DEV_PROXY_TARGET`, con `http://localhost:8000` local y `http://api:8000` en Compose. Variable de destino solo en configuración de Vite, no en código de cliente. Build de frontend incluido en imagen de API y fallback SPA solo para GET de rutas no API, sin ocultar 404 de API ni archivos ausentes. Alternativa de dominios separados contradice DD-26 y cookie Strict.
4. **Cuenta y enlaces.** Consumir los esquemas reales: registro envía `nombre`, `apellido`, `telefono`, `email`, `dni`, `nombre_usuario`, `password`, `obra_social` opcional, `acepta_aviso_privacidad` y `aviso_privacidad_version`. No confiar en aceptación previa si cambia la versión. Correo emite `/verificar-email`, `/restablecer-password` y `/confirmar-turno`; KB lista alias `/restablecer` y `/confirmar`, que se admiten sin romper correos existentes. Fragmentos se extraen sin query ni logs, se eliminan del historial en cuanto se capturan y se envían exclusivamente en el cuerpo. Una ejecución por montaje debe evitar dobles POST de tokens de uso único, incluso bajo StrictMode. Confirmación por enlace pertenece a este alcance como interacción mínima de resultado; gestión de agenda queda fuera.
5. **Estados y reintentos.** Timeouts, espera visible y reintentos finitos solamente para lecturas ante errores de conexión o arranque; no repetir peticiones de efecto incierto. 401, 403, 404, 422 y 429 tienen mensajes diferenciados y no revelan más que el contrato API. Campos y resultados se presentan con etiquetas, foco y mensajes accesibles en español.
6. **Verificación por capas.** TDD estricto: unitarias con Vitest/Testing Library y servicios simulados para formularios, rutas y estados; integración real del proxy y cookie con API real, y validación de build/servido y fallback. No simular la cookie HttpOnly como prueba de integración real.

## Risks / Trade-offs

- [La rotación de refresh penaliza reuso] → serializar renovación, cubrir concurrencia y recarga con API real.
- [URLs de KB difieren de correos actuales] → aceptar ambas rutas y probar las efectivamente emitidas.
- [Fallback SPA intercepta API o archivos inexistentes] → registrar rutas API primero, limitar fallback y probar 404.
- [Acciones de token de un solo uso duplicadas por renderizados] → disparo idempotente desde la capa cliente y pruebas bajo StrictMode; el backend conserva su protección de un solo uso.
- [Cambios de correo requieren reverificación] → informar efecto y respetar respuesta del backend.
- [Dominio de autenticación] → solicitar aprobación explícita antes de escribir código de autenticación/seguridad conforme a gobernanza CRITICAL, con propuesta concreta; la autorización de iniciar el change habilita planificación.

## Migration Plan

Construir e incluir frontend junto a API, configurar proxy de desarrollo y verificar deep links y cookie de origen único. Mantener rutas de API y datos existentes. Ante regresión, revertir el despliegue de build/servido sin alterar la base de datos ni los contratos de API.

## UI Mockups

La implementación de autenticación y seguridad descrita en este diseño fue aprobada explícitamente por el usuario el 2026-11-05.

- Design system revision: 2, aprobada por el usuario el 2026-11-05.
- Decision: yes (2026-11-05), política `system-and-mockups`.
- Mockups: `openspec/changes/frontend-shell-auth/mockups/`.
- Approval: approved (2026-11-05, by user).
- Preview: rendered (2026-11-05), capturas en `mockups/previews/` para escritorio 1440×900 y celular 390×844, con página completa.
- Visual verify: differences (2026-11-05); revisión parcial, diferencias y estados pendientes detallados en [evidence.md](evidence.md).

Las vistas aprobadas y sus capturas son criterios de aceptación visual: [ingreso](mockups/acceso.html), [registro](mockups/registro.html), [enlaces](mockups/enlaces.html), [cuenta](mockups/cuenta.html) y [roles](mockups/roles.html); capturas de [escritorio y celular](mockups/previews/).

### Brief

Usuarios: pacientes y personal de recepción, profesionales, administradores y administrativos. Tareas: acceder, registrar cuenta con aviso vigente, verificar correo, recuperar o cambiar contraseña, confirmar por enlace y gestionar contacto. Se proponen estados de espera, error, éxito y acceso restringido. Vistas adaptadas a 390 y 1440 px con tokens, marca y logo compartidos aprobados. Nombre y logo definitivos permanecen (TBD). La galería muestra cada pantalla y sus estados juntos para revisión; la implementación presenta solo la pantalla y estado correspondientes.
