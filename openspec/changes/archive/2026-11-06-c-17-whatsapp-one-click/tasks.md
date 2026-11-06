# Tasks

## 1. Preparación y privacidad

- [x] 1.1 Ejecutar red de seguridad existente de avisos, barrido y consultas antes de modificar; registrar cantidad y detener ante fallos preexistentes. Aplicar TDD estricto a cada tarea y registrar RED/GREEN/triangulación.
- [x] 1.2 Crear normalización de teléfono y generador de mensaje/enlace; pruebas unitarias primero para formatos argentinos e internacionales, ausentes/ambiguos, caracteres especiales y exclusión de datos clínicos.
- [x] 1.3 Implementar persistencia durable independiente por canal y snapshot del hecho, con migración reversible si hace falta; probar contra PostgreSQL idempotencia, unicidad, actualización del único head y rollback sin alterar correo ni histórico.

## 2. Integración de eventos y barrido

- [x] 2.1 Programar hitos WhatsApp en transacción junto a reserva/reprogramación, incluso sin correo; probar bordes temporales, contacto inválido, rollback y doble programación con PostgreSQL real.
- [x] 2.2 Programar avisos de hechos por personal y liberación junto con el hecho; probar snapshot del ciclo, falta de email/teléfono, persistencia ante cambios posteriores y rollback del hecho.
- [x] 2.3 Preparar por barrido acotado e idempotente, independiente de correo; probar concurrencia, repetición, ventanas vencidas y condiciones RN-26/RN-60 con reloj inyectado.
- [x] 2.4 Garantizar que cancelar, liberar y reprogramar omitan hitos obsoletos sin omitir avisos de hechos; probar ambas intercalaciones concurrentes con PostgreSQL real.

## 3. Operación autorizada

- [x] 3.1 Añadir filtro `canal` y orden de urgencia para WhatsApp preparado, conservando proyección y compatibilidad; probar consultas válidas/invalidas, paginación, roles y aislamiento de consultorio.
- [x] 3.2 Añadir `GET /api/v1/notificaciones/{id}/whatsapp` con respuesta mínima y pruebas de enlace, estado, canal, 401/403/404/409 y no exposición de datos ajenos.
- [x] 3.3 Añadir `POST /api/v1/notificaciones/{id}/marcar-enviada` con transición condicional, actor y reloj; probar doble marca y carreras, permisos, aislamiento y que no afirma entrega.

## 4. Verificación integral

- [x] 4.1 Ejecutar pruebas de integración de ciclo completo con PostgreSQL real (programación, barrido, omisión, reprogramación y marca), y regresiones de email y liberación RN-60; documentar evidencia TDD y resultados.
- [x] 4.2 Ejecutar suite pertinente, verificar único head Alembic si hay migración, OpenSpec `--strict` y `git diff --check`; documentar fallos o límites sin afirmar pruebas no ejecutadas.

## Workflow follow-up

- Revisar resultados y archivar el change una vez completadas las tareas y la validación.
