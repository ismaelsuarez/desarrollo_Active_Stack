# Proposal

## Why

La agenda y las cuentas ya existen, pero una persona todavía no puede consultar huecos públicos ni reservar y gestionar sus turnos desde su cuenta. C-09 conecta ambas piezas y desbloquea los hitos de confirmación de C-16 y la interfaz pública de C-14.

## What Changes

- Calcular disponibilidad por prestación y profesional, respetando bloques, excepciones, ocupación, grilla configurable y horizonte calendario del consultorio.
- Exponer las cuatro lecturas `/api/v1/publico/*` sin ingreso, con datos mínimos y limitación por proceso.
- Ampliar las rutas existentes de turnos para reserva online verificada y autogestión propia: listar, consultar, confirmar, cancelar y reprogramar según estado y plazo.
- Aplicar los límites RN-64 de días y cantidad futura con exclusión de solapamientos y máximo atómico; presentar alternativas ante horario ocupado.
- Consultar el vínculo vigente en cada solicitud, sin confiar en el JWT para la ficha; conservar permisos y contratos del personal.
- Reutilizar el puerto de hitos nulo de C-07, sin adelantar correos, barrido, enlace de confirmación ni frontend.

## Capabilities

### New Capabilities

- `public-availability`: catálogo público, disponibilidad calculada y lecturas públicas limitadas sin datos de pacientes.
- `patient-appointment-management`: límites y operaciones sobre turnos propios con vínculo vigente, acciones permitidas y alternativas.

### Modified Capabilities

- `appointment-booking`: ampliar la entrada de creación existente a Paciente verificado manteniendo la autoridad del servidor y el contrato del personal.

## Impact

Backend: políticas de reserva, puertos y repositorios de agenda, casos `GestionTurnos`/`ConsultarTurnos`, acciones y schemas de turnos, nuevo router público y adaptador de límite en memoria; pruebas unitarias e integración PostgreSQL real. Dependencias C-05 y C-07 archivadas; C-08 está archivado pero no es requisito de fixtures para este change. No se prevén librerías ni migraciones nuevas.

Fuentes: `CHANGES.md` C-09; KB 05 RN-11–14, RN-17, RN-24, RN-29–37, RN-55, RN-59, RN-62–64; KB 06 US-013–018; KB 07 flujos 3/6; KB 09 DD-27/DD-32; KB 11 A1–A4. Q-06/Q-11 están resueltas; sin preguntas Alta bloqueantes. Governance ALTO: propuesta para revisión antes de apply. Sin pantallas en este alcance.
