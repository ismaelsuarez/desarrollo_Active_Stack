# Tasks

Approval: approved (2026-11-05, by user). El usuario aprobó el diseño y autorizó apply con TDD estricto mediante «si», incluidas las decisiones sobre ventanas, tokens sin cuenta y trazabilidad del enlace. No marcar tareas hechas por existir estos artefactos.

Todas las tareas que agregan comportamiento siguen safety net → RED ejecutado → GREEN mínimo → TRIANGULATE (dos casos distintos como mínimo) → REFACTOR con pruebas verdes. Si el baseline falla, informar fallo preexistente sin corregirlo dentro del change. PostgreSQL real para restricciones, repositorios y concurrencia; reloj inyectado, sin SQLite ni mocks de persistencia. Registrar cada ciclo y escenario→test en `evidence.md` a medida que se termina el grupo, sin inventar RED histórico.

## 1. Contrato de tokens y migración

- [x] 1.1 Capturar baseline de modelos, migraciones, cuentas y turnos antes de modificarlos; verificar ejecución y documentar conteo/comando/head reales en evidencia, deteniéndose ante fallo preexistente.
- [x] 1.2 Escribir RED de confirmar_turno sin usuario con turno/ciclo válido y rechazos por propósito; implementar modelo y revisión descendiente del head real, sin agregar ciclo ya existente. Verificar PostgreSQL acepta solo las combinaciones autorizadas y conserva tokens de cuenta.
- [x] 1.3 Probar upgrade/downgrade/upgrade con datos compatibles y preflight de downgrade con tokens sin cuenta incompatibles; verificar falla sin pérdida de datos ni cambios parciales, un head y exclusión intacta. Documentar rollback y discrepancia roadmap/modelo en evidencia del grupo.

## 2. Programación y omisión transaccionales

- [x] 2.1 Diseñar con RED la política temporal de reserva/reprogramación a >48 h, =48 h, 30 h, =24 h y 10 h, más parámetros distintos de 48/24/12; verificar programación exacta, RN-29 y omisión de hitos alcanzados antes de generalizar.
- [x] 2.2 Implementar planificador y repositorios sobre la misma UoW, con pruebas PostgreSQL de deduplicación repetida/concurrente y rollback por fallo de programación; verificar turno, historial y notificaciones se confirman o revierten juntos.
- [x] 2.3 Conectar planificador real a crear/reprogramar y probar por HTTP personal y paciente; verificar las filas existen sin enviar SMTP dentro de la transacción y no queda PlanificadorSinEfectos en composición real.
- [x] 2.4 Agregar omisión inmediata de solicitud/recordatorio programada/preparada al reprogramar, cancelar y liberar; verificar todos los canales y ciclos correspondientes, conservando avisos de hechos consumados y reclamaciones en vuelo. C-17 cubre sus propias preparadas WhatsApp.
- [x] 2.5 Probar reprogramación de marcado con limpieza de marca/fechas, ciclo nuevo y fallo transaccional que conserva el ciclo original; documentar la tabla temporal y trazabilidad de estos escenarios en evidencia del grupo.

## 3. Ventanas, enlaces y registro del despacho

- [x] 3.1 Agregar RED para solicitudes antes/exactamente T-48 y antes/exactamente T-24, recordatorios antes/exactamente T-24 y antes/exactamente T-12; implementar ventanas aprobadas y verificar programadas/enviando vencidas con intentos agotados o cupos completos se omiten antes de consumir intento.
- [x] 3.2 Emitir token opaco al reclamar una solicitud elegible con/sin cuenta y componer enlace en memoria; verificar Mailpit recibe fragmento /confirmar-turno#token=, token_hash/turno/ciclo/vencimiento correctos y ausencia del claro en filas, cuerpos persistidos y logs.
- [x] 3.3 Probar caída/reintento de solicitud con enlaces múltiples del mismo ciclo, sin invalidar el anterior, y vencimiento al inicio; verificar al menos una vez, recuperación TTL y fencing existentes sin cambiar la semántica de cuenta.
- [x] 3.4 Componer recordatorio al reclamar según modo, estado, marca y solicitud email enviada del ciclo actual; verificar advertencia solo cuando corresponde y ausencia de advertencia para solicitud ausente/programada/enviando/fallida/omitida/otro ciclo, manual, marcado o confirmado.
- [x] 3.5 Registrar fechas operativas solo junto al resultado exitoso propio y para el ciclo actual; probar reprogramación durante SMTP y pérdida de reclamación, verificando que no se contaminan fechas del ciclo nuevo ni resultados ajenos.
- [x] 3.6 Validar mensajes por Mailpit con datos sintéticos sensibles en ficha/turno; verificar fecha/hora local y datos mínimos sin DNI, obra social, notas, motivo interno ni secretos, y documentar ventanas/fallos en evidencia del grupo.

## 4. Confirmación por enlace

