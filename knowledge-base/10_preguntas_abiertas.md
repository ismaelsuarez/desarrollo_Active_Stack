# Preguntas Abiertas

Solo se listan vacíos reales que quedan luego de las decisiones confirmadas. No se repiten las seis preguntas ya resueltas el 2026-10-05 (hosting, correo, datos de reserva, boxes y horarios, plazos de confirmación, importación de la planilla actual) ni las decisiones de la fase de base de conocimiento (cuenta del paciente, RBAC más ABAC, canales, estados). La exploración técnica verificada (`discovery/exploracion-tecnica.md`, 2026-10-05, aplicada el 2026-10-06) resolvió la arquitectura de hosting (Q-02) y abrió las preguntas Q-23 a Q-29; lo no verificado (`[NV]`) figura como pregunta o como suposición en [09](09_decisiones_y_supuestos.md).

Columnas: **Bloquea** indica qué parte del trabajo no puede cerrarse sin la respuesta. **Decisor** indica quién debe responder. Entre paréntesis, la regla o supuesto afectado.

## Inconsistencias detectadas

### IN-01 — Alcance de la v1 frente al plazo
**Documento A dice**: el alcance incluye ocho funcionalidades más la cuenta de paciente (registro, verificación de correo, ingreso, recuperación de contraseña) ([01](01_vision_y_objetivos.md), [06](06_funcionalidades.md)).
**Documento B dice**: el MVP completo debe entregarse el 2026-10-19, diez días después de la actualización del 2026-10-09, y la fecha original ya se movió dos veces (`discovery/discovery.md`, riesgos).
**Impacto**: si no se llega, no hay criterio acordado de qué se recorta.
**Resolución (2026-10-12)**: no se recorta ni se mueve la fecha; la entrega es en dos partes (DD-22 en [09](09_decisiones_y_supuestos.md)). El 2026-10-19 se entregan los changes completos y verificados a esa fecha y el resto va en la segunda parte.

### IN-02 — "Resueltas todas las preguntas" frente a vacíos de diseño
**Documento A dice**: el discovery cierra con "ninguna pendiente".
**Documento B dice**: al detallar reglas, modelo y flujos aparecen vacíos que el discovery no cubría (hitos vencidos, aprobación del profesional, vinculación de fichas, entre otros).
**Impacto**: implementar con supuestos no validados.
**Resolución propuesta**: validar cada pregunta de prioridad alta de esta lista con el consultorio y el equipo antes del primer change cuyo propio alcance bloquea (columna Bloquea); las del entorno publicado (Q-23 a Q-27 y Q-29) no bloquean los changes que se construyen y prueban en local, que son todos salvo C-20 (DD-31).

### IN-03 — Estados del turno y marca "sin confirmar"
**Documento A dice**: el discovery lista cinco estados y menciona la marca "sin confirmar" del modo manual.
**Documento B dice**: esta base agrega el estado `liberado` y modela "sin confirmar" como marca y no como estado (RN-20, RN-28).
**Impacto**: la presentación al consultorio podría esperar ver "sin confirmar" como estado.
**Resolución propuesta**: mostrar "sin confirmar" como etiqueta visible sobre un turno `pendiente` y validar con Recepción.

## Preguntas abiertas (priorizadas)

