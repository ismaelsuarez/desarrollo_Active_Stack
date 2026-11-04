---
name: appointment-conflict-reviewer
description: Revisar reglas de turnos odontológicos, solapamientos y escenarios faltantes antes de implementar C-07 (turnos-core). Usar al explorar, especificar o diseñar cambios de reservas, horarios, profesionales o disponibilidad; entregar escenarios trazables y decisiones pendientes, sin implementar ni modificar artefactos.
---

# Revisión de conflictos de turnos

Preparar un informe de dominio para C-07, «Gestión de turnos y prevención de solapamientos» (`turnos-core` en `CHANGES.md`). En cambios relacionados, conservar su alcance y separar las dependencias de C-07 de las capacidades de C-09 (reserva pública), C-10 (sobreturnos) y C-16 (liberación automática).

## Alcance y fuentes

Trabajar en modo de análisis: leer documentación y artefactos, proponer escenarios y pruebas; no implementar código, ejecutar migraciones, operar datos reales ni crear o modificar proposal, design, tasks o specs. Entregar el informe en la respuesta; guardarlo solo si el usuario indica un destino autorizado. No actualizar AGENTS.md, CLAUDE.md, CHANGES.md ni el registro como efecto de esta revisión.

Si las instrucciones locales piden regenerar el registro y eso escribe archivos, respetar el alcance de solo lectura: consultar el índice existente y declarar que no se actualizó, sin ejecutar el refresco.

Resolver las rutas siguientes desde la raíz del repositorio, no desde el directorio de la skill:

1. Leer `AGENTS.md`, `CLAUDE.md`, `.atl/skill-registry.md` y la entrada C-07 de `CHANGES.md`, incluidos «Leer antes», dependencias, riesgos y pruebas previstas. Las reglas duras del proyecto prevalecen ante conflictos con la KB; documentar el conflicto igualmente.
2. Consultar `knowledge-base/README.md` para los identificadores. Leer las secciones relevantes de:
   - `knowledge-base/04_modelo_de_datos.md`: turno, historial, exclusión y mapa de cumplimiento.
   - `knowledge-base/05_reglas_de_negocio.md`: agenda, solapamientos, estados, cancelación, reprogramación y sobreturnos.
   - `knowledge-base/06_funcionalidades.md`: épicas 5 y 6; otras historias solo si afectan el alcance.
   - `knowledge-base/07_flujos_principales.md`: ciclo de vida y flujos 6 y 8.
   - `knowledge-base/08_arquitectura_propuesta.md`: persistencia y estrategia de pruebas.
   - `knowledge-base/09_decisiones_y_supuestos.md` y `knowledge-base/10_preguntas_abiertas.md`: vigencia de DD, SU y Q.
   - `knowledge-base/11_politicas_de_acceso_abac.md`: acciones, atributos, matriz y códigos de rechazo.
3. Si se revisa un change existente, consultar `openspec list --json`, resolver su nombre real y luego `openspec status --change "<nombre>" --json`. Leer los artefactos disponibles y las specs principales relacionadas. No asumir que C-07 es el nombre del directorio ni confundirlo con C-00 (`crear-turno-sin-solapamientos`). Si falta la CLI, informar que no se verificó el estado y continuar la revisión documental, sin crear estructura ni afirmar que un artefacto existe o falta. Si la identificación es ambigua, pedir la selección antes de atribuir hallazgos a un change concreto.

Registrar para cada regla el identificador real, ruta y sección (líneas cuando estén disponibles), su alcance y su condición de decisión confirmada, supuesto vigente, reemplazado o pregunta abierta. No tratar una SU como confirmada por el solo hecho de figurar en una RN. No elegir silenciosamente entre fuentes contradictorias ni usar memoria o código como sustitutos de una decisión de dominio.

## Procedimiento de revisión

### 1. Delimitar las reglas aplicables

