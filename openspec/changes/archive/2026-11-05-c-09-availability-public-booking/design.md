# Design

## Context

Ver `proposal.md` para motivación y los tres deltas para aceptación. Inspección del código: `GestionTurnos` de C-07 ya valida agenda/grilla, guarda turno e historial en una unidad y usa `PlanificadorDeHitos`/`PlanificadorSinEfectos`; el nombre conceptual `ProgramadorHitos` del roadmap no justifica crear otro puerto. `CrearTurno` es el caso anterior simple: no será la base para duplicar la lógica de C-07.

Los routers `turnos.py`, `acciones_turnos.py` y `agenda_turnos.py` hoy restringen estas entradas al personal/profesional. `ConsultarTurnos` carga contexto profesional pero no ficha de cuenta; sus consultas requieren una rama específica de paciente. `RepositorioAgendaTurnosSQL` todavía no proyecta teléfono, días ni máximo de turnos en `ParametrosAgenda`, aunque los parámetros existen en el modelo de consultorio. No se encontraron lecturas públicas de disponibilidad.

Dependencias C-05/C-07 archivadas; no se requieren endpoints de C-08 para preparar fixtures. Q-06/Q-11 resueltas por DD-27; Q-10 (familiares) no amplía la reserva propia. Q-18 son datos reales a configurar más adelante, no se inventan. Governance ALTO: diseño e implementación aprobados por el usuario el 2026-11-05.

## Goals / Non-Goals

Implementation approval: approved (2026-11-05, by user: "apruebo").

**Goals:** compartir validación y transacciones existentes, habilitar paciente sin ampliar autoridad de sus entradas, mantener contratos del personal y hacer comprobable el máximo bajo concurrencia.

**Non-Goals:** frontend, cambios de login/JWT, recuperación de vínculos, sobreturnos de C-10, correo/hitos reales C-16, barrido C-15, Redis obligatorio y migraciones nuevas.

## Decisions

### Disponibilidad pura y lecturas públicas acotadas

Nuevo cálculo puro de intervalos recibe bloques, excepciones, ocupación, duración, zona, parámetros y un instante del `Reloj`. Itera la grilla desde el inicio de cada bloque; usa intervalos semiabiertos y no redondea la duración. El caso de uso carga datos del consultorio por fecha, profesional y prestación; no materializa todo el historial. Horizonte por fechas locales, hoy incluido sólo para inicios futuros. Fuera del horizonte la lectura devuelve lista vacía; escrituras online inválidas responden 422.

Se elige cálculo compartido para evitar diferencias entre disponibilidad, alternativas y escritura; calcular sólo en frontend perdería autoridad y no sirve a clientes API. La disponibilidad es orientativa y cada escritura revalida.

Query de disponibilidad: `profesional_id`, `prestacion_id`, `fecha` (un día local por solicitud), esquema estricto. Los tres catálogos no aceptan filtros de consultorio. Respuestas públicas permiten sólo identificadores/nombres operativos, duración y datos públicos de consultorio. No exponer cuentas, DNI, teléfonos personales, ocupantes, bloques internos ni claves.

### Ruta existente con entrada específica por rol

Conservar POST y PATCH de `/api/v1/turnos` y las acciones existentes. Seleccionar validación estricta por rol después de identificar al principal, documentando ambas formas en OpenAPI sin que una unión permisiva permita campos del personal al paciente. Para Paciente POST sólo profesional, prestación e inicio; PATCH sólo inicio. Un `paciente_id` propio o `duracion_min=null` sigue siendo inválido. El personal conserva payloads y exenciones RN-64. El origen no es entrada: `online` para Paciente, `recepcion` para personal.

Se descarta exigir paciente_id al paciente porque delegaría la identidad y haría ambiguo el contrato. No se duplican rutas con otro prefijo que divergieran de CHANGES.

### Vínculo vigente y autorización central

Consultar cuenta y ficha vigente dentro de la operación; pasar `ficha_vigente_id`, correo verificado y parámetros a `autorizar`/contexto. Aplicar A2, rol, A1, A3 y A4 centrales; no implementar permisos propios en routers. El listado de Paciente filtra en SQL por consultorio y ficha, devolviendo vacío sin ficha. Detalle, historial y acciones de una antigua ficha responden 404 con el mismo JWT anterior. No agregar ficha ni permisos durables a los claims.

