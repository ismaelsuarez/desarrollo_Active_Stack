# Decisiones y Supuestos

Distingue entre lo **decidido y confirmado** por el usuario (decisiones DD) y lo **inferido o propuesto** sin confirmación (supuestos SU, marcados como `**Suposición:**`). Los supuestos deben validarse; las dudas reales pasan a [10](10_preguntas_abiertas.md).

Fuentes: `discovery/discovery.md` (Discovery confirmado, 2026-10-05), las decisiones confirmadas por el usuario en la fase de base de conocimiento, que prevalecen cuando difieren, y `discovery/exploracion-tecnica.md` (exploración técnica verificada, consulta del 2026-10-05, aplicada con aprobación del usuario el 2026-10-06).

Convención de revisión: las decisiones y supuestos que cambiaron con la exploración técnica conservan su identificador. El texto anterior se marca como **Reemplazado el 2026-10-06** y se agrega el texto vigente. En la exploración, `[V]` indica lo leído en documentación o página oficial y `[NV]` lo no verificado; lo `[NV]` figura aquí solo como `**Suposición:**` o como pregunta abierta, nunca como hecho.

## Decisiones documentadas

### DD-01 — Aplicación web con stack obligatorio
**Decisión**: sistema web con frontend React, TypeScript y Vite, y backend Python con FastAPI, JWT, SQLAlchemy, PostgreSQL, Redis (para las funcionalidades asincrónicas que correspondan), Docker y Docker Compose.
**Contexto**: restricción del proyecto, con presupuesto cero y entrega del MVP completo el 2026-10-12 (la fecha original era el 2026-10-03).
**Alternativas consideradas**: no se evaluaron alternativas; el stack es una restricción.
**Justificación**: viene dado por el proyecto.
**Trade-offs aceptados**: sin libertad de elegir tecnología; plazo de siete días desde el 2026-10-05 para backend, frontend, autenticación y recordatorios.

### DD-02 — Mantenibilidad primero, escalabilidad después
**Decisión**: prioridad 1 mantenibilidad, prioridad 2 escalabilidad. Escalabilidad significa modelo de datos preparado para varios consultorios (`consultorio_id` en toda tabla de un consultorio) con un solo consultorio activo en la v1.
**Contexto**: el equipo debe entregar rápido y mantener el sistema; el multiconsultorio completo no es un requisito de la v1.
**Alternativas consideradas**: (a) modelo de un solo consultorio sin `consultorio_id`; (b) multiconsultorio completo con alta y administración por consultorio.
**Justificación**: agregar `consultorio_id` ahora es barato; hacerlo después obliga a migrar todas las tablas y consultas. El multiconsultorio completo no cabe en el plazo.
**Trade-offs aceptados**: un filtro más en cada consulta y en cada política; sin onboarding de consultorios.

### DD-03 — Cuenta propia del paciente con verificación de correo
**Decisión**: el paciente tiene cuenta (usuario y contraseña), se registra desde el enlace público, debe verificar su correo, y existe recuperación de contraseña en la v1. El rol `paciente` va en los claims del JWT junto con los del personal.
**Contexto**: el paciente debe poder confirmar, cancelar y reprogramar por su cuenta (CU-1).
**Alternativas consideradas**: reserva sin cuenta con enlaces firmados por turno; ingreso solo por código enviado al correo.
**Justificación**: decisión del usuario. Una cuenta permite listar los turnos propios y aplicar políticas por propietario.
**Trade-offs aceptados**: más superficie de seguridad (registro, verificación, recuperación) y más trabajo dentro del plazo; mayor fricción para reservar que sin cuenta.

### DD-04 — Autorización: RBAC más ABAC como funciones de política
**Decisión**: roles más funciones de política, sin motor genérico. Cuatro atributos en la v1: propietario del recurso, consultorio, estado del turno y ventana temporal. Detalle en [11](11_politicas_de_acceso_abac.md).
**Contexto**: cinco roles y reglas que dependen del recurso y del tiempo (por ejemplo, un profesional solo toca su agenda; un turno atendido no se edita).
**Alternativas consideradas**: solo RBAC; motor de políticas genérico externo o declarativo.
**Justificación**: solo RBAC no expresa las reglas por recurso; un motor genérico es sobredimensionado para el plazo y el tamaño del equipo.
**Trade-offs aceptados**: las políticas están en código y hay que probarlas; cambiar una regla implica un cambio de código.

### DD-05 — Estado adicional `liberado`
**Decisión**: se agrega el estado `liberado` a los cinco estados del discovery (pendiente, confirmado, ausente, atendido, cancelado).
**Contexto**: el turno sin confirmar se libera automáticamente 12 horas antes (o manualmente en modo manual).
**Alternativas consideradas**: reutilizar `cancelado` con un motivo.
**Justificación**: permite medir cuántos turnos se pierden por falta de confirmación y cuántos por cancelación, y avisar al paciente la causa (RN-20). Se confirmó que se puede agregar si se justifica.
**Trade-offs aceptados**: una transición y un estado más que probar y mostrar.