| ID | Prioridad | Pregunta | Bloquea | Decisor |
|----|-----------|----------|---------|---------|
| Q-01 | Resuelta (2026-10-12) | ~~Si el plazo del 2026-10-19 no alcanza, ¿qué funcionalidades de la v1 se recortan primero y en qué orden?~~ Resuelta por el dueño del proyecto: no se recorta; la entrega es en dos partes y la primera contiene los changes completos y verificados al 2026-10-19, en el orden de `CHANGES.md` (DD-22). | — | Product Owner |
| Q-02 | Resuelta (2026-10-06) | ~~¿Qué proveedor gratuito de hosting se usa? Debe admitir procesos persistentes (API y worker), PostgreSQL y Redis (o una alternativa), HTTPS y salida SMTP, y no dormirse por inactividad.~~ Resuelta en cuanto a la arquitectura: ese conjunto de requisitos es inalcanzable en un plan gratuito sin tarjeta entre lo verificado; se adopta la arquitectura base de DD-13 (frontend en Cloudflare Pages, API con barrido en proceso, PostgreSQL en Neon, disparador externo). Ver DD-13, DD-10, SU-01 y SU-26 en [09](09_decisiones_y_supuestos.md) y [12](12_devops_y_despliegue.md). Lo que sigue abierto del proveedor se desglosa en Q-23 a Q-29. | Nada (resuelta) | Equipo técnico |
| Q-03 | Resuelta (2026-10-12) | ~~¿Qué ocurre con un turno creado o reprogramado cuando ya pasó el hito de 48 h, 24 h o 12 h? ¿Se libera, queda "sin confirmar" o se considera confirmado de entrada? (RN-29, SU-11)~~ Resuelta por el dueño del proyecto: con menos de `horas_confirmacion` de anticipación el turno nace `confirmado`; no se le pide confirmación ni se libera solo (DD-32). | — | Product Owner con Recepción |
| Q-04 | Resuelta (2026-10-12) | ~~¿Un sobreturno requiere la aprobación del profesional afectado (puede vetarlo) o alcanza con avisarle? (RN-40, SU-17)~~ Resuelta por el dueño del proyecto: alcanza con avisarle; su respuesta se registra y no bloquea (DD-30). | — | Administrador y profesionales |
| Q-05 | Resuelta (2026-10-11) | ~~¿Cómo se vincula un paciente que se registra con un DNI que Recepción ya cargó? ¿Es aceptable la vinculación manual por Recepción? (RN-49, SU-21)~~ Resuelta por el dueño del proyecto: el sistema crea la cuenta sin crear una segunda ficha y guarda una solicitud de vinculación con el DNI declarado; la respuesta del registro es idéntica exista o no el DNI; Recepción verifica la identidad y vincula o rechaza. Costo aceptado: ese paciente no reserva en línea hasta que Recepción vincule su cuenta; tras un rechazo, Recepción puede vincularla con la ficha correcta o crear una ficha nueva, y puede desvincular una cuenta de una ficha y reactivar una ficha inactiva (DD-20). La respuesta idéntica del registro no cierra del todo la fuga de pertenencia: el dueño la aceptó y se acota con un límite por origen (definido en DD-21), la visibilidad solo con correo verificado y el registro de cada solicitud. Ver DD-19 a DD-21 y SU-21 en [09](09_decisiones_y_supuestos.md), RN-49 y RN-62 en [05](05_reglas_de_negocio.md) y flujo 1 en [07](07_flujos_principales.md). | Nada (resuelta) | Product Owner |
| Q-06 | Resuelta (2026-10-12) | ~~¿Con qué granularidad se ofrecen los horarios de inicio de turno y puede Recepción ajustar la duración de un turno puntual? (RN-13)~~ Resuelta por el dueño del proyecto: cada 15 minutos, configurable, y Recepción y Administrador ajustan la duración en múltiplos de esa unidad (DD-27, RN-64). | — | Administrador |
| Q-07 | Media | ¿Es aceptable que el correo incluya un enlace de un solo uso que confirma el turno sin ingresar contraseña? (RN-30, SU-12) | Flujo de confirmación | Product Owner |
| Q-08 | Media | ¿Qué prestaciones realiza cada profesional? ¿Todos atienden todo el catálogo? (SU-24) | Modelo de datos y disponibilidad | Administrador |
| Q-09 | Media | ¿Las duraciones sugeridas del catálogo inicial son correctas? Deben confirmarlas los profesionales. (RN-13, SU-23) | Datos semilla | Administrador y profesionales |
| Q-10 | Media | ¿Puede un paciente reservar para otra persona (hijo, familiar) desde su cuenta? | Modelo de paciente y cuenta | Product Owner |
| Q-11 | Resuelta (2026-10-12) | ~~¿Hasta con cuánta anticipación puede reservar un paciente y cuántos turnos futuros activos puede tener?~~ Resuelta por el dueño del proyecto: 60 días y 2 turnos, configurables; no rigen para Recepción ni Administrador (DD-27, RN-64). | — | Administrador |
| Q-12 | Media | ¿Quién gestiona los bloqueos de urgencia (por ejemplo, un profesional que avisa que falta hoy)? ¿Solo el Administrador o también Recepción? (SU-34) | Permisos de Recepción | Administrador |
| Q-13 | Media | ¿Cómo se cargan los feriados: manualmente cada año o desde una fuente oficial? (SU-30) | Configuración inicial | Equipo técnico |
| Q-14 | Resuelta (2026-10-12) | ~~¿El Administrador atiende también como profesional, de modo que necesite dos roles en una misma cuenta? (RN-08, SU-07)~~ Resuelta por el dueño del proyecto: un rol por usuario, y la agenda del profesional puede vincularse a una cuenta de administrador (DD-24). | — | Administrador |
| Q-15 | Media | ¿Cómo debe calcularse y presentarse el indicador de ausentismo (fórmula, períodos, qué hacer con turnos pasados sin marcar)? (RN-45, SU-16) | Indicador de ausentismo | Administrador |
| Q-16 | Resuelta (2026-10-12) | ~~¿Cuáles son las políticas de seguridad de cuenta: vigencia de los enlaces de verificación y recuperación, duración de sesiones, requisitos de contraseña y límite de intentos fallidos? (RN-03, RN-09)~~ Resuelta por el dueño del proyecto con los valores de DD-25. | — | Equipo técnico |
| Q-17 | Media | ¿Cuál es el plazo de conservación de los datos de pacientes y cómo se atiende un pedido de supresión mientras la auditoría y el consentimiento de la Ley 25.326 estén diferidos? (RN-58) | Cumplimiento legal | Administrador, con asesoramiento legal |
| Q-18 | Baja | ¿Cuál es el nombre, el teléfono y la dirección del consultorio que se muestran en el enlace público y en los mensajes? | Datos de configuración inicial | Administrador |
| Q-19 | Baja | ¿Los textos de los correos y de los mensajes de WhatsApp tienen una redacción acordada (tono, firma)? (RN-54) | Plantillas de mensajes | Administrador y Recepción |
| Q-20 | Baja | ¿Hay un máximo de sobreturnos simultáneos por profesional y puede otorgarse un sobreturno fuera del horario semanal? (RN-43, SU-18) | Reglas de sobreturno | Administrador |
| Q-21 | Baja | ¿Cuánto tiempo conviene esperar antes de reintentar un correo fallido y cuántos reintentos se aceptan? (RN-31) | Notificaciones | Equipo técnico |
| Q-22 | Baja | ¿Se desea una línea base de ausentismo previa a la puesta en marcha para medir la mejora (CU-5) y qué meta numérica se espera? | Métricas de éxito de [01](01_vision_y_objetivos.md) | Administrador |
| Q-23 | Alta | ¿Qué proveedor de correo o API HTTPS de correo se permite desde el host elegido para la API? Render gratuito bloquea los puertos SMTP 25, 465 y 587; no se verificó ninguna API HTTPS de correo ni su plan gratuito, ni que otro host gratuito permita SMTP saliente (DD-06, SU-37). | Envío de correo real (verificación, confirmación, recordatorio, liberación) en el entorno publicado. Bloquea C-15, C-16 y C-20 antes de enviar correo real; no bloquea C-05, que en local y en CI usa Mailpit | Equipo técnico |
| Q-24 | Alta | ¿Qué servicio web gratuito aloja la API? Los criterios están en [12](12_devops_y_despliegue.md) (suspensión por inactividad, salida SMTP, dominio, secretos). Koyeb ofrece un servicio web gratuito pero su escalado a cero es contradictorio (`[NV]`); Render se duerme a los 15 minutos y bloquea SMTP (DD-10, DD-13). | Despliegue publicado. Bloquea C-20; C-05, C-14 y C-15 solo lo mencionan como riesgo del despliegue | Equipo técnico |
| Q-25 | Alta | ¿Quién opera el disparador externo del barrido (por ejemplo `schedule` de GitHub Actions, con intervalo mínimo de 5 minutos, o un cron trigger de Cloudflare Workers) y cómo se guarda y rota el secreto compartido? (DD-13, SU-38) | Barrido de hitos, recordatorios y liberación automática. Bloquea C-15, C-16 y C-20 | Equipo técnico |
| Q-26 | Alta | ¿Está habilitable `btree_gist` en el proveedor de PostgreSQL elegido? Figura como soportado en Neon (verificado el 2026-10-05); en Supabase no se verificó (SU-28, SU-40). | Restricción de no solapamiento (DD-08) en el PostgreSQL publicado. Bloquea C-20; C-01 y C-07 no la esperan, porque en local y en CI PostgreSQL corre como superusuario y `btree_gist` funciona | Equipo técnico |
| Q-27 | Alta | ¿Alcanzan las 100 CU-h por mes de Neon con un barrido cada 5 minutos, dado que el cómputo se suspende a los 5 minutos de inactividad? ¿Conviene un intervalo mayor y qué impacto tiene en la precisión de los hitos? (SU-38) | Intervalo del barrido y disponibilidad de la base. Bloquea C-15, C-16 y C-20 | Equipo técnico |
| Q-28 | Resuelta (2026-10-12) | ~~¿Qué estrategia se usa para la cookie `HttpOnly` de renovación con el frontend en Cloudflare Pages y la API en otro dominio?~~ Resuelta por el dueño del proyecto: frontend y API en el mismo origen, la API sirve el frontend compilado y la cookie es propia con `SameSite=Strict` (DD-26). | — | Equipo técnico |
| Q-29 | Alta | ¿El docente o el plan de la asignatura exige desplegar el stack completo (API, PostgreSQL, Redis y proceso persistente)? Si sí, la alternativa es Compose en una VM propia (por ejemplo Oracle Always Free, con condiciones no verificadas) (DD-01, DD-13). | Arquitectura de despliegue. Bloquea C-20; C-01 no cambia | Product Owner |