- [x] 4.1 Diseñar RED del caso de uso con token válido, con/sin cuenta y consultorio diferente del activo; implementar confirmación, consumo e historial atómicos, verificando identidad/medio propuestos y ninguna sesión o cuenta artificial.
- [x] 4.2 Probar token inexistente, usado, vencido en el borde, tipo incorrecto y ciclo anterior; verificar 400 genérico sin cambios y sin datos personales.
- [x] 4.3 Probar liberado y otros estados incompatibles; verificar 409 sin consumo parcial y mensaje de reservar de nuevo para liberado, además de rollback completo si falla historial.
- [x] 4.4 Agregar POST /api/v1/turnos/confirmar-por-enlace con cuerpo solo token y respuesta mínima; verificar 200 sin sesión, 422 por consultorio_id u otro campo extra y que ninguna otra acción acepta ese bearer. Documentar contrato en OpenAPI y evidencia.
- [x] 4.5 Probar PostgreSQL con solicitudes simultáneas usando el mismo token y tokens distintos del mismo turno, además de reprogramación/cancelación concurrente; verificar como máximo una confirmación y ninguna escritura obsoleta o duplicación de historial.

## 5. Decisión automática y marca por ciclo

- [x] 5.1 Diseñar RED de decisión pura automático/manual y RN-60 para solicitud enviada/ausente/programada/enviando/fallida/omitida/otro ciclo; verificar T-12 exacto y un instante antes con diferentes parámetros.
- [x] 5.2 Implementar selección finita y ordenada de pendientes sin marca cuyo hito llegó y no comenzaron; verificar más de un lote, exclusión de confirmados/marcados/otros consultorios y que iniciados no se reevalúan al repetir.
- [x] 5.3 Implementar UPDATE condicional de liberación con solicitud email enviada del ciclo vigente, reloj fresco e historial/aviso en la misma transacción; verificar hueco disponible y rollback total si falla historial o programación.
- [x] 5.4 Implementar marca condicional y su historial sin liberar ni avisar; verificar modo manual y cada falta de prueba de envío, además de solicitud enviada después de marcar que nunca dispara liberación en ese ciclo.
- [x] 5.5 Probar dos barridos concurrentes para liberar y para marcar contra PostgreSQL; verificar un solo historial por decisión y un solo aviso ganador, sin candado global o reclamación artificial de turno.
- [x] 5.6 Probar confirmar/cancelar/reprogramar contra la decisión, incluyendo inicio alcanzado entre selección y escritura; verificar guardas de estado/marca/ciclo/inicio y ningún efecto de una decisión perdedora.
- [x] 5.7 Integrar evaluación antes del despacho en EjecutarBarrido conservando cinco conteos de correo y ambos disparadores; verificar retraso hasta T-12, cupo agotado, aviso durable y ausencia de correos retroactivos que habiliten liberar. Documentar decisiones y límites de lote en evidencia del grupo.

## 6. Avisos durables de hechos consumados

- [x] 6.1 Programar resumen_reserva en la reserva y cancelacion_por_paciente solo al cancelar el titular; verificar personal/paciente, una fila por ciclo y ausencia de duplicados o aviso de personal erróneo.
- [x] 6.2 Probar rollback por programación fallida y cambio de turno posterior antes del envío; verificar snapshot de horario/contacto original y vigencia siempre de resumen, cancelación y liberación.
- [x] 6.3 Probar ficha sin contacto utilizable y SMTP fallido tras commit; verificar no inventa destinatario, no bloquea el hecho, deja señal sin PII y respeta reintentos. Registrar evidencia y alcance de privacidad del grupo.

## 7. Lista operativa y resolución

- [x] 7.1 Agregar sin_confirmar al repositorio/caso de uso/router con RED de marca, estado, consultorio y orden; verificar solo pendientes marcados, incluso ya iniciados que necesitan resolución, y lista mínima sin PII.
- [x] 7.2 Probar autorización Recepción/Administrador y rechazos Profesional/Paciente/Administrativo para true; verificar sin filtro/false conserva el contrato previo de cada rol. Documentar filtro y errores en OpenAPI.
- [x] 7.3 Probar confirmar/cancelar/liberar/reprogramar desde la lista por endpoints existentes; verificar salida del listado, limpieza de marca al reprogramar y nueva evaluación del ciclo futuro, dejando trazabilidad en evidencia.

## 8. Verificación integrada del change

- [x] 8.1 Ejecutar recorrido integrado con reloj, PostgreSQL y Mailpit: reservar→solicitud→confirmar por enlace→recordatorio; pendiente con solicitud enviada→liberación; fallo de solicitud→marca→resolución manual; verificar ambos disparadores usan la misma composición y evidenciar comandos/resultados.
- [x] 8.2 Ejecutar suites de regresión pertinentes y suite backend completa sobre la fuente final; verificar cero fallos/omisiones no justificadas, head único y diff --check limpio, sin repetir pruebas sin cambios o dudas nuevas.
- [x] 8.3 Completar evidence.md con escenario→test, safety net y tabla TDD por tarea (RED/GREEN/TRIANGULATE/REFACTOR), revisión de privacidad/concurrencia y limitaciones reales; validar change --strict, estado apply por CLI y consistencia entre seis deltas/propuesta/diseño/tareas antes de informar apply listo para revisión.

## Workflow follow-up

- Tras revisión de implementación y orden explícita, sincronizar specs y archivar con openspec-archive-change; actualizar CHANGES.md solo al cierre correspondiente.
- Commit y push quedan fuera de este plan hasta instrucción del usuario.