### DD-06 — Canales de comunicación de la v1
**Decisión (vigente, actualizada el 2026-10-06)**: correo automático desde una cuenta existente por SMTP (por ejemplo Gmail con contraseña de aplicación), implementado con `EmailMessage` de la biblioteca estándar y `aiosmtplib` detrás del puerto `EnviadorCorreo`, por el puerto 587 con STARTTLS; y WhatsApp semimanual (el sistema prepara el mensaje y Recepción lo envía con un clic). Sin API oficial de WhatsApp, ARCA, obras sociales ni Mercado Pago. Condiciones verificadas (`discovery/exploracion-tecnica.md`, sección 5 y sección 7): Gmail personal admite 500 correos por día (con bloqueo de entre 1 y 24 horas al excederlo; Workspace admite 2.000) y el sistema alerta al 80 %; la contraseña de aplicación exige verificación en dos pasos y no está disponible con Protección Avanzada ni con cuentas de trabajo o institución; el servicio web gratuito de Render bloquea la salida por los puertos 25, 465 y 587, de modo que desde ese host Gmail por SMTP no es utilizable. Ver SU-37 y Q-23.
**Reemplazado el 2026-10-06 (texto anterior)**: "correo automático por SMTP desde una cuenta existente (por ejemplo Gmail con contraseña de aplicación)", sin condiciones verificadas de puerto, tope ni tipo de cuenta, y asumiendo que el hosting permitía SMTP por 587 o 465.
**Contexto**: presupuesto cero; la API de WhatsApp Business tiene costo por conversación y exige aprobación de plantillas de Meta.
**Alternativas consideradas**: API oficial de WhatsApp; servicios de correo transaccional con plan gratuito.
**Justificación**: es la opción sin costo que cumple el caso de uso en parte (CU-2).
**Trade-offs aceptados**: el WhatsApp depende de que Recepción envíe cada mensaje; el correo tiene tope diario (500 por día en Gmail personal) y puede caer en spam; si el host bloquea SMTP puede hacer falta una API HTTPS de correo, no verificada (SU-37).

### DD-07 — Un box fijo por profesional y validación por profesional
**Decisión**: cada profesional tiene un box fijo; basta validar solapamientos por profesional.
**Contexto**: el discovery hablaba de evitar solapamientos "de un profesional o de un box".
**Alternativas consideradas**: modelar boxes compartidos con agenda por recurso.
**Justificación**: con un box fijo por profesional ambas validaciones coinciden (RN-10).
**Trade-offs aceptados**: compartir boxes sería un cambio de modelo, no de configuración.

### DD-08 — La garantía de no solapamiento vive en la base de datos
**Decisión**: restricción de exclusión de PostgreSQL por profesional sobre el rango del turno, excluyendo sobreturnos y turnos cancelados o liberados (ver [04](04_modelo_de_datos.md)).
**Contexto**: reservas concurrentes del enlace público y de Recepción.
**Alternativas consideradas**: validar solo en la aplicación; bloqueo explícito de filas.
**Justificación**: elimina condiciones de carrera con una regla declarativa (RN-24).
**Trade-offs aceptados**: requiere una extensión de PostgreSQL (SU-28) y traducir el error de la base a un mensaje de usuario.
**Implementación (actualizada el 2026-10-06, `discovery/exploracion-tecnica.md` secciones 1 y 2)**: la restricción se declara en el modelo (`ExcludeConstraint`) y se crea a mano en la migración, después de `CREATE EXTENSION IF NOT EXISTS btree_gist`, porque el autogenerate de Alembic no detecta restricciones EXCLUDE. Un test de integración inserta dos turnos solapados. El adaptador del repositorio traduce el error de exclusión a "horario ocupado" (ver DD-14 y SU-39).

### DD-09 — Orden del backlog y Ley 25.326 diferida
**Decisión**: backlog en este orden: auditoría y consentimiento Ley 25.326, lista de espera, Mercado Pago, recall, API oficial de WhatsApp, facturación y funciones del Administrativo, odontograma y presupuestos, importación.
**Contexto**: el plazo no permite todo en la v1.
**Alternativas consideradas**: incluir la auditoría y el consentimiento en la v1.
**Justificación**: decisión del usuario sobre prioridades.
**Trade-offs aceptados**: desde la v1 se guardan datos personales y la ley aplica desde ese momento; se mitiga con el mínimo de RN-58 y queda registrado como riesgo.

### DD-10 — Presupuesto cero y alojamiento del enlace público
**Decisión (vigente, actualizada el 2026-10-06)**: solo servicios gratuitos; el enlace público de reserva se aloja en un plan gratuito de hosting en la nube con la arquitectura base de DD-13. El proveedor del servicio web de la API sigue por definir (Q-24).
**Contexto**: restricción del proyecto.
**Alternativas consideradas**: no aplica a la restricción; las alternativas de topología están en DD-13.
**Justificación**: restricción del proyecto.
**Trade-offs aceptados (vigentes)**: límites de disponibilidad y de recursos con cifras verificadas el 2026-10-05 (`discovery/exploracion-tecnica.md`, sección 7): el servicio web gratuito de Render se duerme a los 15 minutos, su Postgres gratuito de 1 GB expira a los 30 días y no hay worker ni cron gratuitos; Neon ofrece 1 GB permanente, 100 CU-h por mes y suspensión a los 5 minutos; Upstash Redis ofrece 500.000 comandos por mes; Fly.io no tiene plan gratuito. Las cifras cambian con el tiempo y algunas se leyeron con extractores automáticos: contrastarlas antes de comprometer el plan ([12](12_devops_y_despliegue.md)).
**Reemplazado el 2026-10-06 (texto anterior)**: "límites de disponibilidad y de recursos (sin cifras verificadas), posible inactividad del servicio y dependencia de lo que ofrezca el proveedor".

### DD-11 — Sin borrado físico y trazabilidad de estados
**Decisión**: turnos, pacientes y usuarios no se borran; cambian de estado o se desactivan, y los cambios de estado quedan en `turno_historial`.
**Contexto**: el indicador de ausentismo y las reglas dependen del historial; además se manejan datos personales.
**Alternativas consideradas**: borrado físico o lógico solo con bandera.
**Justificación**: preserva la trazabilidad y las métricas.
**Trade-offs aceptados**: crecimiento de datos; el derecho de supresión de datos personales queda para la fase de la Ley 25.326.

