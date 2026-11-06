# Propuesta: autorización de sobreturnos

## Why

La agenda identifica sobreturnos pero aún no permite otorgarlos con autorización trazable ni registrar la respuesta del profesional. Recepción necesita resolver excepciones de agenda sin perder los límites y el aislamiento existentes.

## What Changes

- Incorporar creación explícita de sobreturnos por Recepción o Administrador con motivo, autorización y solapamiento efectivo, dentro de la agenda y sin bloqueo.
- Registrar en una transacción el turno, su historial, la autorización y el aviso visible al profesional, conservando la integración de hitos y avisos existente.
- Permitir al profesional afectado o al administrador con esa agenda propia responder aprobado o rechazado; la respuesta no altera el turno ni veta el otorgamiento.
- Exponer el aviso y respuesta al personal autorizado en la agenda y vistas operativas, sin ampliar datos de la cuenta de paciente.
- Probar concurrencia, reversión y exclusión sobre PostgreSQL real, además de permisos y contratos HTTP. No incluye pantalla de personal (C-13), límites máximos nuevos ni envíos externos al profesional.

## Capabilities

### New Capabilities

- `overbooking-authorization`: otorgamiento, autorización, aviso y respuesta del profesional sobre sobreturnos.

### Modified Capabilities

Ninguna: se añade el aviso operativo bajo la capacidad nueva, preservando los contratos de autorización y agenda existentes.

## Impact

API de turnos, unidad de trabajo, repositorios, esquema y una migración Alembic sobre el head vigente; lecturas de agenda y pruebas de PostgreSQL. Se reutilizan las políticas ABAC y los planificadores existentes. Incluye autorización y acceso a datos, dominios críticos que requieren aprobación explícita antes de escribir código en apply. Depende de C-07 ya archivado.