Construir un mapa regla → operación → escenario. Empezar por RN-10 a RN-24, RN-29, RN-32 a RN-38, RN-44 y RN-64; consultar RN-39 a RN-43, RN-55/RN-56 y RN-60 cuando intervengan sobreturnos, consultorio o liberación. Verificar estos identificadores contra los documentos actuales, sin congelar una copia de las reglas aquí.

Separar la revisión de C-07 de las funciones futuras: por ejemplo, usar sobreturnos, fichas sin cuenta o marcas «sin confirmar» como precondiciones de fixtures propuestas cuando el endpoint que los produce pertenece a otro change. No incorporar esos endpoints a C-07.

### 2. Comparar intervalos, recursos y límites

Usar fechas y horas sintéticas concretas, zona del consultorio y parámetros explícitos. Verificar:

- Coincidencia exacta, solapamiento parcial por ambos extremos y contención en ambas direcciones; intervalos separados y contiguos. La KB documenta `[inicio, fin)`: compartir solo un extremo no es solaparse. Para intervalos válidos A y B, hay intersección si `A.inicio < B.fin` y `B.inicio < A.fin`. Distinguir esa intersección temporal de la decisión de negocio según profesional, consultorio, estado y autorización.
- Mismo profesional y profesionales distintos, mismo consultorio y consultorios distintos. No deducir autorización de acceso de la ausencia de conflicto temporal. RN-10 vincula el box fijo al profesional: no inventar una política de boxes compartidos ni prohibir solapamientos por paciente sin fuente.
- Inicio y fin en los límites del bloque, fin fuera de horario, pausa entre bloques, bloqueos parciales y totales, excepciones globales y por profesional. Verificar que el turno completo cabe en un único bloque.
- Duración de prestación y duración ajustada, duración nula o negativa, grilla anclada al inicio del bloque y cambio de granularidad. Distinguir duración de catálogo de duración ajustada: no exigir que toda duración del catálogo sea múltiplo de la grilla sin respaldo. Revisar conservación de duración al mover y efecto de cambios del catálogo sobre turnos existentes.
- Estados que ocupan y liberan el hueco. Según la exclusión documentada, `pendiente`, `confirmado`, `atendido` y `ausente` participan; `cancelado` y `liberado` no. La marca «sin confirmar» no es otro estado ni libera el horario.
- Sobreturno autorizado frente a turno regular. La exclusión de PostgreSQL omite sobreturnos; crear o mover un regular sobre un sobreturno activo se rechaza por la aplicación. Registrar la carrera residual regular/sobreturno documentada sin presentar ese control como garantía atómica de la base. La autorización de sobreturnos pertenece a C-10 y no permite ignorar horario o bloqueos.
- Instantes antes, exactamente en y después de cada umbral aplicable: inicio del turno y `horas_confirmacion`; plazo del paciente y horizonte de reserva solo cuando el alcance los incluya. Usar `Reloj`, `timestamptz` y `America/Argentina/Buenos_Aires` según las reglas duras. No imponer al personal los límites de anticipación o cantidad de la reserva del paciente.

### 3. Revisar atomicidad y transiciones

Proponer dos reservas regulares simultáneas del mismo hueco: una prospera y otra recibe horario ocupado, sin persistencia parcial. Distinguir el chequeo previo de la garantía final de exclusión en PostgreSQL (`btree_gist`, `23P01` traducido a error de dominio y 409). SU-39 exige comprobar el código real en integración; una revisión documental no lo confirma.

Revisar reprogramación sobre la misma fila, sin conflicto consigo misma: conserva identificador y duración actual salvo ajuste autorizado; ante conflicto mantiene intactos horario, estado, ciclo, marca e historial. En éxito verificar reinicio del ciclo, limpieza de marca, estado resultante y trazabilidad según RN-21, RN-29, RN-32 y RN-37. Evaluar carreras con cancelar, liberar o mover solo hasta donde haya contrato documentado; si no se define el resultado, registrarlo como decisión pendiente, sin inventar reintentos, prioridad ni bloqueos.

