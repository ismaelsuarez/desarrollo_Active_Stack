# absenteeism-indicator Specification

## Purpose
Permitir al administrador comprender el ausentismo y otras pérdidas de turnos por período y profesional.

## Requirements

### Requirement: Consulta aislada y autorizada
El sistema SHALL ofrecer `GET /api/v1/indicadores/ausentismo` solo al administrador y limitar los resultados al consultorio del principal, con período y filtro opcional por profesional.

#### Scenario: Rol sin acceso
- **WHEN** Recepción, Profesional, Paciente o Administrativo solicita el indicador
- **THEN** recibe 403 sin datos del indicador.

#### Scenario: Aislamiento
- **WHEN** el administrador consulta un período con turnos en otro consultorio
- **THEN** solo se agregan los turnos de su consultorio.

### Requirement: Cálculo de ausentismo
El sistema SHALL calcular ausentes / (atendidos + ausentes) usando turnos cuyo inicio ya llegó en el período, e informar por separado liberados, cancelados y turnos pasados sin cierre.

#### Scenario: Fórmula y estados
- **WHEN** hay 2 ausentes, 8 atendidos, 3 cancelados, 4 liberados y 1 pendiente pasado en el período
- **THEN** la tasa es 0,2 y los demás recuentos se muestran por separado sin contar como ausentes.

#### Scenario: Denominador vacío
- **WHEN** no hay atendidos ni ausentes
- **THEN** la tasa es nula y no se divide por cero.

#### Scenario: Futuro y filtro
- **WHEN** existen turnos futuros o de otro profesional y se filtra uno específico
- **THEN** no se incluyen en los agregados del resultado.

### Requirement: Presentación y filtros
La pantalla SHALL permitir seleccionar período y profesional, presentar resumen, evolución temporal y detalle por profesional y comunicar carga, error y ausencia de datos.

#### Scenario: Consulta exitosa
- **WHEN** el administrador aplica filtros válidos
- **THEN** ve los agregados del período, su evolución y detalle por profesional, incluyendo tasa sin dato cuando es nula.

#### Scenario: Error o sin datos
- **WHEN** falla la consulta o no existen datos
- **THEN** la pantalla informa el estado correspondiente y permite reintentar si falló.

### Requirement: Validación del período
La consulta SHALL rechazar períodos inválidos sin devolver agregados.

#### Scenario: Fechas invertidas
- **WHEN** desde es posterior a hasta
- **THEN** la API responde 422 y la pantalla informa el error.
