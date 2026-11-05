# patient-records Specification

## Purpose

Permitir al personal gestionar fichas mínimas y a cada actor consultar o editar únicamente los datos autorizados, preservando el vínculo de cuenta y los turnos existentes.

## Requirements

### Requirement: Alta mínima y única de ficha
POST /api/v1/pacientes SHALL crear una ficha activa sin cuenta para Recepción o Administrador. SHALL exigir nombre, apellido, teléfono, correo y DNI válidos, admitir obra social y notas opcionales y conservar la unicidad del DNI por consultorio (RN-47, RN-48; US-036).

#### Scenario: Ficha nueva sin cuenta
- **WHEN** Recepción crea una ficha válida en su consultorio
- **THEN** recibe 201 con su identificador, la ficha se recupera por detalle y puede elegirse para vincular una solicitud sin crear una cuenta automática

#### Scenario: DNI inválido o duplicado
- **WHEN** el DNI tiene puntos, espacios internos, letras o coincide con otra ficha del mismo consultorio después de quitar espacios exteriores
- **THEN** responde 422 por formato inválido o 409 por duplicado, sin dejar una ficha parcial; los espacios exteriores se normalizan como en C-05 y el mismo DNI en otro consultorio no causa conflicto

#### Scenario: Entradas y roles no permitidos
- **WHEN** falta un dato obligatorio, se envían activo, usuario_id, consultorio_id o campos desconocidos, o el actor no es personal habilitado
- **THEN** rechaza la entrada con 422 o la acción con 403 y no modifica la base

### Requirement: Búsqueda paginada y acotada de pacientes
GET /api/v1/pacientes SHALL permitir buscar por apellido, DNI o teléfono con paginación y orden estable. SHALL restringir los resultados al consultorio y alcance del actor antes de paginar y calcular el total (RN-50; US-037).

#### Scenario: Criterios y páginas
- **WHEN** se consulta cada criterio, una combinación de criterios o una página posterior
- **THEN** devuelve sólo coincidencias, ordenadas establemente, con total del alcance autorizado y sin repetir fichas entre páginas del mismo conjunto

#### Scenario: Búsqueda sin coincidencias
- **WHEN** ningún paciente autorizado coincide o la página supera el final
- **THEN** devuelve 200 con lista vacía y sin indicar coincidencias fuera del alcance

#### Scenario: Profesional y paciente
- **WHEN** un Profesional busca fichas o un Paciente consulta la colección
- **THEN** el Profesional sólo obtiene pacientes con turnos en su agenda y el Paciente sólo su ficha vigente, o lista vacía si no tiene ficha

### Requirement: Detalle mínimo según rol
GET /api/v1/pacientes/{id} SHALL devolver la ficha autorizada. Sólo Recepción y Administrador SHALL recibir cuenta con id, nombre_usuario, email y email_verificado, o null sin vínculo. Profesional y Paciente SHALL recibir la ficha sin ese bloque ni otros datos de cuenta (RN-58, RN-63; US-039).

#### Scenario: Cuenta visible al personal
- **WHEN** el personal autorizado abre una ficha antes de vincular, después de vincular y después de desvincular
- **THEN** cuenta es null, contiene exactamente los cuatro campos permitidos y vuelve a null respectivamente

#### Scenario: Cuenta omitida a otros lectores
- **WHEN** Profesional de la agenda o Paciente titular consulta la ficha
- **THEN** no aparece la propiedad cuenta, hashes, tokens ni otros datos de autenticación

#### Scenario: Ficha ajena o token anterior a desvincular
- **WHEN** el id es inexistente, pertenece a otro consultorio, queda fuera de la agenda o ya no está vinculado al Paciente del JWT
- **THEN** responde 404 sin exponer datos de la ficha aunque el token de acceso siga vigente