### DD-12 — Autenticación y autorización: PyJWT, Argon2 y RBAC más ABAC en capas
**Decisión**: tokens con PyJWT (HS256) y contraseñas con pwdlib usando Argon2, según el tutorial oficial de FastAPI (`discovery/exploracion-tecnica.md`, sección 3, [V]). RBAC como fábricas de dependencias de FastAPI y ABAC como funciones de política puras invocadas desde los casos de uso. Los repositorios reciben `consultorio_id` desde el `Principal`, nunca desde el cliente. El ingreso compara contra un hash ficticio cuando el usuario no existe para igualar tiempos (práctica del tutorial).
**Contexto**: [08](08_arquitectura_propuesta.md) dejaba "Argon2 o bcrypt, a elegir"; la exploración permite fijar la elección.
**Alternativas consideradas**: otros algoritmos de hash y otras bibliotecas de JWT; no se evaluaron porque el tutorial oficial usa PyJWT y pwdlib con Argon2.
**Justificación**: sigue el tutorial oficial de FastAPI, que reduce el riesgo de errores de implementación; refuerza DD-04 y RN-06.
**Trade-offs aceptados**: HS256 usa una clave simétrica que comparten quien firma y quien valida (aceptable con una sola API); la clave `JWT_SECRET_KEY` pasa a ser un secreto crítico.

### DD-13 — Arquitectura de despliegue base con barrido en proceso
**Decisión**: frontend estático en Cloudflare Pages; API con un barrido idempotente en proceso en un servicio web gratuito; PostgreSQL en Neon (`btree_gist` figura como soportado, [V]); Redis opcional (Upstash) o sustituido por el candado de PostgreSQL (`pg_try_advisory_lock` o `SELECT ... FOR UPDATE SKIP LOCKED`); un disparador HTTP externo cada 5 minutos que llama a `POST /internal/barrido` autenticado con un secreto compartido. La tabla `notificacion` sigue siendo la fuente de verdad y el barrido es idempotente. El puerto `Planificador` oculta el disparador. Docker Compose se mantiene como entorno local y de desarrollo y como alternativa si se exige el stack completo en una VM propia (`discovery/exploracion-tecnica.md`, secciones 4 y 7).
**Contexto**: entre lo verificado no existe un stack gratuito con API, PostgreSQL, Redis y un proceso aparte siempre activo en un único PaaS sin tarjeta.
**Alternativas consideradas**: (a) todo en un proveedor, descartada por lo anterior; (b) ARQ, RQ o Celery sobre Redis: ARQ es el mejor ajuste técnico si se exige una librería, pero está en modo de mantenimiento desde 2025-10-18; RQ no tiene soporte asyncio documentado; (c) Compose en una VM propia (Oracle Always Free, con condiciones no verificadas), vigente como alternativa.
**Justificación**: es la arquitectura menos mala entre las opciones verificadas, cumple el presupuesto cero de DD-10 y conserva el diseño de SU-26 (la base de datos como fuente de verdad y el barrido idempotente).
**Trade-offs aceptados**: el barrido depende de un disparador externo (Q-25); con el servicio dormido los hitos pueden retrasarse; cuotas de Neon y de Upstash a respetar (Q-27); más de un proveedor implica CORS y cookies entre dominios (SU-27, Q-28). Reemplaza la contingencia "opción C" de la versión anterior de [12](12_devops_y_despliegue.md), que pasa a ser la base.

### DD-14 — Acceso a datos asíncrono y migraciones con un único head
**Decisión**: SQLAlchemy 2.x asíncrono con asyncpg y `async_sessionmaker(engine, expire_on_commit=False)`; la restricción de exclusión se crea a mano en la migración tras `CREATE EXTENSION IF NOT EXISTS btree_gist` y se cubre con un test de integración que inserta dos turnos solapados; el adaptador del repositorio traduce el error de exclusión a "horario ocupado" (SU-39); historia de Alembic lineal con un único head, verificada en CI con `alembic heads`, aplicada con `alembic upgrade head` (nunca `heads`) y `compare_type=True`.
**Contexto**: el autogenerate de Alembic no detecta restricciones EXCLUDE ni restricciones sin nombre; dos revisiones con el mismo padre producen varios heads y `alembic upgrade head` falla (`discovery/exploracion-tecnica.md`, secciones 1 y 2, [V]).
**Alternativas consideradas**: confiar en el autogenerate (descartada por lo anterior); validar solo en la aplicación (ver DD-08).
**Justificación**: mantiene la garantía de DD-08 reproducible y verificable.
**Trade-offs aceptados**: parte del esquema se escribe a mano y hay que vigilar las ramas de migraciones.

### DD-15 — Docker Compose: esquema actualizado
**Decisión**: sin clave `version` (obsoleta); `healthcheck` en la API y `depends_on` con `service_healthy` y `service_completed_successfully`; `restart: unless-stopped` en los servicios de ejecución prolongada; `mailpit` bajo el perfil `dev`; secretos desde archivos montados en `/run/secrets/<nombre>` o desde el almacén de secretos del host (`discovery/exploracion-tecnica.md`, sección 6, [V]).
**Contexto**: el esquema de [12](12_devops_y_despliegue.md) era ilustrativo y no incluía todo lo anterior.
**Alternativas consideradas**: variables de entorno planas para todos los secretos (menos seguro).
**Justificación**: buenas prácticas verificadas en la referencia oficial de Compose.
**Trade-offs aceptados**: algo más de configuración inicial.

## Supuestos inferidos

