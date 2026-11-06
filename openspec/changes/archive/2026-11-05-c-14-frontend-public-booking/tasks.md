# Tareas

## 1. Diseño y línea de base

- [x] 1.1 Crear y presentar mockups de consulta, selección, reserva, mis turnos, confirmación, cancelación, reprogramación y estados de error/carga en móvil y escritorio; registrar revisión visual y aprobación explícita en `design.md` y `mockups/README.md` antes de aplicar.
- [x] 1.2 Ejecutar pruebas frontend existentes y typecheck como red de seguridad; registrar resultados antes de modificar archivos existentes.

## 2. Contratos y errores

- [x] 2.1 Con TDD, ampliar el cliente para extraer de forma tipada y limitada alternativas y detalles útiles de 403/409; probar respuestas válidas, inesperadas y compatibilidad con consumidores de C-11.
- [x] 2.2 Con TDD, implementar formato de instantes en zona del consultorio y tratamiento de selección obsoleta; probar zonas de dispositivo diferentes y respuestas fuera de orden.

## 3. Consulta pública y reserva

- [x] 3.1 Con TDD, mostrar consultorio, prestaciones, profesionales y selección de fecha/horario sin sesión; probar carga, vacío, 429, errores y ausencia de datos ajenos.
- [x] 3.2 Con TDD, conectar el acceso o registro para un visitante y conservar o reconstruir la selección de manera segura; probar pérdida de selección y que autenticarse no ejecuta la reserva.
- [x] 3.3 Con TDD, enviar reserva explícita de paciente con solo campos permitidos; probar éxito, 403, límite 409, disponibilidad obsoleta y escritura sin respuesta ni reintento automático.
- [x] 3.4 Con TDD, mostrar alternativas de ocupación, selección explícita y lista vacía; probar que una segunda escritura no ocurre sin acción del usuario.

## 4. Mis turnos y acciones

- [x] 4.1 Con TDD, listar turnos propios y sus acciones desde `acciones_permitidas`; probar pasados/futuros, profesional ausente del catálogo y teléfono cuando corresponda.
- [x] 4.2 Con TDD, confirmar y cancelar con actualizaciones y manejo de error; probar límites, acciones ausentes, resultado incierto y turno liberado con opción de nueva reserva.
- [x] 4.3 Con TDD, permitir reprogramar con disponibilidad orientativa, preservando turno original si falla; probar duración distinta, 409 con y sin alternativas, 422 y éxito.

## 5. Integración y revisión

- [x] 5.1 Ejecutar suite frontend, typecheck y build; probar integración de selección, ingreso/registro/verificación y reserva con API simulada, incluidos fallos y demora.
- [x] 5.2 Revisión visual omitida por decisión explícita del usuario (2026-11-05); limitaciones y checklist no ejecutado documentados en `design.md` y `evidence.md`.
- [x] 5.3 Verificar rutas directas y mismo origen con proxy/API según entorno disponible; documentar lo verificado y lo no ejecutado sin exponer credenciales.

## Workflow follow-up

- Sincronizar especificaciones y archivar tras completar las tareas y revisiones del proyecto.
