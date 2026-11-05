# Tasks

Implementar solo tras nueva instrucción de apply y revisión explícita de [design.md](design.md), especialmente autenticación interna y purga. Cada tarea de código sigue safety net → RED ejecutado → GREEN → triangulación (mínimo dos casos por comportamiento) → refactor verde. Usar PostgreSQL real, reloj inyectado y datos sintéticos; registrar evidencia sin atribuir RED históricos a comportamiento existente. Cada grupo incorpora sus pruebas y documentación. No archive, commit ni push dentro de apply.

## 1. Base y migración incremental

- [x] 1.1 Registrar la aprobación y obtener baseline de suites afectadas C-03/C-05/C-07/C-08/C-09 y notificaciones antes de modificar sus archivos; verificar resultados y detenerse ante un fallo preexistente según el protocolo.
- [x] 1.2 Test primero de ciclo nullable y clave única de notificación; agregar modelo y migración posterior al head vigente y verificar repetición, carrera, ciclo/canal distinto y múltiples correos sin turno.
- [x] 1.3 Test primero de `barrido_estado` por consultorio con UUID, estado, fechas y conteos; verificar restricciones, aislamiento y ausencia de PII; agregar modelo/migración.
- [x] 1.4 Probar upgrade limpio y desde 0008 con filas legadas sin inventar ciclos ni borrar datos; verificar índices/CHECK previos, cabeza única y downgrade solo en BD desechable; documentar rollout y límite de rollback de datos.

## 2. Extensión compatible del despacho

- [x] 2.1 Test primero de resultado detallado por fila; extender el servicio conservando la fachada bool y verificar éxito, cuota, omisión, fallo y reclamación perdida sin confundir resultados de otros procesos.
- [x] 2.2 Test primero de vigencia de solicitud/recordatorio en programadas y enviando vencidas; verificar estados, ciclo nulo/ajeno, consultorio e inicio antes/igual/después del reloj; conservar rechazo de vinculación y cuenta.
- [x] 2.3 Cubrir los cinco tipos de avisos de hechos consumados con fixtures de turno cambiado/ya iniciado; verificar que no se omiten por estado o ciclo y respetan intentos/cupos.
- [x] 2.4 Verificar orden vigencia → intentos → cupo, bordes de TTL y limpieza de reclamada_en; probar topes completos con cierres omitida/fallida sin envío, elegibles intactas y medianoche local; documentar pequeña superación concurrente aceptada.
- [x] 2.5 Probar dos conexiones para reclamación exclusiva, SMTP fuera de transacción, caída tras enviar y resultado tardío exitoso/fallido; preservar fencing sin repetir implementación ya válida y registrar caracterización auténtica.

## 3. Barrido acotado y estado propio

- [x] 3.1 Test primero de selección en cuatro grupos de IDs finitos y deterministas; verificar límite por grupo, futuros excluidos, cuota de cuenta que no desplaza turnos y cada ID tratado una vez por ejecución.
- [x] 3.2 Test primero de `EjecutarBarrido` y sus cinco conteos propios; verificar lote mixto, pérdida de reclamación, error SMTP aislado, lote vacío y repetición sin reenviar enviadas.
- [x] 3.3 Test primero de marca durable al iniciar/terminar; verificar reinicio, error, interrupción y finalización fuera de orden por UUID sin bloquear el procesamiento de otros barridos.
- [x] 3.4 Probar dos barridos simultáneos más despacho inmediato con conexiones distintas, barreras y evidencia de filas diferentes; verificar ausencia de doble reclamación vigente y funcionamiento sin REDIS_URL.
- [x] 3.5 Probar recuperación tras tres horas de suspensión y varios lotes sin bucle de reintento inmediato; documentar conteos, límite interno y latencia del trabajo restante.

## 4. Disparadores y configuración

- [x] 4.1 Test primero de configuración sensible y flags SWEEP con defaults del diseño; verificar intervalo positivo, secreto vacío que deshabilita solo HTTP, 300 segundos por defecto y timeout menor que TTL; actualizar `.env.example` sin secretos reales.
- [x] 4.2 Test primero de dependencia de secreto `X-Sweep-Secret` en tiempo constante y POST interno; verificar 403 sin efectos para secreto ausente/incorrecto/no configurado, rechazo de cuerpo/query ajenos y consultorio solo de servidor.
- [x] 4.3 Verificar 200/resumen y 503 genérico ante fallo de infraestructura, y ausencia de `/internal/barrido` en OpenAPI; registrar el adaptador al mismo caso de uso y documentar invocación local con secreto de prueba.
- [x] 4.4 Test primero del bucle opcional en lifespan; verificar habilitado/deshabilitado, misma composición que HTTP, error recuperable seguido de nueva ejecución y sesiones independientes sin compartir AsyncSession.
- [x] 4.5 Probar cancelación y espera de la tarea propia durante shutdown, incluso envío en curso; verificar recuperación posterior por TTL y actualizar documentación/Compose de desarrollo sin worker ni Redis obligatorio.

