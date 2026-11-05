# Spec Delta

## Purpose

Ofrecer navegación segura y sesión renovable para pacientes y personal en una aplicación de mismo origen.

## ADDED Requirements

### Requirement: Navegación y guardas por rol
La SPA SHALL ofrecer rutas públicas y privadas, layouts para paciente, recepción, profesional y administrador, y comprobar la sesión y rol antes de mostrar una pantalla privada. Las guardas son de experiencia de usuario; la API conserva la autorización efectiva.

#### Scenario: Sin sesión
- **WHEN** un visitante intenta abrir una ruta privada
- **THEN** se dirige al ingreso sin mostrar contenido privado.

#### Scenario: Rol no permitido
- **WHEN** un usuario autenticado abre una ruta ajena a sus permisos
- **THEN** se muestra acceso denegado o se redirige a una ruta permitida.

#### Scenario: Rol administrativo sin pantalla
- **WHEN** ingresa un usuario administrativo
- **THEN** no obtiene por ello acceso a las pantallas de otros roles y ve un estado adecuado.

### Requirement: Sesión renovable de mismo origen
El cliente SHALL mantener el access token solo en memoria y usar la cookie HttpOnly con credenciales incluidas para renovar y cerrar sesión. SHALL restaurar la sesión al recargar cuando la cookie sea válida y consultar el perfil autorizado.

#### Scenario: Inicio y recarga
- **WHEN** se ingresa correctamente y luego se recarga con cookie válida
- **THEN** se renueva la sesión y se obtiene el perfil sin guardar el access token en almacenamiento persistente del navegador.

#### Scenario: Renovación rechazada
- **WHEN** la cookie está ausente o vencida
- **THEN** se limpia la sesión y las rutas privadas solicitan ingreso, sin un bucle de renovación.

#### Scenario: Renovaciones concurrentes
- **WHEN** varias solicitudes requieren renovación simultáneamente
- **THEN** comparten una única renovación y no reutilizan la cookie rotada.

#### Scenario: Cierre de sesión
- **WHEN** el usuario cierra sesión
- **THEN** se solicita el cierre a la API, se limpia el token en memoria y se deja de mostrar contenido privado.

### Requirement: Errores y disponibilidad del servicio
El cliente SHALL distinguir errores de autenticación, autorización y recurso ausente, e informar espera o indisponibilidad de la API. Solo lecturas seguras SHALL tener reintentos acotados ante demoras o fallos transitorios; las escrituras de resultado incierto no SHALL repetirse automáticamente.

#### Scenario: API tarda en despertar
- **WHEN** una lectura demora o falla transitoriamente durante el arranque
- **THEN** la pantalla muestra aviso y reintenta con límite sin bloquear indefinidamente.

#### Scenario: Respuesta 403 o 404
- **WHEN** la API responde 403 o 404
- **THEN** se presenta un estado comprensible sin tratarlo como credenciales vencidas.

#### Scenario: Fallo de escritura
- **WHEN** una operación de escritura falla o queda sin respuesta
- **THEN** se informa el resultado incierto o el error sin repetir automáticamente la operación.

### Requirement: Comunicación y rutas del mismo origen
La SPA SHALL usar `/api/v1` como base relativa y el proxy de Vite para `/api` en desarrollo, con destino configurable; producción SHALL servir el build desde la API y resolver rutas directas de la SPA sin interceptar rutas de API.

#### Scenario: Desarrollo y producción
- **WHEN** se carga una ruta directa de la aplicación o se llama a `/api/v1` desde el navegador
- **THEN** la SPA y API permanecen en el mismo origen y la ruta de API llega a su controlador.
