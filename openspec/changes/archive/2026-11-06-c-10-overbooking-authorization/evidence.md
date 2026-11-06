# Evidencia de implementación C-10

## TDD y verificaciones

| Tarea | Capa | Red de seguridad | RED → GREEN y triangulación |
|---|---|---|---|
| 1.1 Persistencia | PostgreSQL | 39 pruebas de migración y creación y 7 unitarias aprobadas antes del cambio | Migración ausente, columnas ausentes, restricciones y repositorio ausente fallaron primero; 9 casos de migración, integridad, repositorio y aislamiento pasaron. |
| 1.2 Alta | HTTP y PostgreSQL | 47 pruebas existentes de reservas aprobadas antes del cambio | Ruta ausente falló primero; 16 casos de roles, autorización, grilla, bloqueos, horarios, contigüidad y estados pasaron. |
| 1.3 Atomicidad | HTTP y PostgreSQL | Incluida en la red de seguridad anterior | Historial con acción incorrecta falló primero; cuatro fallos inyectados revirtieron la operación; verificados avisos, exclusión SQLSTATE 23P01 y dos autorizaciones concurrentes. |
| 2.1 Respuesta | HTTP y PostgreSQL | Políticas de sobreturno: 7 pruebas unitarias aprobadas | Ruta ausente falló primero; rechazo, aprobación y ocho combinaciones de rol, agenda y consultorio pasaron sin alterar el turno. |
| 2.2 Lectura | HTTP y PostgreSQL | 68 pruebas de agenda y acciones del paciente aprobadas antes del cambio | Campo ausente falló primero; otra ejecución detectó un campo nulo en paciente y se corrigió la selección del esquema. Agenda, lista y detalle se verificaron para personal y paciente. |

La ejecución conjunta de lecturas y regresiones de agenda y acciones de paciente aprobó 99 pruebas. La ejecución final dirigida de C-10, migraciones y dos casos de correo aprobó 68; otra ejecución de correo C-09/C-15/C-16 con Mailpit configurado aprobó 51. OpenSpec validó el change en modo estricto sin errores, y Alembic informó un solo head `0011_overbooking_authorization`.

## Límite de la suite completa

La suite completa inicial en Windows ejecutó 1713 pruebas: 1691 pasaron y 22 fallaron. Ocho fallos eran expectativas que fijaban el head `0010`; se actualizaron a `0011` y pasaron en la ejecución dirigida. Diez fallos de correo se produjeron antes de iniciar Mailpit o por no configurar `SMTP_TEST_HOST` y `SMTP_TEST_PORT`; se repitieron con Mailpit local y pasaron. Dos pruebas de infraestructura no encuentran Bash funcional desde Windows; dos pruebas de concurrencia C-08 agotan esperas de nombres de tareas asyncio en este entorno. Esas cuatro pruebas no se declaran aprobadas. La suite completa no se volvió a ejecutar tras estas correcciones; las repeticiones dirigidas se indican arriba.

La ejecución completa comenzó antes de añadir la última prueba dirigida de concurrencia de C-10, que pasó por separado. No se afirma una ejecución completa verde.
