# Proposal

## Why

Recepción necesita gestionar turnos completos sin dobles reservas ni cambios parciales. C-00 aporta la reserva básica y su exclusión en PostgreSQL; C-04 y C-06 aportan autorización y configuración de agenda, pero faltan su integración, el ciclo de vida y el historial de C-07 (RN-14, RN-17, RN-21, RN-24, RN-37).

## What Changes

- Extender la creación por Recepción/Administrador con horario, excepciones, grilla, duración ajustada, ficha existente sin cuenta y estado inicial según RN-23/RN-29/DD-32.
- Incorporar reprogramación sobre la misma fila, cancelación con motivo, confirmación, liberación manual, atendido, ausente y corrección, con autorización centralizada e historial atómico.
- Exponer lecturas de turnos, historial, agenda y turnos de una ficha, y el adaptador de acceso a pacientes por agenda previsto para C-08.
- Evolucionar la tabla `turno` existente y agregar `turno_historial` y las FK pendientes de `token_usuario` y `notificacion`; conservar la exclusión creada por C-00 y comprobar su vigencia.
- Corregir en el contrato ABAC el rechazo por identificador de un turno de otra agenda: 404, según KB 11 y las instrucciones del proyecto; una agenda ajena sigue siendo 403.
- Mantener la garantía de una sola reserva regular concurrente y el 409 de horario ocupado. Comprobar el control aplicativo contra sobreturnos activos sin prometer resolver su carrera residual.

Fuera de alcance: UI, reserva pública y disponibilidad pública de C-09, alta/autorización de sobreturnos C-10, gestión de fichas C-08, despacho/hitos C-15/C-16, WhatsApp C-17 y despliegue C-20. Se prevén puertos de integración; no se adelantan esos endpoints ni servicios.

## Capabilities

### New Capabilities

- `appointment-lifecycle`: reprogramación, transiciones e historial coherente de turnos.
- `appointment-agenda`: lecturas autorizadas de agenda, turnos e historial de una ficha.

### Modified Capabilities

- `appointment-booking`: ampliar creación con reglas de agenda, estado inicial, duración ajustada y respuesta API de conflictos, preservando la garantía concurrente de C-00.
- `core-data-models`: completar turno e historial, añadir FK pendientes y mantener atomicidad y tiempo inyectado.
- `attribute-based-access-control`: distinguir agenda ajena (403) de turno ajeno consultado por identificador (404), conservando las demás políticas.

## Impact

Backend FastAPI, casos de uso, repositorios SQLAlchemy asíncronos, políticas puras, modelos y nueva migración Alembic sobre `0007_agenda_config`; pruebas unitarias, PostgreSQL real y API. No se añaden dependencias de aplicación ni servicios pagos.

Dependencias de roadmap: C-04 y C-06 figuran archivados; la CLI confirmó la raíz local y ausencia de changes activos antes de crear este change. Gobierno CRÍTICO: esta preparación autoriza solo documentos; apply necesita un pedido explícito posterior.

Fuentes: `CHANGES.md` §C-07; KB 04 §turno/turno_historial; KB 05 RN-14, RN-17 a RN-24, RN-29, RN-32, RN-34 a RN-38, RN-44, RN-64; KB 06 US-019 a US-023, US-025 a US-028, US-038; KB 09 DD-08/DD-14/DD-32 y SU-39; KB 11 §Matriz de decisión. Revisión mediante `appointment-conflict-reviewer` y consultas oficiales con Context7, detalladas en `design.md`.
