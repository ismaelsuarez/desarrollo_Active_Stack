# Diseño

## Context

C-09 expone catálogos públicos, disponibilidad y gestión propia; C-11 aporta sesión en memoria, rutas y cliente HTTP. `GET /turnos` devuelve `acciones_permitidas` y `profesional_id`, no el nombre del profesional. El catálogo público contiene solo profesionales activos. `ApiError` actual conserva estado y campos inválidos, pero descarta detalles y alternativas. Ver `proposal.md` y `specs/`.

## Goals / Non-Goals

**Goals:** una navegación accesible de consulta pública, reserva y gestión propia que preserve autoridad y privacidad de la API.

**Non-Goals:** cambiar reglas de agenda, autorización, modelos o cronograma de notificaciones; crear cuenta, ficha o reserva automáticamente; publicar el sistema.

## Decisions

1. **Datos y autoridad.** Consumir `GET /publico/{consultorio,prestaciones,profesionales,disponibilidad}` y `/turnos` con las credenciales de C-11. Usar `acciones_permitidas` del servidor para controles y refrescar tras cada acción. No calcular permisos con el reloj del dispositivo. El catálogo resuelve nombres disponibles; si un profesional ya no aparece, mostrar una identificación neutral y no inventar el nombre. Alternativa descartada: asumir que el catálogo activo resuelve todo turno histórico.
2. **Selección y autenticación.** Conservar en memoria una selección pública mientras dure la navegación; al pasar por ingreso/registro o abrir verificación en otro contexto, ofrecer volver a elegir cuando se haya perdido. La autenticación no envía la reserva: el paciente confirma de nuevo. No persistir tokens ni información sensible de salud. Alternativa descartada: ejecutar automáticamente la operación después del ingreso.
3. **Contratos de escritura.** `POST /turnos` recibe solo `profesional_id`, `prestacion_id` e `inicio` con zona; `PATCH /turnos/{id}` solo `inicio`; confirmar/cancelar usan sus endpoints. Mostrar estado real de respuesta y volver a consultar. Deshabilitar envíos repetidos; si una respuesta es incierta, indicar que se revisen los turnos antes de reintentar. No repetir escrituras automáticamente.
4. **Errores tipados.** Ampliar el cliente preservando compatibilidad y un subconjunto validado de `detail` para 409 de horario, alternativas o límite, y 403 de plazo/teléfono, sin registrar cuerpos arbitrarios. Cuando un 403 no identifique su causa con seguridad, dar orientación general sin atribuirle una causa concreta. La API sigue siendo la autoridad.
5. **Zona y reprogramación.** Usar la zona pública del consultorio para fechas locales y visualizar intervalos devueltos como instantes; enviar el instante con zona sin reinterpretarlo en la zona del dispositivo. La disponibilidad pública se calcula con duración vigente de prestación y no excluye el turno original; la reprogramación conserva su duración real. Por tanto estos intervalos son orientativos para reprogramar, pueden omitir opciones o ser rechazados: advertirlo y manejar 409/422 conservando el original. No prometer exhaustividad ni éxito antes del servidor. Una API específica sería más precisa pero cambia alcance backend y no se presupone aquí.
6. **Lecturas y carreras.** Reutilizar los reintentos limitados de C-11 y aviso de espera; cancelar o ignorar respuestas obsoletas al cambiar selección. Tratar 429 con un mensaje de espera, sin bucle. Contrastar estados vacíos, error y carga con controles accesibles.

## Risks / Trade-offs

- [Duración histórica distinta al catálogo] → disponibilidad orientativa en reprogramación, sin garantía ni exhaustividad; el servidor valida y preserva el original. Es una limitación funcional que debe ser visible en la revisión de producto.
- [Nombre de profesional inactivo no disponible] → identificación neutral para turnos históricos; no revelar datos de terceros ni afirmar nombres.
- [Cambios de disponibilidad entre consulta y escritura] → aceptar alternativas 409 solo como sugerencias sujetas a nuevo envío.
- [Revisión visual C-11 parcial] → sus limitaciones se conservan en el archivo histórico y no se declaran resueltas por C-14.

## Migration Plan

Publicar junto al build SPA y API existente, sin migraciones. Para revertir, desplegar el build SPA previo; no revertir turnos creados. Verificar rutas directas y proxy existente.

## UI Mockups

- Design system revision: 2.
- Decision: yes (2026-11-05), conforme a `system-and-mockups`.
- Mockups: [`mockups/index.html`](mockups/index.html); brief y pasos de revisión en [`mockups/README.md`](mockups/README.md).
- Approval: approved (2026-11-05, by user; revisión corregida de registro e ingreso).
- Preview: manual (2026-11-05, `mockups/index.html`); Playwright no inició por ausencia de Chrome configurado. La revisión de registro e ingreso tampoco tiene capturas ni inspección renderizada automatizada.
- Visual verify: manual (2026-11-05). El usuario pidió omitir esta revisión en C-14; no se inspeccionó la implementación ni se afirma coincidencia. Checklist y limitaciones en [`evidence.md`](evidence.md).
