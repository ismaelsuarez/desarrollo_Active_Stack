# Tasks

Todas las tareas de implementación siguen Strict TDD: red, green y triangulación, con línea de base previa cuando se modifiquen archivos existentes.

## 1. Preparación y diseño

- [x] 1.1 Completar la aprobación de los [mockups](mockups/README.md) basados en el sistema visual revisión 2 y verificar su registro en `design.md` antes de aplicar.
- [x] 1.2 Obtener aprobación explícita para implementar el alcance concreto de autenticación y seguridad por gobernanza CRITICAL; registrar la decisión.
- [x] 1.3 Establecer línea de base de pruebas frontend y backend afectadas, verificar resultados y configurar dependencias de routing y pruebas compatibles con el lockfile.

## 2. Mismo origen y distribución

- [x] 2.1 Configurar proxy `/api` con destino exclusivo de desarrollo, Compose y variables documentadas; verificar que local y Compose usen sus destinos y no entren al build.
- [x] 2.2 Servir build desde la API con fallback acotado a rutas de SPA; probar deep links, recursos, 404 API y ausencia de fallback para métodos no GET.
- [x] 2.3 Integrar build frontend en imagen de producción y documentar arranque y reversión; comprobar que la imagen sirve API y SPA en un origen.

## 3. Transporte y sesión

- [x] 3.1 Implementar cliente tipado con base relativa, credenciales incluidas, autorización y tratamiento de 401/403/404/422/429; probar cuerpos y estados sin exponer secretos.
- [x] 3.2 Implementar tiempo de espera, aviso y reintento acotado de lecturas transitorias; probar éxito tardío, agotamiento y ausencia de reintentos para escrituras inciertas.
- [x] 3.3 Implementar proveedor con access token en memoria, login, perfil y logout; probar errores, limpieza de memoria, falta de persistencia y fallo de revocación.
- [x] 3.4 Restaurar sesión y serializar refresh, con un máximo de un reintento tras 401 confirmado; probar concurrencia, rotación, rechazo sin bucles y respuesta tardía tras logout.

## 4. Shell y navegación

- [x] 4.1 Crear router, rutas públicas y layouts de paciente, recepción, profesional y administrador; probar navegación, enlaces profundos y estado del rol administrativo.
- [x] 4.2 Incorporar guardas de sesión y rol con estados de carga y denegación; probar acceso permitido, sin sesión y rol incorrecto sin mostrar contenido privado.
- [x] 4.3 Crear componentes atómicos y plantillas accesibles, separando contenedores y presentación; probar interacciones y mensajes por props y documentar convenciones de composición.

## 5. Cuenta pública

- [x] 5.1 Implementar carga del aviso de privacidad, casilla desmarcada y registro con la versión recibida; probar error de carga, aceptación, versión obsoleta, errores de campo y payload sin consultorio ni rol.
- [x] 5.2 Implementar login, reenvío y recuperación; probar credenciales inválidas, correo no verificado, límites y mensajes genéricos sin enumeración.
- [x] 5.3 Implementar lectura segura de fragmentos y rutas/alias de verificación, restablecimiento y confirmación; probar tokens ausentes, usados, válidos y montaje StrictMode sin duplicar POST ni filtrar tokens.
- [x] 5.4 Implementar formulario de restablecimiento; probar contraseña inválida, resultado correcto y rechazo del enlace.

## 6. Cuenta autenticada

- [x] 6.1 Implementar cambio de contraseña para todos los roles autenticados; probar contraseña incorrecta, validación y confirmación exitosa.
- [x] 6.2 Implementar actualización de contacto solo para paciente; probar teléfono, correo cambiado, correo equivalente, conflicto y acceso de otro rol.

## 7. Integración

- [x] 7.1 Ejecutar typecheck, build, pruebas frontend y pruebas backend afectadas; verificar resultados y corregir regresiones.
- [x] 7.2 Probar navegador o cliente HTTP real contra API real a través de proxy: login, cookie HttpOnly/Strict, refresh rotado, recarga y logout; documentar evidencia sin exponer secretos.
- [x] 7.3 Verificar responsive, accesibilidad y los estados visuales contra los [mockups](mockups/README.md) aprobados, sus [capturas](mockups/previews/) y el sistema visual revisión 2; registrar resultados o limitaciones según política.