Los siguientes son propuestas técnicas o de producto que el usuario **no confirmó**. Se tratan como válidas hasta que se validen o se corrijan. Los seis primeros (SU-01 a SU-06) son sugerencias técnicas explícitas del encargo.

### SU-01 — Trabajos programados con barrido en proceso (revisado el 2026-10-06)
**Suposición (vigente, 2026-10-06):** los recordatorios, las solicitudes de confirmación y la liberación automática se ejecutan como un barrido idempotente dentro del proceso de la API, disparado por una llamada HTTP externa cada 5 minutos a `POST /internal/barrido` (ver DD-13). Redis es opcional.
**Reemplazado el 2026-10-06 (texto anterior):** "los recordatorios, las solicitudes de confirmación y la liberación automática se ejecutan como trabajos programados en un proceso worker que usa Redis", en un hosting que admitiera procesos persistentes y no se durmiera. Según `discovery/exploracion-tecnica.md` (sección 7) eso es inalcanzable en un hosting gratuito sin tarjeta entre lo verificado; la opción de barrido en proceso pasó de contingencia a base.
**Origen**: sugerencia técnica del encargo, corregida con la exploración técnica verificada.
**Riesgo si es falso**: si se exige el stack completo (API, PostgreSQL, Redis y proceso persistente), la alternativa es Compose en una VM propia (Q-29).
**Cómo validar**: confirmar con el proveedor elegido (Q-24) cómo se comporta el servicio dormido ante el disparador y quién opera el disparador (Q-25).

### SU-02 — Zona horaria `America/Argentina/Buenos_Aires`
**Suposición:** toda la operación usa la zona `America/Argentina/Buenos_Aires`; los instantes se guardan en UTC.
**Origen**: sugerencia técnica del encargo.
**Riesgo si es falso**: horarios mal calculados en hitos y disponibilidad.
**Cómo validar**: confirmar que el consultorio opera en esa zona.

### SU-03 — Backend en capas / hexagonal
**Suposición:** el backend se organiza en `domain`, `application`, `infrastructure` y `api`.
**Origen**: sugerencia para servir a la mantenibilidad (prioridad 1).
**Riesgo si es falso**: otra estructura sería viable; el costo de la capa extra puede sentirse con el plazo corto.
**Cómo validar**: revisar el primer change de implementación; si la capa de aplicación resulta pesada, simplificarla sin romper el aislamiento del dominio.

### SU-04 — Frontend con contenedor/presentacional y diseño atómico
**Suposición:** componentes organizados en átomos, moléculas, organismos y plantillas, con contenedores que obtienen datos y componentes presentacionales que solo pintan.
**Origen**: sugerencia técnica del encargo.
**Riesgo si es falso**: organización distinta de la interfaz.
**Cómo validar**: revisar con la primera pantalla implementada.

### SU-05 — Idioma de la interfaz: español (Argentina)
**Suposición:** toda la interfaz y los correos están en español de Argentina.
**Origen**: sugerencia técnica del encargo.
**Riesgo si es falso**: textos a reescribir.
**Cómo validar**: confirmar con el consultorio.

### SU-06 — API documentada con el OpenAPI de FastAPI
**Suposición:** la documentación de la API es el OpenAPI generado por FastAPI; `/docs` se habilita en desarrollo y se restringe en producción.
**Origen**: sugerencia técnica del encargo; la restricción en producción es una decisión de seguridad propuesta.
**Riesgo si es falso**: ninguno relevante; solo exposición de documentación si se deja pública.
**Cómo validar**: revisar la variable `OPENAPI_DOCS_ENABLED` al desplegar.

### SU-07 — Un rol por usuario
**Suposición:** cada usuario tiene un único rol (RN-08).
**Origen**: el discovery lista roles distintos sin acumulación; el dueño podría atender como profesional.
**Riesgo si es falso**: un administrador que también atiende necesitaría dos cuentas o un modelo de varios roles.
**Cómo validar**: preguntar si el dueño también atiende pacientes.

### SU-08 — El personal no se autorregistra
**Suposición:** el Administrador crea las cuentas de personal (RN-07).
**Origen**: solo el paciente se registra desde el enlace público según las decisiones.
**Riesgo si es falso**: habría que habilitar invitaciones o altas diferentes.
**Cómo validar**: confirmar el procedimiento de alta de Recepción y profesionales.

### SU-09 — Identificador de ingreso: nombre de usuario
**Suposición:** el ingreso se hace con `nombre_usuario` y contraseña; el correo es único y sirve para verificación y recuperación.
**Origen**: las decisiones indican "usuario y contraseña".
**Riesgo si es falso**: si se prefiere ingresar con el correo, cambia el formulario y la unicidad.
**Cómo validar**: confirmar con el consultorio al diseñar el registro.

### SU-10 — Estado `liberado` además de los cinco confirmados
**Suposición:** el estado `liberado` es suficiente para modelar la liberación; la marca "sin confirmar" del modo manual es un dato y no un estado.
**Origen**: las decisiones permiten agregarlo si se justifica (DD-05).
**Riesgo si es falso**: si el consultorio quiere ver "liberado" como un cancelado, se puede unificar al presentar.
**Cómo validar**: mostrar la agenda al consultorio.

### SU-11 — Hitos ya vencidos al crear o reprogramar
**Suposición:** los hitos vencidos se omiten y no se libera automáticamente un turno cuyo pedido de confirmación no pudo emitirse (RN-29).
**Origen**: el discovery define los hitos pero no qué ocurre con reservas cercanas al turno.
**Riesgo si es falso**: turnos de último momento podrían liberarse al instante o quedar sin gestión.
**Cómo validar**: pregunta abierta de prioridad alta en [10](10_preguntas_abiertas.md).