## 5. Limpieza periódica segura

- [x] 5.1 Test primero de tokens de usuario y refresh expirados por consultorio; verificar expira_en menor/igual/mayor al reloj, credenciales válidas y filas ajenas conservadas, FKs y repetición idempotente.
- [x] 5.2 Reutilizar purgas de registro/ingreso y probar retención a 24 horas menos/igual/más un instante; verificar que siguen funcionando al escribir y que no eliminan otros datos del dominio.
- [x] 5.3 Integrar limpieza una vez por barrido en transacciones cortas aun sin correos; verificar fallo controlado/rollback sin afectar turnos y documentar cortes exactos y alcance de la purga.

## 6. Programación de avisos del personal

- [x] 6.1 Test primero del puerto de avisos y repositorio de notificaciones en UoW; verificar inserción idempotente por clave exacta y rollback de errores reales, sin commits ni SMTP desde el planificador.
- [x] 6.2 Test primero de aviso de reprogramación por Recepción/Administrador: turno e historial con nuevo ciclo y una notificación juntos; verificar rechazo/fallo de inserción sin efectos parciales y mantener contrato independiente de PlanificadorDeHitos.
- [x] 6.3 Test primero de cancelación por personal con ciclo vigente; verificar aviso durable que no se omite por cancelación, fallo de historial/commit y que acciones propias de pacientes no crean avisos por personal.
- [x] 6.4 Test primero de plantillas de datos mínimos y snapshot del hecho; verificar ambos tipos en Mailpit, horario capturado frente a cambios posteriores y ausencia de DNI, salud, motivo, obra social, tokens y secretos en contenido/logs.
- [x] 6.5 Probar contacto faltante y paciente sin cuenta vinculada; verificar cambio permitido sin destinatario inventado, evento técnico sin PII y entrega posterior/reintentos sin revertir el turno; documentar esta limitación y frontera C-16/C-17.

## 7. Bandeja e indicadores operativos

- [x] 7.1 Test primero de bandeja filtrada/paginada; verificar enum/limit/offset, orden estable, conjuntos vacíos y proyección mínima sin destinatario, cuerpo, enlaces ni error original; documentar el contrato API.
- [x] 7.2 Integrar dependencias de rol y política central NOTIFICACION_GESTIONAR; verificar Recepción/Administrador permitidos, otros roles 403, sin sesión 401 y aislamiento por consultorio tanto en bandeja como indicadores.
- [x] 7.3 Test primero de cantidades, antigüedades, cuota/alerta y vacío; verificar fechas futuras, día local, enviando vencidas incluidas como estado pero excluidas de cupo y umbral exacto .8.
- [x] 7.4 Test primero de GET indicadores con estado durable de última ejecución; verificar éxito/error/en curso/ausencia y fin viejo que no pisa un inicio posterior; documentar interpretación operativa sin prometer un historial ilimitado.

## 8. Integración y cierre de apply

- [x] 8.1 Ejecutar recorrido API+PostgreSQL+Mailpit: cambio staff → aviso durable → barrido → correo → bandeja/indicadores; incluir SMTP fallido y cuenta C-05 coexistiendo, con logs sin PII y ningún hito C-16 anticipado.
- [x] 8.2 Ejecutar regresión integral del backend sobre fuente final, migraciones y pruebas de concurrencia deterministas; informar pruebas exactas, fallos preexistentes si los hay y único head de Alembic, sin atribuir ejecuciones que no ocurrieron.
- [x] 8.3 Completar evidencia por tarea y trazabilidad de todos los escenarios de los tres deltas; ejecutar OpenSpec strict del change y git diff --check, verificar solo alcance aprobado y registrar cualquier desviación.
- [x] 8.4 Actualizar estado implementado en CHANGES manteniendo `[ ]` hasta archivo; guardar resumen Engram, retirar únicamente servicios temporales propios y verificar CLI apply all_done sin archivar ni publicar.

## Workflow follow-up

- Presentar resultado y evidencia al usuario. El archivo, sincronización de specs principales, commit y push requieren las instrucciones posteriores correspondientes.
