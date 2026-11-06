# Design

## Context

`RepositorioAvisosDeTurnoSQL` programa email y retorna temprano si falta correo. La bandeja de `ConsultarNotificaciones` admite estado pero no canal y usa proyección mínima; el esquema de notificación ya admite canal, estados, mensaje, enlace y actor, con unicidad por turno/tipo/canal/ciclo. `omitir_hitos` ya incluye `preparada` en todos los canales. El barrido de correo y decisiones de C-16 debe preservarse.

## Goals / Non-Goals

**Goals:** Añadir un flujo durable de preparación y marca manual sin acoplar WhatsApp a la entrega o disponibilidad de correo, manteniendo políticas y aislamiento existentes.

**Non-Goals:** UI (C-18), API de WhatsApp Business, envío automático, comprobación de entrega o alterar RN-60.

## Decisions

1. **Trabajo durable independiente por canal.** Programar o disponer de un marcador durable WhatsApp por hito/hecho en su transacción de origen, luego preparar al vencer mediante el barrido; conservar un snapshot del hecho para avisos de reprogramación/cancelación aun si el turno cambia después. Alternativa descartada: derivar de emails enviados, que perdería pacientes sin correo y avisos cuando SMTP falla. Selección de vencidos acotada, concurrente e idempotente con PostgreSQL y unicidad existente; preservar ventanas y condiciones vigentes en la misma transacción que serializa contra los cambios del turno. No introducir otro proceso.
2. **Serialización y omisión.** Lock de fila del turno antes de revisar estado/ciclo y crear la preparada, orden de locks consistente con transiciones existentes; `omitir_hitos` omite programada/preparada y hechos consumados no se omiten. Probar carreras con PostgreSQL real, incluida marca manual. Las filas de hechos usan el ciclo y snapshot del momento del hecho, nunca se reconstruyen con fecha nueva del turno.
3. **Sin contacto utilizable.** Normalización en value object puro: soporte explícito de números internacionales con `+` o `00` y nacionales argentinos, incluidas convenciones móviles; nunca adivinar números ambiguos o imposibles. Contacto ausente/inválido no bloquea el hecho ni otro canal; registro técnico sin teléfono ni texto. Las reglas exactas de prefijos se prueban con ejemplos nacionales, móviles, extranjeros y errores.
4. **Mensajes seguros.** Construir desde datos permitidos y zona del consultorio, no desde notas ni plantillas clínicas; codificar el texto de URL. El recordatorio respeta RN-26/RN-60 en el instante de preparación. Nunca persistir token de confirmación en claro o incluirlo en WhatsApp; confirmar mediante canales existentes.
5. **Acceso y contratos.** Extender consulta con filtro canal validado, manteniendo salida y orden anterior cuando no se pide WhatsApp preparado; ordenar esa combinación por `programada_para`, desempate por ID. Dos rutas específicas reutilizan RBAC/ABAC NOTIFICACION_GESTIONAR, consultorio desde principal y actualización condicional `preparada` → `enviada_manual` con actor y hora; 404 para identificador ajeno, 409 para estado/canal incompatible. La lista sigue sin payload; solo detalle autorizado devuelve enlace. Marca no prueba entrega y no abre servicios externos.

## Risks / Trade-offs

- [Carrera entre barrido y reprogramación] → serializar la lectura y escritura; ensayar ambas intercalaciones con PostgreSQL real.
- [Teléfonos ambiguos] → rechazar normalizaciones inseguras, conservar señal técnica sin datos y no impedir correo.
- [Marcación no garantiza envío] → denominar estado envío manual, sin promesa de entrega.
- [Cambios al esquema si se requiere snapshot o trabajo durable] → migración reversible con un solo head y prueba de upgrade/downgrade; no mutar filas históricas ni exponer datos en logs.

## Migration Plan

Revisar si el modelo actual permite almacenar trabajo y snapshot de forma duradera sin colisiones. Si requiere campos o índices, migrar sobre head vigente, validar upgrade/downgrade y compatibilidad con datos anteriores; rollback retira solo lo agregado sin alterar avisos email. Los trabajos existentes no se recrean retrospectivamente salvo diseño explícito que evite duplicaciones y textos obsoletos.

## UI Mockups

Decision: no (no UI). C-17 solo modifica API y procesamiento; pantallas corresponden a C-18.
