# Discovery — Sistema de turnos y agenda para consultorios odontológicos

**Fecha**: 2026-10-02 (actualizado el 2026-10-05 con las decisiones sobre las preguntas abiertas)
**Fuentes investigadas**: 24 sistemas odontológicos de Argentina, Latinoamérica y el exterior, más 2 complementos. Detalle, tabla comparativa, matriz de puntuación y recomendación en `discovery/analisis-competitivo.md`.

## 1. Problema que resuelve

Un consultorio odontológico de 2 a 5 profesionales pierde turnos por ausencias. Confirma todo a mano por WhatsApp y por teléfono, y da sobreturnos sin control, lo que complica la atención al paciente.

## 2. Usuarios / roles

- **Administrador/dueño**: configura agendas, profesionales y reglas, y mide las ausencias.
- **Recepción**: da, mueve y confirma turnos, y autoriza sobreturnos con aviso al profesional.
- **Profesional**: ve su agenda del día con el estado de cada turno.
- **Paciente**: reserva, confirma, cancela o reprograma por su cuenta.
- **Administrativo**: facturación, cobro a obras sociales, documentación, contratos y liquidaciones. En la v1 existe solo como rol con permisos; sus funciones llegan en una etapa posterior.

## 3. Casos de uso

Los cinco bloquean la v1 y fueron confirmados.

1. Como paciente, quiero reservar, confirmar, cancelar o reprogramar mi turno por mi cuenta, para no depender de que me atiendan el teléfono.
2. Como recepción, quiero que el sistema confirme los turnos automáticamente, para no hacerlo a mano. En la v1 se cumple en parte: el correo es automático y el mensaje de WhatsApp lo prepara el sistema y lo envía recepción con un clic.
3. Como recepción, quiero que no se puedan superponer turnos de un profesional o de un box, y que los sobreturnos solo se den con autorización, para evitar el desorden en la atención.
4. Como profesional, quiero ver mi agenda del día con el estado de cada turno (confirmado, ausente, atendido), para saber a quién esperar.
5. Como administrador, quiero ver cuántos turnos se pierden por ausencias, para medir si el problema mejora.

## 4. Competidores / soluciones existentes

**Solución actual**: papel o agenda física, planilla o Google Calendar, más WhatsApp y teléfono. No hay software previo, así que la competencia real es el proceso manual.

**Mercado**: se relevaron 24 sistemas. Los cinco prioritarios para demo:

| Competidor | Problema que resuelve | Pricing | Diferenciadores |
|---|---|---|---|
| DentalCore (Argentina) | Gestión de consultorio con agenda, WhatsApp, ARCA y obras sociales | USD 50/mes en el sitio, con cifras contradictorias en otras fuentes | Localización argentina más completa declarada. Proveedor unipersonal y sin reseñas |
| DentalTec (Argentina) | Gestión para odontólogos y círculos, con foco en obras sociales | No publicado | Validación de prácticas contra obras sociales. Turnos online no evidenciados |
| Dentalink (Chile, con landing argentina) | Gestión de clínicas con agenda documentada | No publicado | Mejor documentación pública de agenda: sobreagendamiento, bloqueos y recurso por sillón |
| AgendaPro (Chile, presente en Argentina) | Reserva online y gestión para negocios de servicios, con vertical dental | CLP publicados. Pesos argentinos sin confirmar | Reserva 24/7 con seña por Mercado Pago. Clínica limitada |
| Odonthia (Argentina) | Gestión de consultorio con historia clínica y firma electrónica | Plan gratuito. Complementos desde USD 26/mes, con discrepancia de moneda | Cumplimiento legal argentino declarado |

**Notas**: casi toda la evidencia de los proveedores argentinos es marketing, no documentación verificable en uso. Como referentes de experiencia de usuario: Simples Dental (agenda por sillones, lista de espera, enlace público), Clinicorp (reagendamiento y cancelación automáticos, prevención de solapamientos) y AgendaPro (reserva 24/7 con seña).

**Vacíos del mercado argentino**: no se evidenció autogestión del paciente, lista de espera ni prevención de solapamientos en ningún proveedor local. Los precios son opacos y solo Odonthia declara la Ley 25.326.

## 5. Funcionalidades necesarias

Alcance de la v1:

- Agenda por profesional (un box fijo por profesional), con duración según la prestación y bloqueos.
- Horario semanal propio por profesional, con excepciones por fecha (feriados, vacaciones, ausencias) que bloquean la agenda.
- Catálogo inicial editable de prestaciones comunes, con duraciones sugeridas.
- Prevención de solapamientos, y sobreturnos solo con autorización.
- Reserva online por enlace público, con confirmar, cancelar y reprogramar por el paciente.
- Confirmación y recordatorios por correo automático, y por WhatsApp con mensaje preparado por el sistema que recepción envía con un clic.
- Estados del turno: pendiente, confirmado, ausente, atendido y cancelado.
- Cinco roles con permisos, incluido Administrativo (solo permisos en la v1).
- Ficha mínima de paciente: nombre y apellido, teléfono, correo, DNI, obra social como dato y notas. La reserva online pide esos mismos datos.
- Indicador de ausentismo para el administrador.

