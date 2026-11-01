# Proposal: c-04-abac-policies

## Why

La autenticación base y el control de acceso por roles (RBAC) implementados en C-03 determinan qué acciones generales puede intentar un rol, pero no pueden resolver si un usuario específico tiene derecho a operar sobre una instancia concreta de un recurso. En un consultorio odontológico, un profesional solo debe acceder a su propia agenda, un paciente solo a sus propios turnos y ficha, y ciertas operaciones críticas (cancelar, reprogramar, atender, liberar) dependen estrictamente del estado del turno y de ventanas de tiempo relativas (24 horas antes, hora de inicio alcanzada, aislamiento estricto de consultorio).

Este change implementa las políticas de acceso ABAC (Attribute-Based Access Control) como funciones puras en la capa de dominio, gobernando los cuatro atributos centrales del sistema (A1 propietario/titular, A2 consultorio, A3 estado del turno y A4 ventana temporal) con denegación por defecto y sin acoplamiento a infraestructura.

## What Changes

- **Funciones de política puras en el dominio (`app/domain/policies/`)**:
  - **A2 Consultorio (evaluado siempre y primero)**: `mismo_consultorio(usuario, recurso)`.
  - **A1 Propietario/Titular**: `es_dueno_de_agenda(usuario, turno)` y `es_titular_del_turno(usuario, turno, ficha_vigente_id)`.
  - **A3 Estado del turno**: `turno_es_modificable(turno)` y `transicion_permitida(turno, nuevo_estado)` aplicando la tabla canónica de transiciones de RN-18.
  - **A4 Ventana temporal**: `dentro_de_ventana_paciente(turno, ahora, horas_limite)` (ventana de 24h) y `hora_de_inicio_alcanzada(turno, ahora)`.
  - **Políticas complementarias**: `puede_autorizar_sobreturno(usuario)`, `sobreturno_cumple_condiciones(turno, horario, bloqueos)`, `puede_ver_paciente(usuario, paciente, turnos_del_profesional)`, `puede_ver_ausentismo(usuario)`.
- **Catálogo de acciones y decisiones tipadas (`app/domain/policies/acceso.py` y tipos asociados)**:
  - Enumeración/catálogo exhaustivo de acciones: `agenda.ver`, `turno.ver`, `turno.crear`, `turno.reprogramar`, `turno.cancelar`, `turno.confirmar`, `turno.atendido`, `turno.ausente`, `turno.corregir_ausente`, `turno.liberar`, `sobreturno.autorizar`, `sobreturno.responder`, `paciente.ver`, `paciente.editar`, `paciente.vincular`, `paciente.desvincular`, `paciente.reactivar`, `configuracion.gestionar`, `notificacion.gestionar`, `indicador.ausentismo`.
  - Estructura `Decision` inmutable con `permitido: bool`, `motivo: str | None` y código HTTP sugerido (`codigo_http: int | None`).
  - Punto de entrada unificado `autorizar(usuario, accion, recurso=None, contexto=None) -> Decision` con denegación por defecto (default-deny).
  - Regla de mapeo de códigos según KB 11: `404` para recursos ajenos/otro consultorio (evitar fugas de existencia), `403` para acciones denegadas dentro del consultorio conocido.
  - Soporte de contexto inyectado (`ContextoAcceso`): instante actual inyectado (`ahora: datetime`) y ficha vigente del paciente (`ficha_vigente_id: int | None`).
- **Entidades y tipos auxiliares de dominio**:
  - Modelo de intervalo de tiempo (`Intervalo`) y extensiones necesarias en entidades de dominio para evaluación pura de políticas sin tocar base de datos ni `datetime.now()`.
  - Tratamiento del rol `administrativo` como reservado (sin acceso funcional en v1).

## Capabilities

### New Capabilities
- `attribute-based-access-control`: Políticas de autorización basadas en atributos (A1, A2, A3, A4) mediante funciones puras en dominio, catálogo de acciones, contexto inyectado y punto de entrada `autorizar` con regla de códigos de respuesta (403/404).

### Modified Capabilities
<!-- Ninguna capability existente modifica sus requisitos funcionales -->

## Impact

- **Código afectado**:
  - `backend/app/domain/policies/`: nuevo paquete de dominio con módulos `consultorio.py`, `turno.py`, `sobreturno.py`, `paciente.py`, `indicadores.py`, `acceso.py` y tipos asociados.
  - `backend/app/domain/value_objects/`: nuevos value objects (`intervalo.py`, `decision.py`, `accion.py`).
  - `backend/tests/unit/policies/`: suite exhaustiva de pruebas unitarias puras que verifican la matriz rol × acción × atributo (casos permitidos, denegados y valores de borde temporales exactos).
- **APIs y dependencias**: No modifica endpoints REST directamente en este change; prepara el motor de autorización que consumirán los casos de uso a partir de C-05, C-06 y C-07. No agrega dependencias externas (usa la biblioteca estándar de Python y los tipos ya existentes en `app.domain`).
