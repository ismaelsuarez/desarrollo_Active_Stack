# Diseño

## Context

Ver propuesta y deltas. La sesión actual expone id de usuario pero no id de profesional; `/profesionales` con usuario_id es solo administrador. `GET /agenda` exige id de profesional y las lecturas operativas no incluyen `acciones_permitidas`. El 409 de turno para personal es texto sin alternativas; solo la reserva del paciente incluye alternativas. El cliente conserva sesión en memoria, reintenta lecturas y evita repetir escrituras salvo renovación tras 401.

## Goals / Non-Goals

**Goals:** entregar recorridos completos seguros, sin inferir la agenda por nombre ni sustituir políticas del servidor.

**Non-Goals:** alterar políticas, crear un motor de disponibilidad o cambiar el dominio de turnos y fichas. No publicar ni introducir trabajadores nuevos.

## Decisions

1. **Contexto propio y acciones.** Añadir lectura autenticada mínima para resolver el profesional vinculado al principal (null si no existe) y agregar acciones calculadas por políticas/reloj del servidor a respuestas operativas. Mantener forma paciente e invariantes de consulta. Alternativa descartada: identificar por nombre o derivar permisos en navegador; no es fiable y puede exponer información. Cubrir ABAC y aislamiento con PostgreSQL real.
2. **Agenda y datos.** Recepción utiliza catálogo público activo para selección y Administrador puede usar catálogo autenticado; Profesional obtiene id desde contexto propio. Fechas se representan en zona pública del consultorio; solicitudes obsoletas se ignoran. Profesionales inactivos no presentes en catálogo público requieren etiqueta neutral si aparecen en históricos; no adivinar identidad.
3. **Conflictos y opciones.** Personal recibe 409 sin alternativas. Consultar disponibilidad pública separadamente cuando sea posible, etiquetándola orientativa: usa duración vigente, horizonte público y no excluye turno original. Si no hay opciones o falla la consulta, mostrar conflicto y permitir elegir otra fecha/hora. No afirmar que el 409 incluye alternativas ni que una opción garantiza éxito. La API conserva última palabra.
4. **Ficha y reserva.** Alta de ficha y turno son dos escrituras independientes. No aparentar atomicidad: si ficha se creó y turno falla, conservar selección y comunicar que la ficha permanece; no repetir alta automáticamente. No retener información sensible en almacenamiento persistente ni logs.
5. **Permisos y concurrencia.** Guardas de ruta y controles de UX por rol y acciones recibidas, nunca como seguridad; API verifica cada escritura. Deshabilitar doble envío y actualizar tras éxito/409; no repetir solicitudes cuyo resultado sea incierto. Desvincular requiere motivo antes de envío; vínculo rechazado puede seleccionarse para vincular y solo pendiente para rechazo.
6. **Presentación.** Reutilizar tokens revisión 2, componentes existentes y rutas por rol; estado de carga, vacío y fallo diferenciados, etiquetas visibles, foco y uso de teclado. El mockup es referencia de estados, no aplicación funcional ni fuente de datos.

## Risks / Trade-offs

- [Extensión de lectura de autorización] → probar que no amplía acceso ni revela agenda ajena y que el servidor revalida al escribir.
- [Opciones orientativas] → explicar su límite al reprogramar y manejar 409/422 sin pérdida de datos.
- [Ficha ya creada cuando falla turno] → mostrar resultado parcial y ofrecer continuar con la ficha.
- [Cuota de lectura pública] → tratar 429 como indisponibilidad temporal sin bucle; permitir elegir otra fecha.

## Migration Plan

Desplegar backend compatible y SPA juntos, sin migración. Revertir SPA y ampliaciones de lectura si es necesario; no revertir datos creados por el personal.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-06), política `system-and-mockups`.
- Mockups: [`mockups/index.html`](mockups/index.html), guía [`mockups/README.md`](mockups/README.md).
- Approval: approved (2026-11-06, by user).
- Preview: manual (2026-11-06, `mockups/index.html`); Playwright no inició porque no encuentra Chrome configurado y Computer Use informó que el host de navegador no está disponible. No se generaron capturas ni se inspeccionó visualmente el render.
- Visual verify: manual (2026-11-06), pendiente de ejecución por pantalla; ver [`mockups/verify/README.md`](mockups/verify/README.md). No hubo inspección, capturas, comprobación de consola/red ni teclado automatizados.
