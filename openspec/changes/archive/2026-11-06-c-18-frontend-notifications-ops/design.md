# Diseño: operación de notificaciones

## Context

La bandeja ofrece filtros `canal`, `estado`, `limit` y `offset`, sin total ni nombre/contacto; el detalle de WhatsApp devuelve solo id y enlace. `/turnos?sin_confirmar=true` devuelve acciones calculadas por servidor. `/notificaciones/indicadores` expone antigüedades, alerta y último barrido. El shell y detalle de turno existentes son reutilizables.

## Goals / Non-Goals

**Goals:** interfaz operativa por rol, accesible y resiliente, con información mínima real.

**Non-Goals:** envío automático de WhatsApp, cambiar políticas ABAC, exponer contenido de correo o construir una nueva API de conteos.

## Decisions

1. Nuevas rutas protegidas para bandejas, turnos sin confirmar y panel; reutilizar cliente de sesión, detalle y acciones existentes. El servidor sigue autorizando cada operación.
2. La lista WhatsApp usa `canal=whatsapp&estado=preparada`; la de correo usa `canal=email&estado=fallida`. El listado no incluye destinatario: mostrar tipo, id, fecha e id de turno y acceder a detalle autorizado. Páginas con siguiente/anterior; un resultado incompleto no representa total.
3. Obtener el enlace al pulsar y abrirlo por acción del usuario con protecciones de nueva pestaña; comprobar destino `https://wa.me/` y gestionar bloqueo de ventana sin marcar enviado. Marcar enviado es independiente; ante resultado incierto consultar, no reenviar la escritura.
4. Indicadores del servidor son fuente de verdad para cuota y alerta; fechas en zona del consultorio. Sin total de WhatsApp, usar `99+` si hay al menos 100 filas, o total exacto solo si una página completa de 100 tiene menos de 100; no enumerar páginas para un contador. El conteo de turnos procede de la lista íntegra devuelta; error es desconocido, nunca cero.
5. Advertencia de último barrido con umbral de presentación de 15 minutos (tres intervalos previstos de cinco minutos), configurable mediante constante local y documentado como indicativo; si no hay barrido, indicarlo. No confundirlo con TTL de reclamación, que no expone la API. Cuota usa `alerta` del servidor, no un cálculo alternativo.
6. Acciones de turnos se derivan exclusivamente de `acciones_permitidas`, con validación y resolución del conflicto del servidor. Al fallar una escritura por red, no repetir automáticamente.

## Risks / Trade-offs

- [Sin conteo total en bandeja] → indicador acotado `99+`, paginación real en la pantalla.
- [Bloqueo de ventanas tras solicitud asíncrona] → comprobar apertura y ofrecer enlace seguro explícito sin registrar envío.
- [El servidor autoriza indicadores también a Recepción] → la UI limita el panel a Administrador, sin cambiar seguridad existente.
- [Reloj local al calcular antigüedad de barrido] → advertencia es orientativa; mostrar fecha real y sin afirmar fallo definitivo.

## Migration Plan

Desplegar frontend con API C-17; revertir frontend si es necesario, sin migración de datos ni cambios de contrato.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-06).
- Mockups: `mockups/`.
- Approval: approved (2026-11-06, by user).
- Preview: rendered (2026-11-06, `mockups/previews/mobile.png` 390×844 y `mockups/previews/desktop.png` 1440×900; Edge headless).
- Visual verify: differences (2026-11-06); capturas y pendientes en `mockups/verify/README.md`.
- Navegación: el usuario eligió mantener páginas separadas tras conocer la diferencia con el mockup (2026-11-06). El mockup original se conserva como referencia; no representa esta decisión posterior.