### SU-12 — Confirmación con enlace de un solo uso
**Suposición:** el correo incluye un enlace de un solo uso que solo permite confirmar el turno sin ingresar contraseña; cancelar y reprogramar exigen sesión.
**Origen**: mitigación del riesgo de que el paciente no ingrese y el turno se libere.
**Riesgo si es falso**: si no se acepta, más pacientes necesitarán ingresar para confirmar y subirán las liberaciones; si se acepta, quien tenga acceso al correo puede confirmar.
**Cómo validar**: pregunta abierta en [10](10_preguntas_abiertas.md).

### SU-13 — Reprogramar reinicia la confirmación
**Suposición:** al reprogramar, el turno vuelve a `pendiente` y se reinician los hitos (RN-32).
**Origen**: coherencia con el ciclo de confirmación.
**Riesgo si es falso**: si no es deseado, el turno conservaría `confirmado` en un horario que el paciente no confirmó.
**Cómo validar**: confirmar con Recepción.

### SU-14 — El recordatorio de 24 horas llega a pendientes y confirmados
**Suposición:** se envía a ambos, con texto distinto (RN-26).
**Origen**: el discovery dice "manda un recordatorio 24 horas antes" sin precisar destinatarios.
**Riesgo si es falso**: envíos innecesarios que consumen el tope diario de correo.
**Cómo validar**: confirmar con el consultorio; ajustar si el tope de correo se vuelve un problema.

### SU-15 — Aviso al paciente al liberar el turno
**Suposición:** el sistema avisa por correo al paciente cuando su turno fue liberado (RN-27).
**Origen**: buena práctica; reduce confusión del paciente.
**Riesgo si es falso**: un correo más por liberación.
**Cómo validar**: confirmar con el consultorio.

### SU-16 — Fórmula del indicador de ausentismo
**Suposición:** tasa = ausentes / (atendidos + ausentes), con liberados y cancelados informados aparte (RN-45).
**Origen**: el discovery pide "cuántos turnos se pierden por ausencias" sin definir la métrica.
**Riesgo si es falso**: el Administrador interpretaría mal la mejora.
**Cómo validar**: revisar la fórmula con el Administrador antes de implementarla.

### SU-17 — Sobreturno: aviso obligatorio, respuesta registrada pero no bloqueante
**Suposición:** el aviso al profesional es obligatorio y se registra; su aprobación o rechazo se registra pero no bloquea (RN-40).
**Origen**: el discovery dice "con aviso o aprobación del profesional afectado".
**Riesgo si es falso**: si el profesional debe poder vetar, hay que bloquear el sobreturno hasta que responda.
**Cómo validar**: pregunta abierta de prioridad alta en [10](10_preguntas_abiertas.md).

### SU-18 — Límites del sobreturno
**Suposición:** el sobreturno respeta el horario semanal y las excepciones; no se fija un máximo de sobreturnos simultáneos (RN-43).
**Origen**: coherencia con RN-11 y RN-12.
**Riesgo si es falso**: Recepción podría necesitar sobreturnos fuera de horario.
**Cómo validar**: confirmar con Recepción.

### SU-19 — Facultades del Profesional limitadas a atendido y ausente
**Suposición:** el Profesional solo marca `atendido` y `ausente` en su agenda (RN-38).
**Origen**: el Profesional "ve su agenda"; las altas y bajas son de Recepción.
**Riesgo si es falso**: un profesional que no pueda cancelar o mover un turno dependerá de Recepción.
**Cómo validar**: confirmar con los profesionales.

### SU-20 — Campos obligatorios de la ficha
**Suposición:** son obligatorios nombre, apellido, teléfono, correo y DNI; obra social y notas son opcionales (RN-47).
**Origen**: el discovery lista los datos sin precisar obligatoriedad.
**Riesgo si es falso**: fichas incompletas o formularios con exceso de campos.
**Cómo validar**: confirmar con Recepción.

### SU-21 — Sin vinculación automática de cuenta y ficha por DNI
**Suposición:** si el DNI ya existe sin cuenta, Recepción vincula manualmente (RN-49).
**Origen**: evita que alguien reclame la ficha de otra persona.
**Riesgo si es falso**: fichas duplicadas o más trabajo manual.
**Cómo validar**: pregunta abierta en [10](10_preguntas_abiertas.md).

### SU-22 — Excepciones sobre turnos existentes
**Suposición:** una excepción sobre un período con turnos exige resolverlos de forma explícita; no se cancelan en silencio (RN-16).
**Origen**: evita pérdida silenciosa de turnos.
**Riesgo si es falso**: la cancelación masiva automática podría ser preferida.
**Cómo validar**: confirmar con el Administrador.

### SU-23 — Duraciones del catálogo inicial
**Suposición:** las duraciones del catálogo inicial son sugerencias propuestas al armar esta base de conocimiento, no datos de las fuentes; el consultorio debe confirmarlas.
**Origen**: el encargo pide un catálogo inicial con duraciones sugeridas; las fuentes no traen duraciones.
**Riesgo si es falso**: turnos con duración equivocada que generan demoras o huecos.
**Cómo validar**: revisar las duraciones con los profesionales antes de publicar.

### SU-24 — Todas las prestaciones activas para todos los profesionales
**Suposición:** no hay restricción por profesional; cualquier profesional puede atender cualquier prestación activa.
**Origen**: las fuentes no relacionan prestaciones con profesionales.
**Riesgo si es falso**: se ofrecerían prestaciones a profesionales que no las realizan; hay que agregar la tabla de relación.
**Cómo validar**: pregunta abierta en [10](10_preguntas_abiertas.md).

