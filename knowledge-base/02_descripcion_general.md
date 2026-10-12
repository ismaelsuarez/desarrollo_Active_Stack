# Descripción General

## Stack tecnológico

Stack obligatorio (restricción del proyecto). Las versiones se fijan al crear el proyecto, en los archivos de dependencias, y no se definen en esta base de conocimiento.

| Capa | Tecnologías | Observaciones |
|------|-------------|---------------|
| Frontend | React, TypeScript, Vite | Aplicación web de una sola página (SPA). Idioma de la interfaz: español (Argentina). |
| Backend | Python, FastAPI | API REST. Documentación OpenAPI generada por FastAPI. |
| Autenticación | JWT | Los claims incluyen el rol (también `paciente`) y `consultorio_id`; nunca la ficha ni el identificador del paciente (ver [RN-06](05_reglas_de_negocio.md)). |
| ORM | SQLAlchemy | Acceso a datos mediante repositorios. |
| Base de datos | PostgreSQL | Restricción de exclusión para impedir solapamientos (ver [04](04_modelo_de_datos.md)). |
| Trabajos programados | Barrido idempotente dentro de la API, con reclamación por fila en PostgreSQL | Recordatorios, liberación automática y envío de correo. Un disparador HTTP externo lo activa cada 5 minutos. Redis es opcional (límites de intentos). Ver SU-01 y SU-26 en [09](09_decisiones_y_supuestos.md). |
| Contenedores | Docker, Docker Compose | Entorno local y de despliegue (ver [12](12_devops_y_despliegue.md)). |
| Correo | SMTP de una cuenta existente (por ejemplo Gmail con contraseña de aplicación) | Envío automático de confirmaciones y recordatorios. |
| Presupuesto | Cero | Solo servicios gratuitos o con plan gratuito. |

## Arquitectura general

```text
                        Internet
                           │
        ┌──────────────────┴───────────────────┐
        │                                      │
 Paciente (enlace público)             Personal (Recepción,
        │                              Profesional, Administrador)
        └──────────────┬───────────────────────┘
                       ▼
          ┌─────────────────────────┐
          │ Frontend (React + Vite) │   SPA, rutas públicas y privadas
          └────────────┬────────────┘
                       │ HTTPS / JSON (JWT)
                       ▼
          ┌─────────────────────────┐
          │  API (FastAPI)          │   capas: api → application → domain
          │  políticas RBAC + ABAC  │                    ▲
          │  barrido de hitos       │            infrastructure
          └───┬─────────────────┬───┘
              │                 │ SMTP
              ▼                 ▼
      ┌──────────────┐   ┌──────────────────┐
      │ PostgreSQL   │   │ Servidor de      │
      │ (datos,      │   │ correo (cuenta   │
      │ notificación │   │ existente)       │
      │ y reclamos)  │   └──────────────────┘
      └──────────────┘
              ▲
              │  POST /internal/barrido cada 5 min (secreto compartido)
      Disparador HTTP externo
      (Redis es opcional: solo límites de intentos)

 WhatsApp: el sistema arma el mensaje y el enlace; Recepción lo envía
 desde su propio WhatsApp con un clic (sin API oficial en la v1).
```

Decisiones de alto nivel:

- **Monolito modular en capas** en el backend: un solo servicio de API que también ejecuta el barrido de hitos, sin proceso persistente aparte. Para 2 a 5 profesionales y presupuesto cero, evita la complejidad de microservicios y favorece la mantenibilidad (prioridad 1).
- **La base de datos es la fuente de verdad del calendario de trabajos**: cada notificación o hito queda programado en la tabla `notificacion` y el barrido la procesa reclamando cada fila por separado en PostgreSQL (`FOR UPDATE SKIP LOCKED` y estado intermedio `enviando`). Los hitos pueden retrasarse si el disparador falla, pero no se pierden; el despacho de correo es al menos una vez (ver [08](08_arquitectura_propuesta.md)).
- **La garantía de no solapamiento vive en la base de datos** (restricción de exclusión por profesional), además de la validación en la capa de aplicación.
- **Preparado para varios consultorios**: toda tabla de un consultorio lleva `consultorio_id` y todo acceso se filtra por el consultorio del token (o el que resuelve el servidor en los flujos sin token, RN-59).
- **Zona horaria**: `America/Argentina/Buenos_Aires` (ver **Suposición** SU-02 en [09](09_decisiones_y_supuestos.md)).

## Integraciones externas

| Servicio | Propósito | Tipo | Alcance v1 |
|----------|-----------|------|------------|
| Servidor SMTP de una cuenta de correo existente (por ejemplo Gmail con contraseña de aplicación) | Verificación de correo, recuperación de contraseña, resumen de la reserva, confirmación, recordatorio, avisos de liberación y de cambios del personal, confirmación de la cancelación hecha por el paciente y rechazo de una solicitud de vinculación | SMTP | Sí. Tiene límites de envío y puede caer en spam (ver riesgos en [09](09_decisiones_y_supuestos.md)). |
| WhatsApp (cliente de Recepción) | Confirmación y recordatorio con mensaje preparado por el sistema | Enlace `wa.me` con texto prellenado, abierto por Recepción | Sí, semimanual. Sin API oficial por costo por conversación y aprobación de plantillas de Meta. |
| ARCA (facturación) | Facturación | — | No. Backlog. |
| Obras sociales | Validación y liquidación | — | No. Backlog. La obra social es solo un dato de texto. |
| Mercado Pago | Seña o pago al reservar | — | No. Backlog. |
| Google Calendar / planilla | Importación de agenda previa | — | No. Backlog, sin fecha. |
| Hosting en la nube (planes gratuitos) | Un servicio web gratuito con la API, que sirve también el frontend compilado (DD-26), y PostgreSQL en Neon | Servicios de hosting | Sí. Arquitectura base en DD-13 de [09](09_decisiones_y_supuestos.md); el host de la API sigue abierto (Q-24 en [10](10_preguntas_abiertas.md)). |
| Disparador externo del barrido | Llama cada 5 minutos a `POST /internal/barrido` con un secreto compartido | HTTP (cron externo) | Sí. Quién lo opera sigue abierto (Q-25 en [10](10_preguntas_abiertas.md)). |