Revisar transiciones finales, corrección de ausente, permisos por agenda y consultorio, y efectos sobre historial y notificaciones dentro del alcance. Ante «pasó la hora» frente a «hora alcanzada», u otra diferencia entre RN, flujo y matriz ABAC, exponer ambas referencias y el caso exacto que necesita decisión.

### 4. Clasificar y proponer pruebas

Clasificar cada escenario como **permitido**, **rechazado** o **ambiguo**. Separar funcionamiento normal, error de negocio y caso de borde. No clasificar como permitido un caso solo porque no se documentó una prohibición. Para ambigüedades, indicar «resultado esperado pendiente» y las alternativas a decidir; no convertir una recomendación en criterio de aceptación aprobado.

Proponer pruebas observables con datos concretos, precondiciones, acción, resultado y regla de respaldo. Cubrir camino normal y rechazo o borde por comportamiento; para límites temporales, usar los puntos antes/exacto/después. Indicar capa:

- Unidad: comparaciones, duración, transiciones y políticas puras con reloj inyectado.
- Integración con PostgreSQL real: exclusión, transacciones, persistencia y concurrencia; no SQLite ni base simulada. Usar sesiones/transacciones independientes y sincronización controlada para carreras; verificar resultados y estado final, sin depender de pausas arbitrarias.
- API: traducción del conflicto, validación y acceso. Citar la matriz antes de asignar 403/404/409/422; si el código no está decidido, dejarlo pendiente.

Son propuestas para la implementación posterior con TDD estricto, no tests ejecutados. No afirmar RED/GREEN, cobertura comprobada o concurrencia garantizada durante esta revisión.

## Informe de salida

Entregar en español, con estas secciones:

Ajustar la extensión al pedido: para una consulta acotada, mantener las secciones breves y cubrir los escenarios solicitados, declarando qué quedó sin revisar.

1. **Alcance y evidencia**: change identificado, fuentes consultadas, estado verificado o limitaciones y capacidades fuera de alcance.
2. **Reglas aplicables**: tabla `Regla/DD/SU/Q | Fuente y sección | Condición de vigencia | Operaciones afectadas`.
3. **Escenarios**: tabla `ID | Tipo (normal/error/borde) | Precondiciones y datos | Acción | Clasificación | Resultado observable | Referencias`. Usar IDs locales como `ESC-01`, sin crear nuevos códigos RN/DD oficiales.
4. **Pruebas propuestas**: tabla `Prueba | Escenario | Capa | Preparación y ejecución | Resultado esperado y estado final | Regla`. En carreras, especificar resultados permitidos, conteos y ausencia de cambios parciales; no fijar qué solicitud gana si el contrato no lo define.
5. **Riesgos, inconsistencias y decisiones pendientes**: evidencia de ambas fuentes cuando discrepan, impacto, pregunta concreta, responsable si está documentado y qué parte del alcance bloquea. Distinguir un riesgo aceptado de una nueva decisión. Revisar la vigencia de Q-26: en la documentación de base afecta al despliegue C-20 y no bloquea C-07 local/CI; no convertir preguntas ajenas al alcance en bloqueos.
6. **Recomendaciones para OpenSpec**: para `proposal.md`, alcance y exclusiones; para `design.md`, invariantes, transacciones y riesgos; para `tasks.md`, pruebas y dependencias; para specs, requisitos y escenarios Given/When/Then trazados a las reglas. Presentar recomendaciones, sin editar esos archivos ni dar por aprobadas las decisiones pendientes.

Cerrar con escenarios cubiertos, no revisados por falta de evidencia y preguntas que deben resolverse. Toda conclusión de permitido o rechazado debe tener una fuente; toda inferencia debe estar rotulada y toda expectativa no resuelta debe quedar pendiente.
