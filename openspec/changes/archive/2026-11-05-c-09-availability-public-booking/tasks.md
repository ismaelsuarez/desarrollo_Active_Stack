# Tasks

Antes de apply: revisar propuesta/diseño (governance ALTO) y obtener aprobación de implementación. Cargar skills locales según `.atl/skill-registry.md`: `fastapi`, `sqlalchemy`, `python-testing-patterns`, `tdd` con excepciones de AGENTS.md; resolver docs actuales mediante Context7 al implementar APIs. No cargar appointment-conflict-reviewer: su alcance local es C-07.

Cada tarea con comportamiento sigue safety net → RED ejecutado → GREEN mínimo → triangulación (mínimo dos casos por comportamiento) → refactor con pruebas verdes. Baseline fallido: informar preexistencia y detener ese frente. Guardar evidencia por tarea y no marcar [x] sin ejecución. Las tareas documentales se verifican leyendo el artefacto; no requieren tests artificiales.

Aceptación: los tres archivos `specs/*/spec.md`. No UI. Archivar, commit y push no forman parte de estas tareas.

## 1. Disponibilidad de dominio

- [x] 1.1 Registrar safety net de reserva/agenda/políticas C-07 y lecturas/vínculos C-08 antes de modificar: ejecutar suites relevantes con PostgreSQL real, guardar comandos/resultados y detener si hay fallos previos.
- [x] 1.2 Implementar disponibilidad pura sobre bloques, duración y excepciones globales/propias; verificar con RED/GREEN unitario bloque completo, pausa, duración de 30/60 y contigüidad (public-availability: Disponibilidad respeta agenda y ocupación).
- [x] 1.3 Incorporar ocupación semiabierta incluyendo sobreturnos y excluyendo cancelados/liberados; verificar unitarios con superposición parcial, exacta y extremos contiguos.
- [x] 1.4 Incorporar grilla anclada, parámetro cambiante, duración no múltiplo y futuro respecto del reloj; verificar 09:10 con pasos15/20, prestación20 y exclusión de pasado.
- [x] 1.5 Incorporar horizonte por fecha local y documentar algoritmo en README técnico; verificar día60/día61, medianoche UTC, día sin bloques y salida determinista sin alterar datos.

## 2. Lecturas públicas y limitación

- [x] 2.1 Extender proyecciones/puertos de configuración y consultas de agenda por intervalo; verificar integración SQL con teléfono/zona/días/máximo reales y aislamiento de consultorio sin migración ni N+1 por cada candidato.
- [x] 2.2 Implementar catálogos públicos activos con consultorio_sin_token; verificar integración/API sin sesión para las tres rutas, inactivos excluidos y datos mínimos (public-availability: Catálogo público mínimo del consultorio).
- [x] 2.3 Implementar GET publico/disponibilidad con query estricta profesional/prestación/fecha; verificar integración con bloqueos/turnos reales, fixture de sobreturno, 404 ajeno/inactivo, 422 query inválida y lista vacía sin huecos.
- [x] 2.4 Implementar adaptador de límite en memoria por origen/proceso con poda y capacidad acotada; verificar unitario cuota compartida por cuatro rutas, 429/Retry-After, renovación y origen independiente con reloj controlado.
- [x] 2.5 Integrar límite con resolución de origen existente y documentar rutas/alcance local en README/OpenAPI; verificar API contra cabecera X-Forwarded-For no confiable, ausencia de Redis obligatorio y falta de valores privados en respuestas/logs.

## 3. Reserva online y máximo atómico

- [x] 3.1 Agregar entrada POST específica por rol conservando la actual del personal; verificar API Paciente sólo profesional/prestación/inicio, 422 para paciente_id/duración/confirmar/origen/fin/consultorio incluso null, y OpenAPI con ambas formas (delta appointment-booking).
- [x] 3.2 Resolver ficha y verificación actuales y autorizar centralmente reserva propia; verificar API registro con ficha, vínculo preparado por fixture, correo sin verificar y sin ficha pendiente/rechazada/desvinculada, con 403 mínimo y sin historial parcial.
- [x] 3.3 Implementar bloqueo scoped de ficha y conteo futuro pendiente/confirmado antes de insertar; verificar integración máximo2, tercer409 con máximo, cupo tras cancelar y exclusión de pasados/finales, incluyendo futuros creados por personal.
- [x] 3.4 Demostrar atomicidad del máximo con dos conexiones/transacciones PostgreSQL independientes y un cupo disponible; verificar una201/otra409 y conteo final permitido con sólo un historial nuevo, sin sleeps como prueba de serialización.
- [x] 3.5 Aplicar grilla/horizonte en escritura y estado/origen online; verificar API día60/61, fuera de grilla, estado a48h exactas y47h59m, y preservar exenciones de personal.
- [x] 3.6 Reutilizar unidad, historial y puerto PlanificadorDeHitos existente; verificar integración reserva sin notificaciones con adaptador nulo y rollback de turno/historial ante fallo de historial, puerto o commit. Documentar frontera con C-16.

