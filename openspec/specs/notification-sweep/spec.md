# notification-sweep Specification

## Purpose

Procesar trabajo durable de correo y limpieza mediante un barrido acotado dentro de la API, recuperable tras caídas y compartido por sus dos disparadores.

## Requirements

### Requirement: Barrido durable acotado
El sistema SHALL procesar correos programados vencidos y reclamaciones vencidas en lotes finitos, sin ejecutar hitos de C-16. SHALL informar reclamadas, enviadas, reintentadas, omitidas y fallidas propias. Una reclamación propia cuyo resultado se pierde SHALL contar como reclamada, pero no como enviada, reintentada o fallida propia; no SHALL atribuir resultados ajenos.

#### Scenario: Pendientes tras suspensión
- **WHEN** se ejecuta el barrido después de tres horas sin servicio
- **THEN** procesa el trabajo vencido del lote, conserva el futuro y una repetición no reenvía filas ya enviadas

#### Scenario: Fallo de una entrega y resumen
- **WHEN** un lote incluye un envío exitoso, un error reintentable, una fila no vigente y una agotada
- **THEN** el resumen distingue sus resultados y el fallo de una entrega no impide tratar las otras filas

#### Scenario: Lote finito sin inanición por cupo de cuenta
- **WHEN** hay más pendientes que el tamaño del lote y los correos de cuenta agotaron su cupo
- **THEN** la ejecución termina sin reintentar la misma fila en ese barrido y considera también correos de turnos con cupo disponible

### Requirement: Barridos simultáneos por fila
Dos barridos SHALL poder avanzar simultáneamente y coexistir con el despacho inmediato de cuenta sin reclamar la misma fila mientras su reclamación esté vigente. SHALL conservar entrega al menos una vez, sin candado global ni Redis obligatorio (RN-61, DD-17).

#### Scenario: Dos barridos y despacho inmediato
- **WHEN** dos barridos y un despacho inmediato coinciden sobre las mismas notificaciones
- **THEN** cada reclamación vigente pertenece a un solo envío y los demás pueden procesar filas diferentes

#### Scenario: Caída y resultado tardío
- **WHEN** un envío no registra su resultado, vence y otro barrido lo retoma
- **THEN** permite el reenvío y descarta el resultado tardío de la reclamación anterior sin pisar estado o intentos

### Requirement: Disparador interno autenticado
POST /internal/barrido SHALL exigir un secreto de servidor comparado en tiempo constante y quedar fuera del OpenAPI público. SHALL rechazar la ausencia o incorrección del secreto sin ejecutar trabajo y no aceptar consultorio ni credenciales por query o cuerpo.

#### Scenario: Secreto válido
- **WHEN** se invoca con el secreto correcto en el encabezado definido
- **THEN** ejecuta el barrido del consultorio configurado y responde 200 con su resumen sin datos personales

#### Scenario: Credencial ausente o incorrecta
- **WHEN** falta el encabezado, es incorrecto o el servidor no tiene secreto configurado
- **THEN** responde 403 sin despachar, purgar ni registrar una ejecución autorizada

#### Scenario: Documentación y entrada ajena
- **WHEN** se consulta el OpenAPI o se intenta elegir consultorio mediante una entrada no admitida
- **THEN** el endpoint no figura en el esquema y no usa información del cliente para seleccionar el consultorio

### Requirement: Disparador opcional en proceso
El bucle en proceso SHALL ejecutar el mismo barrido que el endpoint con SWEEP_IN_PROCESS_ENABLED y SWEEPER_INTERVAL_SECONDS. SHALL iniciar y detenerse con la API, conservar el servicio tras un fallo recuperable y usar sesiones independientes por ejecución.

#### Scenario: Activación y recuperación
- **WHEN** el bucle está habilitado y una ejecución falla de forma recuperable
- **THEN** registra el fallo sin secretos, espera el intervalo y vuelve a intentar mientras la API siga activa

#### Scenario: Desactivación y cierre
- **WHEN** el bucle está deshabilitado o la API termina
- **THEN** no inicia ejecuciones deshabilitadas y cancela y espera la tarea propia al cerrar, dejando reclamaciones interrumpidas recuperables

#### Scenario: Configuración inválida
- **WHEN** se configura un intervalo no positivo o SMTP timeout mayor o igual al TTL de reclamación
- **THEN** rechaza el arranque sin revelar secretos

### Requirement: Limpieza periódica con retención
El barrido SHALL purgar token_usuario y refresh_token vencidos y los intentos de registro e ingreso de más de 24 horas, conservando los vigentes y los del borde de retención. SHALL mantener las purgas existentes en escritura sin borrar usuarios, turnos, notificaciones ni historial.

#### Scenario: Borde de vencimiento y retención
- **WHEN** hay tokens expirados, tokens futuros e intentos de hace 24 horas y de un instante anterior
- **THEN** elimina los tokens cuyo expira_en es menor o igual al reloj, elimina solo intentos anteriores al corte de 24 horas y conserva los restantes

#### Scenario: Repetición y aislamiento
- **WHEN** se repite la limpieza del consultorio configurado y hay filas de otro consultorio
- **THEN** no afecta credenciales válidas ni filas del otro consultorio y la segunda ejecución no repite eliminaciones ya confirmadas
