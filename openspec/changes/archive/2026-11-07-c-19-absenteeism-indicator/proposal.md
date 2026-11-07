# Proposal

## Why

El administrador todavía no dispone de una vista de ausentismo que distinga ausencias de cancelaciones y turnos liberados. C-19 completa el indicador previsto en RN-45 y US-040.

## What Changes

- Consulta agregada por período y profesional, limitada al consultorio del administrador y a turnos cuya hora ya llegó.
- Tasa de ausentes sobre atendidos más ausentes; recuentos separados de cancelados, liberados y turnos pasados sin cierre.
- Pantalla administrativa accesible con filtros, resumen, evolución temporal, detalle por profesional y estados de carga, vacío y error.
- Q-15 validada por el usuario el 2026-11-07: fórmula RN-45, filtros por fechas y profesional, evolución mensual y turnos sin cierre separados.

## Capabilities

### New Capabilities

- `absenteeism-indicator`: consulta y presentación del indicador por período y profesional.

### Modified Capabilities

Ninguna.

## Impact

Nueva ruta API y consulta agregada en backend, y nueva vista y navegación administrativa en frontend. Reutiliza turnos, reloj inyectado y autorización de indicadores existente. No requiere migración prevista.