## Resumen de dependencias con el plan

| Pregunta | Primer trabajo que la necesita |
|----------|--------------------------------|
| Q-01 | Resuelta (DD-22); la entrega es en dos partes |
| Q-02 | Resuelta; el seguimiento está en Q-23 a Q-29 |
| Q-23, Q-24, Q-25, Q-29 | Despliegue mínimo de prueba (host de la API, correo, disparador); son del entorno publicado y bloquean C-20. C-15 y C-16 se construyen y prueban en local con Mailpit y el bucle propio del barrido, sin esperarlas (DD-31) |
| Q-28 | Resuelta (DD-26); el seguimiento está en C-03, C-11 y C-20 |
| Q-26 | Despliegue en Neon (C-20). La primera migración local y la de CI no la necesitan: PostgreSQL corre como superusuario y `btree_gist` funciona |
| Q-27 | Operación del barrido en Neon: bloquea C-20; C-15 y C-16 no la esperan en local (DD-31) |
| Q-03 | Resuelta (DD-32); el seguimiento está en C-07, C-09 y C-16 |
| Q-06, Q-11 | Resueltas (DD-27); el seguimiento está en C-02, C-07, C-09 y C-12 |
| Q-04 | Resuelta (DD-30); el seguimiento está en C-10 |
| Q-05 | Resuelta (DD-19 a DD-21); el seguimiento está en C-05, C-08 y C-09 |
| Q-10 | Cuentas, pacientes y registro |
| Q-14 | Resuelta (DD-24); el seguimiento está en C-04, C-06, C-10 y C-13 |
| Q-07 | Confirmación y notificaciones |
| Q-08, Q-09, Q-13, Q-18 | Configuración y datos semilla |
