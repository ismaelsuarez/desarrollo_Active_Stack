# Proposal

## Why

El registro de C-05 ya crea fichas y solicitudes de vinculación, pero Recepción todavía no puede resolverlas ni corregir vínculos equivocados desde la API. C-08 completa la gestión de fichas y el vínculo vigente, con aislamiento por consultorio y sin perder los turnos existentes (RN-47 a RN-51, RN-62, RN-63; US-036 a US-039, US-041, US-042).

## What Changes

- Agregar búsqueda paginada, alta, detalle y edición de fichas; conservar DNI único, datos mínimos, ausencia de borrado y prohibición de editar `activo` o el vínculo por PATCH.
- Aplicar acceso de Recepción/Administrador a su consultorio, Profesional a pacientes de su agenda y Paciente a su ficha vigente. Exponer la cuenta vinculada únicamente al personal habilitado.
- Listar solicitudes pendientes o resueltas y permitir vincular/rechazar con escrituras condicionales, bloqueo inicial de la ficha y reversión íntegra ante conflicto.
- Desvincular con motivo y revocación transaccional de refresh tokens; reactivar fichas inactivas sin agregar desactivación, estados ni columnas.
- Programar el correo mínimo de rechazo y solicitar el despacho existente después del commit, sólo si la cuenta tiene correo verificado.
- Reutilizar el modelo C-05, la unidad de trabajo, las políticas ABAC y el adaptador de agenda de C-07. Mantener el historial de turnos ya disponible, sin duplicar su endpoint.

## Capabilities

### New Capabilities

- `patient-records`: gestión y búsqueda de fichas, lectura mínima por rol y edición autorizada, sin borrado ni desactivación.
- `patient-account-linking`: solicitudes, resolución manual, desvinculación, reactivación y recuperación de vínculos, con concurrencia y correo de rechazo.

### Modified Capabilities

- `attribute-based-access-control`: especificar el acceso a fichas y acciones de vínculo mediante el vínculo vigente y la agenda; corregir el rechazo por identificador de ficha fuera de agenda a 404 sin ampliar permisos.

## Impact

Se prevén routers/esquemas/casos de uso de pacientes y solicitudes, repositorios acotados, ampliación de puertos/UoW, integración con `RepositorioCuentas.revocar_sesiones`, `DespacharNotificacion` y plantilla de rechazo, más pruebas unitarias y PostgreSQL/API reales. El esquema inspeccionado ya satisface los campos, restricciones e índices de C-08: no se propone una migración ni dependencias nuevas.

Depende de C-04 y C-05, completados; aprovecha el adaptador de agenda C-07 ya entregado. Gobernanza **ALTO**: esta propuesta sólo prepara artefactos para revisión; no autoriza implementación. No hay pregunta Alta que bloquee el trabajo local. Q-10 no amplía la relación vigente de una cuenta con una ficha.

Fuera de alcance: UI y leyenda de notas de C-13, reserva pública C-09, barrido C-15, derechos/auditoría general C-21, cambios de JWT, historia clínica, consentimiento nuevo, borrado físico, desactivación y despliegue. El límite conocido del access token hasta su vencimiento se conserva; su ausencia de ficha en claims permite comprobar el vínculo actual en cada solicitud.