### SU-25 — Parámetros de horas guardados por consultorio
**Suposición:** los valores 48, 24, 12 y 24 horas se guardan como parámetros del consultorio con esos valores iniciales; su edición desde la interfaz es opcional.
**Origen**: el discovery indica que el modo manual es por consultorio; guardar los plazos en la configuración evita valores fijos en el código.
**Riesgo si es falso**: ninguno relevante; si se deseara fijarlos, se ignoran las columnas.
**Cómo validar**: confirmar si el Administrador debe poder editarlos.

### SU-26 — Calendario de trabajos en PostgreSQL y barrido idempotente (revisado el 2026-10-06)
**Suposición (vigente, 2026-10-06):** la tabla `notificacion` y los hitos del turno son la fuente de verdad de lo programado; el barrido en proceso los procesa de forma periódica e idempotente. El candado contra ejecuciones simultáneas es `pg_try_advisory_lock` o `SELECT ... FOR UPDATE SKIP LOCKED` en PostgreSQL; Redis es opcional y auxiliar. Se respetan las cuotas de Neon y de Upstash.
**Reemplazado el 2026-10-06 (texto anterior):** "el worker los procesa con un barrido periódico e idempotente, y Redis es auxiliar (cola y bloqueos)"; el candado del barrido estaba en Redis (`discovery/exploracion-tecnica.md`, secciones 4 y 8).
**Origen**: decisión de diseño para mantenibilidad y resiliencia; complementa SU-01 y DD-13.
**Riesgo si es falso**: si se prefiere un trabajo programado por turno, cambia el diseño del barrido.
**Cómo validar**: revisar en el primer change de notificaciones, con un test del candado y de la idempotencia.

### SU-27 — Almacenamiento de sesión en el navegador (revisado el 2026-10-06)
**Suposición (vigente, 2026-10-06):** token de acceso de vida corta en memoria y token de renovación en cookie `HttpOnly` con rotación. Con el frontend en Cloudflare Pages y la API en otro dominio, la cookie necesita `SameSite=None; Secure` o un dominio común para ambos (`discovery/exploracion-tecnica.md`, sección 8, `[NV]`); no se verificó cómo lo tratan los navegadores ni si hay un dominio común disponible sin costo.
**Reemplazado el 2026-10-06 (texto anterior):** "token de acceso de vida corta en memoria y token de renovación en cookie `HttpOnly` con rotación", sin considerar que frontend y API estuvieran en dominios distintos.
**Origen**: buena práctica de seguridad para SPA con JWT.
**Riesgo si es falso**: otro esquema (por ejemplo, ambos tokens en memoria) cambia la experiencia al recargar; si la cookie entre dominios no funciona, hay que compartir dominio o cambiar el almacenamiento del token de renovación.
**Cómo validar**: probar la cookie entre el dominio del frontend y el de la API en el primer despliegue (Q-28).

### SU-28 — Extensión `btree_gist` de PostgreSQL (revisado el 2026-10-06)
**Suposición (vigente, 2026-10-06):** la restricción de exclusión usa la extensión `btree_gist`, disponible en la imagen oficial de PostgreSQL. En Neon figura como soportada ([V], página del proveedor del 2026-10-05); en Supabase `[NV]`; en cualquier otro proveedor, pendiente. La creación se hace a mano en la migración con `CREATE EXTENSION IF NOT EXISTS btree_gist` antes de la restricción.
**Reemplazado el 2026-10-06 (texto anterior):** "disponible en la imagen oficial de PostgreSQL", sin confirmación en un proveedor gestionado.
**Origen**: es lo que requiere la restricción con igualdad de enteros más rango de tiempo.
**Riesgo si es falso**: un PostgreSQL gestionado sin la extensión obligaría a validar con bloqueo explícito.
**Cómo validar**: verificar la extensión en el proveedor elegido (Q-26) con la propia migración y su test de integración.

### SU-29 — Migraciones con Alembic (revisado el 2026-10-06)
**Suposición (vigente, 2026-10-06):** el esquema se versiona con Alembic con `env.py` asíncrono (`alembic init -t async`). El autogenerate no detecta restricciones EXCLUDE, por lo que la restricción de no solapamiento y `CREATE EXTENSION` se escriben a mano. Se mantiene un único head (CI con `alembic heads`; se usa `upgrade head`, nunca `heads`) y `compare_type=True`. Ver DD-14.
**Reemplazado el 2026-10-06 (texto anterior):** "el esquema se versiona con Alembic", sin las salvedades del autogenerate ni el control de heads.
**Origen**: herramienta habitual de SQLAlchemy; el encargo no la nombra.
**Riesgo si es falso**: otra herramienta de migraciones.
**Cómo validar**: confirmar al inicializar el backend y comprobar `alembic heads` en CI.

### SU-30 — Feriados cargados manualmente
**Suposición:** los feriados se cargan a mano como bloqueos; no hay integración con un calendario oficial.
**Origen**: el discovery menciona feriados como excepciones por fecha y no define su fuente.
**Riesgo si es falso**: carga manual repetitiva cada año.
**Cómo validar**: pregunta abierta en [10](10_preguntas_abiertas.md).

### SU-31 — Teléfono normalizado a formato internacional
**Suposición:** los teléfonos se normalizan con código de país de Argentina por defecto para construir el enlace de WhatsApp (RN-53).
**Origen**: necesidad técnica del enlace `wa.me`.
**Riesgo si es falso**: enlaces de WhatsApp que no abren el chat correcto.
**Cómo validar**: probar con teléfonos reales del consultorio.

### SU-32 — Herramientas de prueba
**Suposición:** pytest en el backend y Vitest con Testing Library en el frontend.
**Origen**: herramientas habituales del stack; el modo de TDD estricto exige un ejecutor de pruebas.
**Riesgo si es falso**: otra herramienta.
**Cómo validar**: confirmar al inicializar los proyectos.

