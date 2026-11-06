# Delta

## Purpose

Dar al personal autenticado el contexto mínimo de su propia agenda y las acciones operativas vigentes que la interfaz necesita.

## ADDED Requirements

### Requirement: Identificar agenda propia
El servidor SHALL proporcionar al Profesional y al Administrador autenticados el identificador de su agenda vinculada, o ausencia explícita, derivado de su identidad y consultorio. MUST NOT aceptar la identidad de otra cuenta como filtro ni exponer datos adicionales de cuentas.

#### Scenario: Agenda propia existente
- **WHEN** Profesional o Administrador con agenda vinculada consulta su contexto
- **THEN** recibe solo el identificador de su propia agenda dentro del consultorio.

#### Scenario: Sin agenda o rol no habilitado
- **WHEN** Administrador sin agenda consulta el contexto o un actor no habilitado intenta acceder
- **THEN** el primero recibe ausencia explícita y el segundo recibe denegación.

### Requirement: Acciones operativas vigentes
Las lecturas operativas de agenda y turno SHALL informar acciones permitidas calculadas por las políticas existentes para el principal, estado y hora del servidor. MUST NOT ampliar acceso, modificar las respuestas del paciente ni sustituir la validación al escribir.

#### Scenario: Permisos y estados distintos
- **WHEN** Recepción y Profesional consultan un turno accesible en distintos estados
- **THEN** cada respuesta incluye únicamente las acciones de su rol y estado y omite las incompatibles.

#### Scenario: Cambio concurrente
- **WHEN** el estado o permiso cambia después de la lectura
- **THEN** el servidor vuelve a validar la escritura y la rechaza si ya no corresponde.
