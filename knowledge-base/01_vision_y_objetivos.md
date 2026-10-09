# Visión y Objetivos

## Propósito del sistema

Sistema web de turnos y agenda para un consultorio odontológico de 2 a 5 profesionales, que reduce las ausencias, automatiza la confirmación de turnos y ordena los sobreturnos.

Hoy el consultorio gestiona la agenda en papel, planilla o Google Calendar y confirma cada turno a mano por WhatsApp y por teléfono. No hay software previo: la competencia real es el proceso manual. El problema que se ataca tiene tres síntomas: se pierden turnos por ausencias, la confirmación consume tiempo de Recepción y los sobreturnos se dan sin control, lo que complica la atención al paciente.

La versión 1 (v1) atiende **un único consultorio**. El modelo de datos queda preparado para varios consultorios (`consultorio_id` en toda tabla que pertenece a un consultorio), pero la administración multiconsultorio no forma parte de la v1 (ver [RN-55](05_reglas_de_negocio.md) a RN-57).

## Prioridades de calidad

| Prioridad | Atributo | Qué significa en este proyecto |
|-----------|----------|--------------------------------|
| 1 | Mantenibilidad | Código en capas (dominio, aplicación, infraestructura, API), reglas de negocio aisladas y probadas, políticas de acceso como funciones puras. |
| 2 | Escalabilidad | El modelo de datos admite varios consultorios (`consultorio_id`), pero solo uno está activo en la v1. No incluye alta de consultorios ni administración por consultorio. |

## Objetivos por actor

| Actor | Objetivo principal | Objetivos secundarios |
|-------|--------------------|-----------------------|
| Administrador/dueño | Medir y reducir las ausencias (caso de uso CU-5). | Configurar profesionales, horarios, prestaciones y reglas; gestionar usuarios; autorizar sobreturnos. |
| Recepción | Que el sistema confirme los turnos sin trabajo manual (CU-2) y que no haya solapamientos (CU-3). | Dar, mover y cancelar turnos; autorizar sobreturnos con aviso al profesional; enviar con un clic el mensaje de WhatsApp preparado; decidir sobre turnos sin confirmar en modo manual. |
| Profesional | Ver su agenda del día con el estado de cada turno (CU-4). | Marcar atendido o ausente en sus propios turnos; recibir el aviso de un sobreturno. |
| Paciente | Reservar, confirmar, cancelar o reprogramar su turno por su cuenta (CU-1). | Registrarse y verificar su correo desde el enlace público; recuperar su contraseña; ver sus turnos. |
| Administrativo | En la v1 solo existen el rol y sus permisos reservados. | Facturación, cobro a obras sociales, documentación, contratos y liquidaciones llegan en una etapa posterior. |

## Casos de uso confirmados

Los cinco bloquean la v1 y están confirmados. Se referencian como CU-1 a CU-5 en [06_funcionalidades.md](06_funcionalidades.md).

| Código | Caso de uso |
|--------|-------------|
| CU-1 | Como paciente, quiero reservar, confirmar, cancelar o reprogramar mi turno por mi cuenta, para no depender de que me atiendan el teléfono. |
| CU-2 | Como Recepción, quiero que el sistema confirme los turnos automáticamente, para no hacerlo a mano. En la v1 se cumple en parte: el correo es automático y el mensaje de WhatsApp lo prepara el sistema y lo envía Recepción con un clic. |
| CU-3 | Como Recepción, quiero que no se puedan superponer turnos de un profesional o de un box, y que los sobreturnos solo se den con autorización, para evitar el desorden en la atención. |
| CU-4 | Como profesional, quiero ver mi agenda del día con el estado de cada turno (confirmado, ausente, atendido), para saber a quién esperar. |
| CU-5 | Como administrador, quiero ver cuántos turnos se pierden por ausencias, para medir si el problema mejora. |

## Alcance v1

Fecha de entrega del MVP completo: **2026-10-19**. La fecha original era 2026-10-03 y se movió dos veces (al 2026-10-12 y después al 2026-10-19).