### Requirement: Edición de ficha por personal
PATCH /api/v1/pacientes/{id} SHALL permitir a Recepción y Administrador corregir los datos de la ficha, validar formato y unicidad, y conservar campos omitidos. MUST NOT modificar activo, usuario_id, consultorio_id, datos de login ni turnos (RN-47, RN-48, RN-63; SU-47).

#### Scenario: Corrección parcial
- **WHEN** el personal cambia nombre, DNI o contacto de la ficha y omite otros campos
- **THEN** guarda sólo los cambios pedidos, conserva cuenta y turnos y no altera correo, verificación ni contraseña de la cuenta vinculada

#### Scenario: Campos opcionales y rechazo atómico
- **WHEN** se limpian obra_social o notas con null, o se intenta duplicar DNI, anular un dato obligatorio o editar activo o vínculo
- **THEN** permite limpiar opcionales y rechaza la solicitud inválida con 409 o 422 sin cambios parciales

### Requirement: Contacto propio preserva la identidad de cuenta
Un Paciente SHALL poder editar únicamente teléfono y/o correo de su ficha vigente. Un cambio de correo propio SHALL mantener el contrato de C-05: actualizar cuenta y ficha vigente, quitar verificación e invalidar enlaces previos antes de programar una verificación nueva. MUST NOT editar otra ficha ni otros campos.

#### Scenario: Contacto propio o correo equivalente
- **WHEN** el titular cambia su teléfono o envía un correo equivalente tras normalizar
- **THEN** actualiza el teléfono si corresponde y conserva verificación sin un correo adicional para el email equivalente

#### Scenario: Correo propio diferente
- **WHEN** cambia su email a uno disponible y diferente
- **THEN** cuenta y ficha quedan con el correo normalizado, la cuenta sin verificar y una verificación nueva, sin conceder acceso a otra ficha

#### Scenario: Campo ajeno a contacto, conflicto o vínculo cambiado
- **WHEN** intenta editar nombre, DNI, obra social, notas u otro campo, el correo de cuenta está ocupado o el vínculo ya no corresponde al id pedido
- **THEN** responde 422 por campo no permitido, 409 por correo ocupado o 404 por ficha ajena, sin cambios parciales ni correo adicional

#### Scenario: Contacto propio concurrente con desvinculación
- **WHEN** el nuevo PATCH de contacto compite con desvincular y su transacción informa 40P01 o 40001
- **THEN** responde 409 con rollback completo de cuenta, ficha y verificación, sin respuesta 500 ni ampliación de permisos

### Requirement: Preservación de fichas y turnos
La API de C-08 MUST NOT ofrecer borrado físico ni desactivación de fichas, ni escribir sus turnos. Las operaciones SHALL conservar el endpoint de historial de turnos entregado por C-07 y sus filtros de agenda (RN-58, SU-47; US-038).

#### Scenario: Sin borrar ni desactivar
- **WHEN** se intenta DELETE sobre una ficha o PATCH con activo=false
- **THEN** no existe borrado permitido, responde 405 o 422 respectivamente y conserva ficha y turnos

#### Scenario: Compatibilidad con turnos existentes
- **WHEN** se consulta /pacientes/{id}/turnos antes y después de editar o corregir un vínculo
- **THEN** los turnos de la ficha permanecen y se aplican los filtros C-07, sin duplicar ni sustituir esa ruta

### Requirement: Minimización de listados y rechazos
Las colecciones SHALL devolver sólo los campos operativos para identificar la ficha. Errores y logs MUST NOT incluir valores de DNI, teléfono, correo, obra social, notas, credenciales ni consultas de búsqueda (RN-54, RN-58).

#### Scenario: Listado mínimo
- **WHEN** se busca una ficha con notas y datos de contacto sintéticos privados
- **THEN** la colección no devuelve notas, obra social, cuenta ni datos de autenticación

#### Scenario: Rechazo sin fuga
- **WHEN** falla validación, unicidad o autorización de una ficha
- **THEN** respuesta y logs no reproducen valores privados de entrada ni de fichas ajenas
