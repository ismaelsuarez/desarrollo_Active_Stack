# Tasks: c-04-abac-policies

## 1. Tipos de dominio, catálogo y estructuras base de decisión

- [x] 1.1 Implementar value objects `Accion`, `Decision`, `Intervalo` y `ContextoAcceso` en `backend/app/domain/value_objects/` y verificar con pruebas unitarias en `backend/tests/unit/policies/test_types.py`
- [x] 1.2 Exportar los tipos públicos desde `backend/app/domain/policies/__init__.py` y verificar resolución de imports limpios

## 2. Políticas A2 (Aislamiento de consultorio) y A1 (Dueño de agenda y titularidad)

- [x] 2.1 Implementar política pura `mismo_consultorio(usuario, recurso)` en `backend/app/domain/policies/consultorio.py` y verificar con pruebas unitarias que apruebe igual consultorio y rechace consultorio ajeno (404) en `backend/tests/unit/policies/test_consultorio.py`
- [x] 2.2 Implementar políticas puras `es_dueno_de_agenda(usuario, turno)` y `es_titular_del_turno(usuario, turno, ficha_vigente_id)` en `backend/app/domain/policies/turno.py` y verificar con pruebas unitarias en `backend/tests/unit/policies/test_titularidad.py` (titular con ficha vigente, rechazo con ficha `None`, turno ajeno 404, agenda ajena 403)

## 3. Políticas A3 (Estados y transiciones) y A4 (Ventanas temporales)

- [x] 3.1 Implementar `turno_es_modificable(turno)` y `transicion_permitida(turno, nuevo_estado)` según tabla canónica de RN-18 en `backend/app/domain/policies/turno.py` y verificar con pruebas unitarias en `backend/tests/unit/policies/test_transiciones.py` (estados terminales atendido/cancelado/liberado, ausente modificable solo vía corregir_ausente)
- [x] 3.2 Implementar `dentro_de_ventana_paciente(turno, ahora, horas_limite)` y `hora_de_inicio_alcanzada(turno, ahora)` en `backend/app/domain/policies/turno.py` y verificar con pruebas unitarias de límites temporales exactos (en el límite exacto y a $\pm 1$ segundo) en `backend/tests/unit/policies/test_ventanas.py`

## 4. Políticas de sobreturnos, pacientes, liberación de turnos e indicadores

- [x] 4.1 Implementar `puede_autorizar_sobreturno`, `puede_responder_sobreturno` y `sobreturno_cumple_condiciones` en `backend/app/domain/policies/sobreturno.py` y verificar con pruebas unitarias en `backend/tests/unit/policies/test_sobreturnos.py` (autorización por recepción/administrador, respuesta exclusiva del profesional de la agenda o administrador con agenda propia DD-24)
- [x] 4.2 Implementar políticas de ficha de paciente (`puede_ver_paciente`, `puede_editar_paciente`, vinculación/desvinculación) en `backend/app/domain/policies/paciente.py` y de ausentismo en `backend/app/domain/policies/indicadores.py`, verificando con pruebas unitarias en `backend/tests/unit/policies/test_paciente_indicadores.py`
- [x] 4.3 Implementar política de `turno.liberar` (aprobado en modo manual o con marca "sin confirmar" en automático; rechazo en automático sin marca; denegado a profesional y paciente) y verificar con pruebas unitarias en `backend/tests/unit/policies/test_liberacion.py`

## 5. Coordinador central de autorización (`autorizar`) y verificación de matriz completa

- [x] 5.1 Implementar punto de entrada centralizado `autorizar(usuario, accion, recurso=None, contexto=None) -> Decision` en `backend/app/domain/policies/acceso.py` evaluando en orden A2 -> RBAC -> A1/A3/A4 con denegación por defecto y mapeo canónico de códigos HTTP (404/403)
- [x] 5.2 Implementar suite exhaustiva parametrizada de la matriz completa rol × acción × atributo según KB 11 en `backend/tests/unit/policies/test_matriz_abac.py`, verificando denegación total para rol `administrativo` y registro de rechazos sin datos personales
- [x] 5.3 Ejecutar verificación completa de tests unitarios de políticas y suite global de pruebas (`pytest backend/tests/unit/policies/` y `pytest backend/tests/`) asegurando 100% verde sin regresiones

## Workflow follow-up

- Proceder a la fase de implementación mediante `/opsx:apply c-04-abac-policies` siguiendo el ciclo Strict TDD.