- Agenda por profesional, con un box fijo por profesional, duración variable según la prestación y bloqueos.
- Horario semanal por profesional con excepciones por fecha (feriados, vacaciones, ausencias) que bloquean la agenda.
- Catálogo inicial editable de prestaciones comunes, con duraciones sugeridas a confirmar por el consultorio.
- Prevención de solapamientos y sobreturnos solo con autorización de Recepción o Administrador, con registro del autorizante.
- Reserva online por enlace público, con confirmación, cancelación y reprogramación por el paciente hasta 24 horas antes.
- Cuenta de paciente: registro, verificación de correo, ingreso y recuperación de contraseña.
- Confirmación y recordatorios por correo automático (SMTP) y por WhatsApp semimanual (mensaje preparado, envío con un clic por Recepción).
- Estados del turno: pendiente, confirmado, ausente, atendido, cancelado, más el estado `liberado` (ver [RN-20](05_reglas_de_negocio.md)).
- Cinco roles con permisos (autorización por rol más políticas por atributos, ver [11_politicas_de_acceso_abac.md](11_politicas_de_acceso_abac.md)). Administrativo existe solo como rol.
- Ficha mínima de paciente: nombre y apellido, teléfono, correo, DNI, obra social (solo como dato) y notas.
- Indicador de ausentismo para el Administrador.

## Fuera de alcance

Backlog posterior, en este orden de prioridad:

1. Auditoría y consentimiento de datos conforme a la Ley 25.326. Es una funcionalidad planificada, diferida de la v1. Desde la v1 se almacenan datos personales de pacientes, por lo que la ley aplica desde ese momento (ver riesgo en [09](09_decisiones_y_supuestos.md)).
2. Lista de espera con relleno automático de huecos por cancelación.
3. Seña o pago por Mercado Pago al reservar.
4. Recall automático de controles periódicos.
5. Conversación bidireccional por la API oficial de WhatsApp Business, incluido el envío automático de confirmaciones.
6. Facturación ARCA, cobro y liquidación con obras sociales, contratos y documentación (funciones del rol Administrativo).
7. Odontograma, periodontograma, presupuestos y planes de tratamiento.
8. Importación desde planilla o Google Calendar (diferida, sin fecha).

Además, quedan fuera de la v1:

- Alta y administración de nuevos consultorios (multiconsultorio completo).
- Integración con obras sociales, ARCA o Mercado Pago.
- API oficial de WhatsApp Business.
- Historia clínica.

## Métricas de éxito

Las fuentes no fijan metas numéricas, por lo que no se inventan. Se definen los indicadores que el sistema debe poder medir; las metas y la línea base las define el consultorio (ver [10](10_preguntas_abiertas.md)).

| Indicador | Qué mide | Fuente en el sistema |
|-----------|----------|----------------------|
| Tasa de ausentismo | Proporción de turnos marcados `ausente` sobre los turnos cuya hora llegó (RN-45). | Estados y historial del turno. |
| Turnos liberados por falta de confirmación | Huecos generados por la liberación automática o manual. | Estado `liberado`. |
| Turnos confirmados antes del hito de liberación | Efectividad de los canales de confirmación. | `confirmado_en` y notificaciones. |
| Trabajo manual de confirmación | Mensajes de WhatsApp que Recepción aún debe enviar. | Notificaciones del canal WhatsApp. |
| Sobreturnos autorizados | Control del uso de sobreturnos. | Registro de autorizaciones de sobreturno. |

## Referencia de mercado

Se relevaron 24 sistemas odontológicos (detalle en `discovery/analisis-competitivo.md`). Casi toda la evidencia de proveedores argentinos es material comercial no verificado en uso. Los vacíos que este proyecto aprovecha: no se evidenció autogestión del paciente, lista de espera ni prevención de solapamientos en proveedores locales. Los referentes de experiencia de usuario son Simples Dental (agenda por sillones, enlace público), Clinicorp (reagendamiento y cancelación automáticos, prevención de solapamientos) y Dentalink (mejor documentación pública de agenda: sobreagendamiento y bloqueos).