## API REST

Prefijo `/api/v1`. Documentación interactiva generada por FastAPI (OpenAPI). Resumen por recurso; el detalle de quién puede hacer qué está en [03](03_actores_y_roles.md) y [11](11_politicas_de_acceso_abac.md).

| Recurso | Endpoints principales | Acceso |
|---------|-----------------------|--------|
| Autenticación | `POST /auth/registro`, `POST /auth/verificar-email`, `POST /auth/reenviar-verificacion`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/recuperar-password`, `POST /auth/restablecer-password`, `GET /auth/me` | Público, salvo `logout` y `me` |
| Público (reserva) | `GET /publico/consultorio`, `GET /publico/aviso-privacidad`, `GET /publico/prestaciones`, `GET /publico/profesionales`, `GET /publico/disponibilidad` | Público, solo lectura |
| Usuarios | `GET/POST /usuarios`, `PATCH /usuarios/{id}` (el alta rechaza el rol `paciente` con 422, RN-07) | Administrador |
| Profesionales y boxes | `GET/POST /profesionales`, `PATCH /profesionales/{id}`, `GET/POST /boxes` | Administrador (escritura) |
| Horarios y bloqueos | `GET/PUT /profesionales/{id}/horario-semanal`, `GET/POST /profesionales/{id}/bloqueos`, `DELETE /bloqueos/{id}` | Administrador (escritura) |
| Prestaciones | `GET/POST /prestaciones`, `PATCH /prestaciones/{id}` | Administrador (escritura) |
| Pacientes | `GET/POST /pacientes`, `GET/PATCH /pacientes/{id}`, `GET /pacientes/{id}/turnos`, `POST /pacientes/{id}/desvincular`, `POST /pacientes/{id}/reactivar` | Recepción, Administrador; Profesional (acotado); Paciente (propio). Desvincular y reactivar: solo Recepción y Administrador (RN-63). El detalle de la ficha incluye la cuenta vinculada solo para Recepción y Administrador (RN-63) |
| Solicitudes de vinculación | `GET /solicitudes-vinculacion?estado=` (con la ficha vinculada en las solicitudes `vinculada`), `POST /solicitudes-vinculacion/{id}/vincular`, `POST /solicitudes-vinculacion/{id}/rechazar` | Recepción, Administrador |
| Turnos | `GET /turnos`, `POST /turnos`, `GET /turnos/{id}`, `PATCH /turnos/{id}` (reprogramar), `POST /turnos/{id}/confirmar`, `POST /turnos/{id}/cancelar`, `POST /turnos/{id}/liberar`, `POST /turnos/{id}/atendido`, `POST /turnos/{id}/ausente`, `GET /turnos/{id}/historial` | Según política ABAC |
| Confirmación por enlace | `POST /turnos/confirmar-por-enlace` | Público, con el token de un solo uso recibido por correo (el consultorio sale de la fila del token, RN-59) |
| Sobreturnos | `POST /sobreturnos` (crea el turno superpuesto y su autorización), `POST /sobreturnos/{id}/respuesta-profesional` (`{id}` es el del turno) | Recepción, Administrador; Profesional (respuesta), o Administrador sobre su propia agenda (DD-24) |
| Agenda | `GET /agenda?profesional_id=&fecha=` | Según política ABAC |
| Notificaciones | `GET /notificaciones?estado=`, `GET /notificaciones/{id}/whatsapp`, `POST /notificaciones/{id}/marcar-enviada` | Recepción, Administrador |
| Indicadores | `GET /indicadores/ausentismo` | Administrador |
| Consultorio | `GET /consultorio`, `PATCH /consultorio` (modo de liberación y parámetros) | Administrador (escritura) |
| Salud | `GET /health` | Público |

Convenciones: errores en formato uniforme (código, mensaje, detalle de campo), fechas en ISO 8601 con zona horaria, identificadores numéricos (`bigint`, DD-23), paginación en listados.

## Mapa de la base de conocimiento

| Necesito entender | Archivo |
|-------------------|---------|
| Para qué existe el sistema y qué queda fuera | [01](01_vision_y_objetivos.md) |
| Quién usa el sistema y con qué permisos | [03](03_actores_y_roles.md), [11](11_politicas_de_acceso_abac.md) |
| Qué datos se guardan | [04](04_modelo_de_datos.md) |
| Qué reglas se aplican | [05](05_reglas_de_negocio.md) |
| Qué funcionalidades se construyen | [06](06_funcionalidades.md), [07](07_flujos_principales.md) |
| Cómo se construye y se despliega | [08](08_arquitectura_propuesta.md), [12](12_devops_y_despliegue.md) |
| Qué se decidió, qué se asumió y qué falta | [09](09_decisiones_y_supuestos.md), [10](10_preguntas_abiertas.md) |
