## Purpose

Permitir el registro público del paciente con consentimiento versionado, verificación de correo y protección frente al abuso sin revelar la existencia de una ficha por su DNI.

## ADDED Requirements

### Requirement: Aviso de privacidad vigente
El sistema SHALL servir texto y versión de KB 13 en GET /api/v1/publico/aviso-privacidad, con los datos del consultorio activo resuelto por el servidor (RN-59, RN-65).

#### Scenario: Consultorio completo
- **WHEN** se consulta el aviso con nombre, domicilio y teléfono configurados
- **THEN** devuelve la versión vigente y reemplaza los tres marcadores con esos datos

#### Scenario: Datos provisionales
- **WHEN** falta un dato del responsable
- **THEN** conserva su marcador y la verificación de preparación para producción detecta el aviso incompleto

### Requirement: Consentimiento y datos del registro
POST /api/v1/auth/registro SHALL exigir nombre, apellido, teléfono, correo, DNI, usuario, contraseña de al menos ocho caracteres, aceptación verdadera y versión vigente; obra social es opcional. SHALL rechazar campos no declarados y guardar fecha y versión aceptadas (RN-01, RN-04, RN-65).

#### Scenario: Registro aceptado
- **WHEN** un registro válido acepta la versión vigente
- **THEN** crea una cuenta paciente sin verificar, guarda contraseña hasheada y fecha del reloj inyectado, programa verificación y responde 201 sin secretos

#### Scenario: Consentimiento inválido
- **WHEN** falta aceptación, es falsa o la versión no coincide
- **THEN** responde 422 sin crear cuenta, ficha, solicitud ni correo

#### Scenario: Identidad del servidor
- **WHEN** se envía consultorio_id, rol u otro campo desconocido
- **THEN** responde 422 y no permite que el cliente elija consultorio ni rol

#### Scenario: Datos normalizados y duplicados
- **WHEN** usuario o correo normalizado ya existe en el consultorio
- **THEN** rechaza el registro sin persistir una cuenta parcial y conserva el intento de registro previamente confirmado

### Requirement: Ficha o solicitud sin enumerar DNI
El registro SHALL crear una sola ficha por DNI normalizado y consultorio. Si existe SHALL crear una solicitud pendiente sin vincular ni modificar la ficha existente. Respuesta y plantilla de verificación SHALL ser iguales en ambos caminos (RN-49, RN-62).

#### Scenario: DNI nuevo
- **WHEN** el DNI todavía no pertenece a una ficha
- **THEN** crea la ficha vinculada y no crea solicitud

#### Scenario: DNI existente
- **WHEN** el DNI pertenece a una ficha con o sin cuenta
- **THEN** crea la cuenta y solicitud pendiente sin duplicar ni vincular esa ficha

#### Scenario: Registros simultáneos
- **WHEN** dos cuentas distintas se registran simultáneamente con el mismo DNI nuevo
- **THEN** ambas reciben la misma respuesta y quedan una ficha y una solicitud, sin abortar ninguna transacción por el DNI

### Requirement: Límite durable de registro
El registro SHALL limitar solicitudes por origen con HMAC-SHA256 y ventana configurable; sin origen determinable SHALL aplicar el límite global. Todo intento admitido SHALL confirmarse antes de validar y registrar; uno excedido SHALL responder 429 sin insertar otro intento. La dirección nunca SHALL persistirse ni registrarse (RN-62, DD-21).

#### Scenario: Límite por origen
- **WHEN** un origen agota REGISTRATION_LIMIT_PER_ORIGIN dentro de la ventana
- **THEN** el siguiente registro responde 429 sin incrementar intentos ni crear cuenta

#### Scenario: Validación o transacción fallida
- **WHEN** una solicitud admitida falla después por validación o por conflicto de cuenta
- **THEN** su intento permanece confirmado

#### Scenario: Proxy confiable
- **WHEN** TRUSTED_PROXY_HOPS es uno
- **THEN** usa la última entrada válida de X-Forwarded-For e ignora las anteriores manipulables

#### Scenario: Sin proxy o sin origen
- **WHEN** los saltos son cero o no se puede determinar una dirección válida
- **THEN** ignora el encabezado con cero y usa la conexión directa; si no obtiene origen aplica REGISTRATION_LIMIT_GLOBAL

#### Scenario: Retención
- **WHEN** se inserta un intento con filas de más de 24 horas
- **THEN** purga esas filas y conserva las recientes mediante el reloj inyectado

### Requirement: Verificación de correo
El sistema SHALL aceptar tokens aleatorios hasheados, de un uso y vencimiento configurable en POST /api/v1/auth/verificar-email. El consultorio SHALL salir de la fila del token. POST /api/v1/auth/reenviar-verificacion SHALL aplicar límites durables y programar un correo sin enumerar cuentas (RN-02, RN-03, RN-59).

#### Scenario: Token válido
- **WHEN** se verifica un token vigente de una cuenta activa
- **THEN** consume el token y marca email_verificado con el reloj inyectado, permitiendo ingresar

#### Scenario: Token inválido
- **WHEN** el token no existe, venció, fue usado o es de otro propósito
- **THEN** rechaza sin modificar la cuenta

#### Scenario: Consumo concurrente
- **WHEN** dos solicitudes usan el mismo token simultáneamente
- **THEN** solo una puede consumirlo

#### Scenario: Reenvío limitado
- **WHEN** se pide reenvío para correo inexistente, ya verificado o sin verificar
- **THEN** responde de forma genérica, solo programa cuando corresponde y aplica el límite configurable antes de repetir envíos