## 6. Funcionalidades opcionales

Backlog posterior, en este orden de prioridad:

1. Auditoría y consentimiento de datos conforme a la Ley 25.326 (feature planificada, diferida de la v1).
2. Lista de espera con relleno automático de huecos por cancelación.
3. Seña o pago por Mercado Pago al reservar.
4. Recall automático de controles periódicos.
5. Conversación bidireccional por la API oficial de WhatsApp Business, que incluye el envío automático de confirmaciones.
6. Facturación ARCA, cobro y liquidación con obras sociales, contratos y documentación (funciones del rol Administrativo).
7. Odontograma, periodontograma, presupuestos y planes de tratamiento.
8. Importación desde planilla o Google Calendar.

## 7. Reglas de negocio

- El sistema pide confirmación 48 horas antes del turno y manda un recordatorio 24 horas antes. Un turno que sigue sin confirmar se libera solo 12 horas antes y el hueco queda disponible. Cada consultorio puede cambiar a modo manual, donde el turno queda marcado como "sin confirmar" y recepción decide si llama o lo libera.
- El paciente puede cancelar o reprogramar por su cuenta hasta 24 horas antes del turno. Pasado ese plazo debe llamar al consultorio.
- Un profesional no puede tener dos turnos superpuestos. Cada profesional tiene un box fijo, así que alcanza con validar por profesional.
- Los sobreturnos los da recepción con aviso o aprobación del profesional afectado, y queda registrado quién los autorizó.

## 8. Integraciones

- Correo electrónico automático para confirmaciones y recordatorios, enviado por SMTP desde una cuenta de correo existente (por ejemplo Gmail con contraseña de aplicación).
- WhatsApp semimanual: el sistema arma el mensaje y recepción lo envía con un clic desde su WhatsApp. No hay API oficial en la v1, por costo por conversación y aprobación de plantillas de Meta.
- Sin integraciones con ARCA, obras sociales ni Mercado Pago en la v1.

## 9. Restricciones

- **Plazo**: entrega del MVP completo el 19-10-2026. La fecha original era el 3-10-2026 y se movió dos veces (a 12-10-2026 y luego a 19-10-2026).
- **Backend obligatorio**: Python, FastAPI, JWT para autenticación, SQLAlchemy como ORM, PostgreSQL, Redis para las funcionalidades asincrónicas que correspondan, y Docker con Docker Compose.
- **Frontend obligatorio**: React, TypeScript y Vite.
- **Presupuesto cero**: solo servicios gratuitos o con plan gratuito. El enlace público de reserva se aloja en un plan gratuito de hosting en la nube.

## 10. Riesgos

- **Plazo**: el MVP completo con backend, frontend, autenticación y recordatorios debe entrar en diez días desde el 9-10-2026, y la fecha ya se movió dos veces.
- **Supuesto sin probar**: que el paciente lea el correo de confirmación. Si no lo lee, la liberación automática le quita un turno que pensaba usar.
- **WhatsApp semimanual**: depende de que recepción envíe cada mensaje, así que no elimina por completo el trabajo manual.
- **Ley 25.326 diferida**: desde la v1 se guardan datos personales de pacientes y la ley aplica desde ese momento, aunque la auditoría y el consentimiento lleguen después.
- **Hosting y correo gratuitos**: tienen límites de envío y de disponibilidad. El correo por SMTP de una cuenta existente tiene tope diario y puede caer en spam, y el enlace público necesita un hosting en la nube accesible desde internet.
- **Mercado analizado por marketing**: casi nada de lo de los proveedores argentinos está verificado en uso. El puntaje de DentalCore (4,00) refleja lo que declara, no lo que está demostrado.

## 11. Preguntas abiertas

Ninguna pendiente. Las seis preguntas abiertas se resolvieron el 2026-10-05:

- **Hosting del enlace público**: plan gratuito de un proveedor de hosting en la nube.
- **Correo**: SMTP de una cuenta de correo existente, por ejemplo Gmail con contraseña de aplicación.
- **Datos de la reserva**: nombre y apellido, teléfono, correo, DNI y obra social.
- **Boxes, horarios y prestaciones**: un box fijo por profesional, horario semanal por profesional con excepciones por fecha, y catálogo inicial editable de prestaciones.
- **Plazos**: confirmación a las 48 horas, recordatorio a las 24 horas y liberación del turno sin confirmar a las 12 horas.
- **Planilla actual**: la importación queda diferida, sin fecha, como último punto del backlog.
