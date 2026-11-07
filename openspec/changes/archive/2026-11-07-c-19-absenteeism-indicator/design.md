# Design

## Context

Existe la política `indicador.ausentismo` con permiso exclusivo de administrador. Turnos, sesión y reloj ya existen; no existe aún consulta agregada ni pantalla. Ver propuesta y RN-45, RN-46, Flujo 10 y Q-15.

## Goals / Non-Goals

**Goals:** consulta aislada por consultorio y filtros, con evolución y estados explícitos.

**Non-Goals:** modificar estados de turnos, exportar datos o identificar pacientes; integrar sistemas externos.

## Decisions

- API calcula agregados en servidor filtrando por `consultorio_id` del principal; no acepta consultorio del cliente. Se reutiliza la política existente. Alternativa de agregar en navegador descartada por privacidad y volumen.
- El período se expresa mediante fechas locales inclusivas del consultorio, convertido a intervalo semiabierto de instantes; se consulta por inicio del turno y se excluye inicio posterior al reloj inyectado. Evolución mensual dentro del intervalo, totales y detalle por profesional usan el mismo conjunto filtrado. La fórmula, filtros, evolución mensual y tratamiento de sin cierre fueron confirmados por el usuario el 2026-11-07 (Q-15).
- Se devuelve tasa fraccional nullable y recuentos por estado; el frontend formatea porcentaje y explica ausencia de denominador. Los pendientes y confirmados ya iniciados se cuentan juntos como sin cierre.
- Contrato implementado: respuesta `{resumen, evolucion, profesionales}`; resumen contiene `ausentes`, `atendidos`, `cancelados`, `liberados`, `sin_cierre`, `tasa`; evolución contiene esos campos más `mes` (`YYYY-MM`), profesionales esos campos más `profesional_id` y `nombre`. Los modelos de respuesta se publican en OpenAPI.
- Intervalo inválido y parámetros no declarados se rechazan; el profesional ajeno al consultorio no revela datos. No se requiere migración ni dependencia externa.

## Risks / Trade-offs

- Q-15 y SU-16: el usuario confirmó la fórmula, filtros por fechas y profesional, evolución mensual y tratamiento de sin cierre el 2026-11-07.
- Los datos agregados cambian al corregir estados: son una fotografía actual, no un informe histórico inmutable.

## Migration Plan

Desplegar API y frontend juntos; revertir ambos si fuera necesario. No hay cambio de esquema previsto.

## UI Mockups

- Design system revision: 2
- Decision: yes (2026-11-07)
- Mockups: `mockups/`
- Approval: approved (2026-11-07, by user)
- Preview: rendered (2026-11-07; `mockups/previews/mobile.png`, `mockups/previews/desktop.png`; Playwright con Edge)
- Visual verify: differences (2026-11-07; `mockups/verify/`): inspeccionados estados normal, vacío, error y carga en móvil 390×844 y escritorio 1440×900. Playwright aprobó sin desbordes generales, errores de consola ni fallos de red inesperados en el estado normal; error 500 fue inyectado intencionalmente para probar el reintento. Servidor detenido. Diferencias frente al mockup:
  - Resuelta, móvil: la navegación ahora ocupa una sola fila desplazable y mantiene visible y señalada la sección activa, como la navegación compacta del mockup. Conserva enlaces y contadores adicionales de la aplicación; estos aparecen en una segunda fila. Probados el foco y el desplazamiento por teclado.
  - Menor, ambos: la evolución usa etiquetas `AAAA-MM` y barras relativas al mes de tasa más alta; el mockup muestra nombres de meses. Abrir `/ausentismo` con datos de varios meses.
  - Menor, móvil: la tabla permite desplazamiento horizontal para ver todas las columnas. Abrir `/ausentismo` con datos y desplazar la tabla.
  - Menor, vacío y carga: se presentan bajo los filtros y el vacío conserva los indicadores en cero; el mockup los muestra en paneles de ejemplo independientes. Forzar respuesta vacía o demorada.
  - No se verificó una sesión real conectada al backend desde el navegador; las respuestas de la API se simularon en Playwright. La API se verificó por separado contra PostgreSQL real.