### SU-33 — Servidor de correo de prueba en desarrollo
**Suposición:** en desarrollo se usa un servidor SMTP de captura (por ejemplo Mailpit, bajo el perfil `dev` de Compose desde el 2026-10-06) en lugar de la cuenta real.
**Origen**: evita consumir el tope de la cuenta y enviar correos reales durante el desarrollo.
**Riesgo si es falso**: ninguno relevante.
**Cómo validar**: revisar el entorno local.

### SU-34 — Recepción no administra horarios ni excepciones
**Suposición:** solo el Administrador gestiona horarios, excepciones, prestaciones, profesionales y parámetros.
**Origen**: el discovery asigna "configura agendas, profesionales y reglas" al Administrador y "da, mueve y confirma turnos" a Recepción.
**Riesgo si es falso**: si un profesional falta de urgencia, Recepción no podría bloquear la agenda sin el Administrador.
**Cómo validar**: pregunta abierta en [10](10_preguntas_abiertas.md).

### SU-35 — Alta inicial del administrador por variables de entorno
**Suposición:** el primer administrador se crea al inicializar el entorno a partir de variables de entorno.
**Origen**: no hay otro camino para crear la primera cuenta, porque el personal no se autorregistra.
**Riesgo si es falso**: otro procedimiento de arranque.
**Cómo validar**: revisar el proceso de inicialización.

### SU-36 — Instantes en UTC, horarios semanales en hora local
**Suposición:** los instantes de turnos y bloqueos se guardan en `timestamptz`; los horarios semanales se guardan como hora local del consultorio.
**Origen**: práctica estándar para evitar errores de zona horaria.
**Riesgo si es falso**: errores de zona al calcular disponibilidad.
**Cómo validar**: pruebas unitarias del cálculo de disponibilidad.

### SU-37 — Posible API HTTPS de correo
**Suposición:** si el host elegido para la API bloquea los puertos SMTP (Render gratuito bloquea 25, 465 y 587), el envío de correo usará una API HTTPS de correo detrás del mismo puerto `EnviadorCorreo`. `[NV]`: no se verificó ningún proveedor de ese tipo ni su plan gratuito, ni se verificó que otro host gratuito permita SMTP saliente.
**Origen**: `discovery/exploracion-tecnica.md`, secciones 5 y 7.
**Riesgo si es falso**: sin salida SMTP ni API de correo gratuita, no hay correo automático, que es el único canal automático (DD-06).
**Cómo validar**: pregunta abierta Q-23; probar el envío real desde el host elegido antes de publicar.

### SU-38 — El disparador externo es confiable y despierta el servicio
**Suposición:** una llamada HTTP cada 5 minutos a `POST /internal/barrido` es suficiente para ejecutar el barrido con la precisión que piden los hitos de 48, 24 y 12 horas, y despierta el servicio web gratuito cuando está dormido. `[NV]`: la exploración verificó el intervalo mínimo de 5 minutos de GitHub Actions y los 5 cron triggers de Cloudflare Workers, pero no el tiempo de arranque del servicio dormido ni la puntualidad de los disparadores.
**Origen**: `discovery/exploracion-tecnica.md`, sección 7.
**Riesgo si es falso**: retrasos en recordatorios y en la liberación automática de turnos (RN-26, RN-27).
**Cómo validar**: medir la puntualidad del barrido en el primer despliegue (antigüedad de la notificación `programada` más vieja, ver [12](12_devops_y_despliegue.md)); Q-25 y Q-27.

### SU-39 — Código SQLSTATE de la restricción de exclusión
**Suposición:** el error de exclusión de PostgreSQL llega con el SQLSTATE `23P01` y se traduce a "horario ocupado" en el adaptador del repositorio. `[NV]`: no se verificó en fuente primaria. Tampoco hay en la documentación de SQLAlchemy un ejemplo literal con `tstzrange` y el operador `&&`; la expresión debe cubrirse con el test de integración que inserta dos turnos solapados.
**Origen**: `discovery/exploracion-tecnica.md`, sección 1.
**Riesgo si es falso**: el error llegaría al usuario como un error genérico en lugar de "horario ocupado".
**Cómo validar**: el propio test de integración de DD-14, que debe forzar el error y comprobar el código.

### SU-40 — `CREATE EXTENSION btree_gist` desde la migración
**Suposición:** la migración puede ejecutar `CREATE EXTENSION IF NOT EXISTS btree_gist` con `op.execute(...)` antes de crear la restricción, con los permisos del usuario de base de datos del proveedor. `[NV]`: la exploración marca el procedimiento como no verificado.
**Origen**: `discovery/exploracion-tecnica.md`, sección 2.
**Riesgo si es falso**: la migración falla en el proveedor; habría que habilitar la extensión desde su consola.
**Cómo validar**: ejecutar `alembic upgrade head` contra Neon antes del primer despliegue (Q-26).

### SU-41 — Los correos de cuenta se intentan enviar de inmediato
**Suposición:** el correo de verificación y el de recuperación de contraseña se intentan enviar en el momento, dentro de la solicitud, con el mismo caso de uso que usa el barrido. Si el envío falla, la notificación queda `programada` y el siguiente barrido la reintenta. Los hitos de los turnos (48, 24 y 12 horas) sí dependen del barrido.
**Origen**: propuesta del roadmap regenerado el 2026-10-08 (`CHANGES.md`, C-05); aplicada en [07](07_flujos_principales.md), flujos 1 y 2.
**Riesgo si es falso**: si el envío inmediato no se acepta, el registro y la recuperación esperan hasta 5 minutos al siguiente barrido, lo que degrada la experiencia del paciente.
**Cómo validar**: confirmarlo con el equipo antes de implementar C-05.

