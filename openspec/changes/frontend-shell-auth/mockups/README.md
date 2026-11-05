# Mockups C-11

Approval: approved (2026-11-05, by user)

Base visual: revisión 2, aprobada por el usuario el 2026-11-05. Nombre comercial y logo definitivos pendientes (TBD); el logo compartido es provisional.

Las páginas son galerías estáticas para revisar pantallas y estados, no una aplicación funcional. Cada tarjeta representa una pantalla o un estado alternativo; no se pretende mostrarlos todos juntos al usuario final. Los datos, nombres y botones son ilustrativos.

## Vistas

- [Ingreso y recuperación](acceso.html): ingreso, credenciales incorrectas, correo sin verificar, espera, recuperación y reenvío.
- [Registro](registro.html): campos del paciente, aceptación del aviso vigente, aviso no disponible o actualizado.
- [Enlaces](enlaces.html): verificación, enlace vencido o usado, restablecimiento, confirmación de turno y espera.
- [Cuenta](cuenta.html): contacto del paciente, cambio de contraseña y cierre de sesión sin confirmación del servidor.
- [Roles](roles.html): estructuras de paciente, recepción, profesional y administrador; estado del rol administrativo, acceso restringido, carga y página ausente.

## Fuentes y revisión

Propuesta, especificaciones, diseño y tareas de C-11; `design-system/tokens.css`, `brand.js` y `assets/logo.svg`. La navegación de agenda y sus funciones se implementarán en cambios posteriores. Abrir cualquiera de los cinco HTML en un navegador; los enlaces superiores permiten recorrer las vistas. No necesitan servidor ni acceso a internet.

Preview: rendered (2026-11-05). Se capturaron e inspeccionaron las diez vistas en Edge: escritorio 1440×900 y celular 390×844, con página completa. Archivos `previews/<vista>-desktop.png` y `previews/<vista>-mobile.png`. Las capturas corresponden a la galería completa y muestran estados alternativos de manera simultánea solo para facilitar la revisión.

Visual verify: pendiente de implementación.
