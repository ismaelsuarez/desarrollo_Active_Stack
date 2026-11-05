# Sistema visual — base para revisión

Mode: system-and-mockups
Revision: 2
Approval: approved (2026-11-05, by user)

Decisión: elegida por el usuario el 2026-11-05. Cada cambio visual tendrá un mockup revisado antes de implementarse. Revisión 2 aprobada por el usuario: color principal #2A9D8F para el logo provisional y el botón; el texto del botón es oscuro para conservar contraste.

## Propósito y fuentes

Base compartida para una aplicación web de turnos odontológicos, orientada a pacientes, recepción, profesionales y administración. Priorizamos lectura clara, formularios explícitos y estados reconocibles en escritorio y celular. Fuentes: `knowledge-base/01_vision_y_objetivos.md`, `03_actores_y_roles.md`, `06_funcionalidades.md` y el esqueleto `frontend/src/App.tsx`. El frontend actual solo contiene un título; no se encontró identidad visual establecida.

## Decisiones abiertas

- Nombre comercial definitivo: (TBD). Se muestra el nombre descriptivo ya existente como provisional.
- Logo definitivo: (TBD); el archivo actual indica visiblemente que es provisional.
- Imágenes y fotografías: (TBD); no se presupone ninguna identidad ni derechos de uso.
- Paleta, tipografía y componentes de esta revisión: aprobados; nombre y logo siguen provisionales.

## Archivos y reemplazos

- Nombre mostrado: editar la constante `BRAND_NAME` en `brand.js`.
- Logo: reemplazar `assets/logo.svg` manteniendo la ruta y actualizar su texto alternativo si corresponde.
- Colores, tipografía, espacios, foco y movimiento: editar variables en `tokens.css`.
- `brand.md` documenta procedencia y reglas; `components.html` es la referencia local.
- Abrir `components.html` en el navegador para revisar. Las capturas móviles y de escritorio se guardan en `previews/` cuando se dispone de renderizado.

Un cambio de tokens o activos compartidos requiere aumentar la revisión, identificar las vistas afectadas y pedir nueva aprobación cuando cambie su apariencia.