## Riesgos registrados

| Riesgo | Descripción | Mitigación |
|--------|-------------|------------|
| Plazo ajustado | El MVP completo con backend, frontend, autenticación y recordatorios debe entregarse el 2026-10-12 (siete días desde el 2026-10-05) y la fecha ya se movió una vez. La cuenta de paciente agrega alcance al plan original. La arquitectura base (DD-13) suma servicios que configurar (Cloudflare Pages, Neon, host de la API, disparador externo, correo) dentro del mismo plazo. | Orden de entrega por dependencias; definir qué se recorta si no se llega (pregunta abierta Q-01); resolver temprano las preguntas de despliegue Q-23 a Q-25 y probar un despliegue mínimo antes de construir el resto. |
| Canal automático solo por correo y liberación automática | Un paciente que no lee el correo puede perder un turno que pensaba usar. Es un supuesto sin probar. | Recordatorio a 24 h, WhatsApp semimanual, enlace de confirmación (SU-12), modo manual por consultorio (RN-28) y aviso de liberación (SU-15). |
| WhatsApp semimanual | Depende de que Recepción envíe cada mensaje; no elimina por completo el trabajo manual. | Lista priorizada, un clic por mensaje, marca de enviado y alerta de pendientes (US-033). |
| Ley 25.326 diferida | Desde la v1 se guardan datos personales y la ley aplica desde ese momento, aunque la auditoría y el consentimiento lleguen después. | Mínimo de RN-58: datos limitados, acceso por rol y atributos, contraseñas hasheadas, HTTPS, sin borrado físico, mensajes sin datos de salud. Auditoría y consentimiento como primer ítem del backlog. |
| Límites de los planes gratuitos | Cifras verificadas el 2026-10-05, que cambian con el tiempo: el servicio web gratuito de Render se duerme a los 15 minutos, su Postgres gratuito expira a los 30 días y no hay worker ni cron gratuitos; Neon ofrece 100 CU-h por mes y suspende el cómputo a los 5 minutos; Upstash ofrece 500.000 comandos por mes. | Arquitectura base de DD-13 (Neon en lugar del Postgres de Render; barrido en proceso con disparador externo); contrastar las cifras antes de comprometer el plan; vigilar cuotas (Q-27). |
| Tope y bloqueo del correo | Gmail personal admite 500 correos por día con bloqueo de 1 a 24 horas al excederlo; la contraseña de aplicación no existe con Protección Avanzada ni con cuentas de trabajo o institución; Render gratuito bloquea los puertos SMTP 25, 465 y 587. El correo es el único canal automático. | Alerta al 80 % del tope, reintentos acotados (RN-31), monitoreo de notificaciones `fallida`, puerto `EnviadorCorreo` intercambiable y posible API HTTPS de correo (SU-37, Q-23); WhatsApp semimanual como respaldo. |
| Disparador externo del barrido | Con el servicio gratuito dormido el barrido solo corre si lo dispara una llamada externa; si el disparador falla, los hitos se retrasan (SU-38). | Barrido idempotente que recupera lo vencido; indicadores operativos de [12](12_devops_y_despliegue.md); responsable del disparador definido (Q-25). |
| Cookie entre dominios | El token de renovación en cookie `HttpOnly` puede no funcionar con el frontend y la API en dominios distintos (SU-27). | Probar temprano; `SameSite=None; Secure` o dominio común; decisión en Q-28. |
| Mercado analizado por marketing | Casi toda la evidencia de los proveedores argentinos es material comercial no verificado en uso; el puntaje de DentalCore (4,00) refleja lo declarado. | Tratar el análisis competitivo como referencia, no como validación; validar con el consultorio real. |
| Concurrencia de reservas | Dos reservas simultáneas por el mismo hueco. | Restricción de exclusión en la base de datos (DD-08). |
| Correo como identidad | La cuenta del paciente depende de un correo verificado y recuperable. | Verificación obligatoria (RN-02) y recuperación segura (RN-05). |

## Conflictos entre fuentes resueltos

| Tema | Discovery | Decisión vigente | Dónde se refleja |
|------|-----------|------------------|------------------|
| Acceso del paciente | Habla de reservar "por su cuenta" sin describir cuenta ni registro | Cuenta con usuario y contraseña, registro, verificación de correo y recuperación de contraseña | DD-03, RN-01 a RN-05 |
| Estados del turno | Cinco estados | Se agrega `liberado` y la marca "sin confirmar" | DD-05, RN-18, RN-20 |
| Solapamientos | "de un profesional o de un box" | Alcanza con validar por profesional (un box fijo por profesional) | DD-07, RN-10 |
| Autorización | Roles con permisos, sin detallar atributos | RBAC más cuatro atributos ABAC | DD-04, [11](11_politicas_de_acceso_abac.md) |
| Preguntas abiertas | "Ninguna pendiente" | Se detectaron nuevos vacíos al detallar el diseño | [10](10_preguntas_abiertas.md) |
| Hosting con proceso persistente y Redis | Supuesto inicial de un hosting gratuito con procesos persistentes, Redis y sin suspensión (SU-01, Q-02) | La exploración técnica verificada lo muestra inalcanzable sin tarjeta; la base es el barrido en proceso con disparador externo (2026-10-06) | DD-13, SU-01, SU-26, [12](12_devops_y_despliegue.md) |
| Correo desde el hosting | Gmail por 587 o 465 desde el hosting | Render gratuito bloquea esos puertos; tope de 500 por día; la contraseña de aplicación no existe con Workspace ni con Protección Avanzada (2026-10-06) | DD-06, SU-37, Q-23 |
