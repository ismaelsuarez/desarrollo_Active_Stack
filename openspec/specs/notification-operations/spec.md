# notification-operations Specification

## Purpose

Permitir que Recepción y Administrador observen fallos de correo y salud del barrido de su consultorio sin exponer destinatarios, mensajes ni secretos.

## Requirements

### Requirement: Bandeja autorizada de notificaciones
GET /api/v1/notificaciones SHALL permitir a Recepción y Administrador consultar notificaciones propias con filtro de estado y paginación. SHALL rechazar otros roles y minimizar la proyección sin devolver destinatario, cuerpo, tokens o errores originales del transporte.

#### Scenario: Fallidas del consultorio
- **WHEN** Recepción consulta estado=fallida con paginación válida
- **THEN** obtiene solo filas fallidas de su consultorio con identificador, turno asociado, tipo, canal, estado, intentos y fechas operativas

#### Scenario: Roles y aislamiento
- **WHEN** un paciente, Profesional o Administrativo consulta la bandeja, o un administrador consulta habiendo filas de otro consultorio
- **THEN** los roles no autorizados reciben 403 y el administrador no recibe filas ajenas

#### Scenario: Consulta inválida o sin sesión
- **WHEN** se solicita un estado desconocido, una página inválida o no hay sesión
- **THEN** rechaza con 422 las entradas inválidas y con 401 la ausencia de autenticación, sin devolver información de notificaciones

### Requirement: Indicadores del correo
Los indicadores SHALL informar cantidad de fallidas, antigüedad de la programada más vieja, cantidad y antigüedad de enviando, conteo diario de correo, límites y alerta al umbral configurado, limitados al consultorio autorizado. Una colección vacía SHALL devolver cero y antigüedad nula.

#### Scenario: Estados y cuota del día
- **WHEN** hay filas programadas, enviando vigentes y vencidas, fallidas y enviadas en días distintos
- **THEN** los indicadores distinguen los estados, calculan las antigüedades con el reloj y el conteo diario incluye solo enviadas de ese día y reclamaciones vigentes

#### Scenario: Umbral y vacío
- **WHEN** el conteo llega al 80 por ciento configurado o no hay filas
- **THEN** activa la alerta en el umbral y para conjuntos vacíos devuelve cantidades cero y antigüedades nulas, sin inventar una ejecución previa

### Requirement: Estado durable del último barrido
El sistema SHALL conservar en PostgreSQL, por consultorio, el identificador, inicio, fin, estado y resumen del último barrido iniciado. SHALL distinguir ausencia, en curso, éxito y error y evitar que una ejecución anterior sobrescriba el resultado de una posterior.

#### Scenario: Reinicio de la API
- **WHEN** termina un barrido y después se reinicia la API
- **THEN** la consulta autorizada conserva su estado y resumen sin depender de memoria del proceso

#### Scenario: Finalización fuera de orden
- **WHEN** empieza un segundo barrido antes de terminar el primero
- **THEN** la finalización del primero no sustituye el estado del segundo y no impide que ambos procesen notificaciones distintas

#### Scenario: Interrupción o error
- **WHEN** una ejecución se interrumpe o falla antes de completar
- **THEN** su marca durable permite observar en curso con su antigüedad o error con hora de fin, sin credenciales ni mensaje original de la excepción