## 4. Lecturas y acciones propias

- [x] 4.1 Habilitar rama Paciente de GET turnos con filtro SQL por ficha vigente; verificar futuros/pasados, 200 vacío sin ficha, estado/fecha/profesional/prestación visibles y ausencia de datos de otras cuentas.
- [x] 4.2 Habilitar detalle e historial propios reutilizando autorización central; verificar mismo JWT anterior a fixture de desvinculación: listado vacío y 404 por identificador, además de ajeno/otro consultorio.
- [x] 4.3 Calcular acciones_permitidas con políticas y reloj, conservando respuesta actual del personal; verificar unitarios/API pendiente/confirmado/final y ambos lados de ventana, sin conferir permisos sólo por presentar una acción.
- [x] 4.4 Habilitar confirmar propio desde cuenta; verificar pendiente→confirmado con historial, ajeno404, liberado403 y fallo transaccional sin cambios, sin implementar enlace de correo.
- [x] 4.5 Habilitar cancelar propio por A1/A3/A4; verificar 24h exactas permitido y23h59m403 con teléfono, estado final403, ajeno404 antes de detalle temporal y hueco libre tras commit.
- [x] 4.6 Documentar lecturas, acciones y códigos en README/OpenAPI; verificar que las rutas usan vínculo actual y todos los casos de JWT previo conservan404 sin cambiar claims ni registrar PII.

## 5. Reprogramación propia

- [x] 5.1 Validar PATCH según rol y contexto actual; verificar API entrada Paciente sólo inicio, 422 duración incluso null, ajeno404 y ventana exacta24h frente a23h59m.
- [x] 5.2 Reutilizar cambio atómico preservando duración actual, grilla/horizonte y exclusión del propio turno; verificar integración ajuste45min, máximo lleno sin cupo extra, día61/fuera de grilla422 y destino ocupado409 sin cambiar original.
- [x] 5.3 Conservar ciclo, limpieza de marca y RN-29 en reprogramación; verificar a48h/47h59m, incremento único, historial, adaptador de hitos nulo y rollback completo cuando falla integración.
- [x] 5.4 Documentar PATCH y diferencia con duración de catálogo; verificar ejemplos de request/response y regresiones de reprogramación por personal, incluida duración ajustada.

## 6. Alternativas y carreras

- [x] 6.1 Calcular alternativas con lectura independiente después del rollback por ocupación; verificar unitarios orden/máximo3/horizonte, duración de creación frente a45min reprogramados y lista vacía válida, sin sesión abortada.
- [x] 6.2 Integrar409 de ocupación con alternativas sin cambiar409 de máximo; verificar API sobreturno activo no ofrecido/directo409, agenda llena y mínimos de datos sin identidad del ocupante. Documentar formato.
- [x] 6.3 Probar dos cuentas sobre el mismo hueco con PostgreSQL real y sesiones independientes; verificar una201/otra409, un turno/historial y alternativas sin el hueco perdido.
- [x] 6.4 Probar escritura online frente a desvinculación sobre la misma ficha con sesiones independientes; verificar relectura de vínculo tras bloqueo y ningún éxito autorizado por identidad obsoleta. Documentar orden efectivo de serialización y riesgo residual de alta simultánea con sobreturno.

## 7. Integración final

- [x] 7.1 Recorrer flujo API público→registro/verificación C-05→reserva→lista→confirmar→reprogramar→cancelar con reloj inyectado y PostgreSQL/Mailpit existentes; verificar sin UI, ni correos C-16 adelantados, ni datos ajenos en errores/logs.
- [x] 7.2 Ejecutar suites unitarias e integración completas y regresiones de personal C-07/C-08; verificar resultados reales sin omisiones ocultas y head único0008, reportando fallos ambientales o preexistentes separadamente.
- [x] 7.3 Validar change con openspec validate --strict --json y git diff --check; verificar todas las specs sin issues, completar evidencia TDD por tarea y revisar trazabilidad de todos los escenarios antes de marcar finalización.

## Workflow follow-up

- Presentar evidencia y obtener revisión de cierre; sincronizar specs y archivar sólo cuando se solicite.
- Commit y push requieren instrucción aparte.