En escritura online, adquirir la ficha mediante SELECT FOR UPDATE filtrado por consultorio y usuario vigente y releer elegibilidad después de adquirir el bloqueo; así comparte serialización con desvincular de C-08 sin usarla como dependencia funcional. No cachear vínculo entre solicitudes. Correo verificado se comprueba contra cuenta actual para impedir reservar después de cambiarlo desde C-05.

### Máximo y reserva en una transacción

La reserva online bloquea fila de paciente antes de contar futuros pendiente/confirmado y antes de insertar, con una sesión por solicitud. Se incluyen turnos creados por personal; una segunda reserva online sobre la misma ficha espera y cuenta el commit anterior. El personal no queda sujeto al máximo y puede superarlo por regla RN-64(e), por lo que no se promete límite global frente a una creación de personal concurrente.

Reutilizar unidad, validación C-07, exclusión regular SQL y control explícito de sobreturnos. Turno, historial y llamada al puerto de hitos se confirman juntos. El puerto existente queda nulo. Reprogramar conserva duración, excluye el propio turno y no cuenta cupos nuevos. Traducciones selectivas de conflicto, sin convertir cualquier error de integridad en 409.

Se descarta contar antes de bloquear: dos transacciones podrían consumir el mismo cupo. No se cambia la restricción EXCLUDE ni se agregan candados globales.

### Acciones disponibles y alternativas

Añadir en respuestas de Paciente `acciones_permitidas` calculadas con el mismo reloj/políticas que ejecutan; mantener respuestas actuales del personal. Confirmar pendiente no hereda la ventana de cancelación. Denegación temporal al titular incluye teléfono del consultorio; un ajeno recibe antes 404 sin ese detalle.

Ante ocupación, terminar rollback de la escritura y abrir lectura independiente para alternativas; no consultar con sesión abortada por 23P01. Propuesta operativa: hasta tres intervalos del mismo profesional, desde el inicio solicitado en adelante dentro del horizonte, ordenados por inicio y excluyendo el turno propio al reprogramar. Usan duración vigente en creación y duración conservada en reprogramación. Sin alternativas devolver `[]`. Cantidad y orden se documentan como elección de presentación, sin garantizar permanencia del hueco.

### Límite público por proceso

Adaptador de ventana en memoria, compartido por las cuatro rutas en la instancia de aplicación y probado con reloj controlado. Propuesta operativa: 60 lecturas por origen cada 60 segundos, constantes internas reemplazables y pruebas con cuotas pequeñas. 429 con Retry-After, poda de ventanas vencidas y memoria acotada. Reutilizar resolución de origen existente y política de proxies; no confiar directamente en X-Forwarded-For ni registrar IP cruda. Sin dependencia externa o variable obligatoria nueva.

Se elige el adaptador exigido por roadmap; un límite distribuido sería otro alcance. No equivale a protección global entre réplicas.

## Risks / Trade-offs

- [Regular contra alta simultánea de sobreturno] → conservar y documentar el riesgo residual RN-17; fixture de sobreturno existente cubierta, no prometer exclusión SQL sobre ambos.
- [Cupo compite con personal exento] → garantizar serialización entre reservas online, conservar exención explícita del personal.
- [Intervalo deja de estar libre tras leer] → revalidar y ofrecer 409 con alternativas; no reservar al consultar.
- [Límite reiniciado o multiplicado por procesos] → documentar alcance local, memoria acotada y ninguna afirmación de protección distribuida.
- [Cambios de rutas compartidas] → safety net C-07/C-08 y pruebas de compatibilidad por rol antes de añadir comportamiento.
- [Evidencia histórica] → no reutilizar los 1161 tests C-08 como pruebas de C-09; apply debe ejecutar RED y GREEN propios.

## Migration Plan

Sin migración prevista: extender proyecciones/puertos sobre columnas existentes. Conservar único head `0008_turnos_core` y comprobarlo durante apply. Si surge necesidad real de esquema, revisar diseño antes de implementarla. Rollback del change revierte código nuevo y conserva datos; no borrar fichas ni turnos.

## UI Mockups

Decision: no (no UI), 2026-11-05. API backend; las pantallas públicas pertenecen a C-14. No se revisa la política visual del proyecto en este change.
