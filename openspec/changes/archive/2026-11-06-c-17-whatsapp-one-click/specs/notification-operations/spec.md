# Spec Delta

## MODIFIED Requirements

### Requirement: Bandeja autorizada de notificaciones
GET /api/v1/notificaciones SHALL permitir a Recepción y Administrador consultar notificaciones propias con filtros opcionales de estado y canal y paginación. SHALL rechazar otros roles y minimizar la proyección sin devolver destinatario, cuerpo, tokens o errores originales del transporte.

#### Scenario: Fallidas del consultorio
- **WHEN** Recepción consulta estado=fallida con paginación válida
- **THEN** obtiene solo filas fallidas de su consultorio con identificador, turno asociado, tipo, canal, estado, intentos y fechas operativas

#### Scenario: Roles y aislamiento
- **WHEN** un paciente, Profesional o Administrativo consulta la bandeja, o un administrador consulta habiendo filas de otro consultorio
- **THEN** los roles no autorizados reciben 403 y el administrador no recibe filas ajenas

#### Scenario: Consulta inválida o sin sesión
- **WHEN** se solicita un estado desconocido, una página inválida o no hay sesión
- **THEN** rechaza con 422 las entradas inválidas y con 401 la ausencia de autenticación, sin devolver información de notificaciones

#### Scenario: WhatsApp preparado por urgencia
- **WHEN** Recepción consulta canal=whatsapp y estado=preparada
- **THEN** obtiene solo esas filas propias ordenadas por hito más próximo con orden estable y sin destinatarios ni mensajes

#### Scenario: Compatibilidad sin canal
- **WHEN** un cliente existente omite el nuevo filtro o envía un canal desconocido
- **THEN** la omisión conserva la respuesta previa y un canal desconocido recibe 422
