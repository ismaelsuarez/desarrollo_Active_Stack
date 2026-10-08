# Políticas de Acceso (RBAC + ABAC)

## Enfoque

La autorización combina dos capas:

1. **RBAC (base):** el rol del token (`administrador`, `recepcion`, `profesional`, `paciente`, `administrativo`) habilita o niega una acción en términos generales. La matriz está en [03_actores_y_roles.md](03_actores_y_roles.md).
2. **ABAC (refinamiento):** cuando el rol habilita la acción, **funciones de política** evalúan atributos del usuario, del recurso y del contexto para decidir si aplica a ese caso concreto.

Se implementa como **roles más funciones de política**, no como un motor genérico de políticas (decisión DD-04 en [09](09_decisiones_y_supuestos.md)). Es la opción más simple y mantenible para cinco roles y cuatro atributos, y deja las reglas legibles y probables con pruebas unitarias.

Principios:

- **Denegar por defecto.** Si ninguna política permite la acción, se rechaza.
- **Las políticas son funciones puras** en la capa de dominio, sin acceso a la base de datos ni al reloj del sistema (el instante `ahora` se inyecta). Esto las hace probables sin infraestructura.
- **La capa de aplicación consulta la política** antes de ejecutar un caso de uso, y la API traduce el rechazo a 403 (acción no permitida) o 404 (recurso de otro consultorio o ajeno, para no revelar su existencia).
- **El rechazo se registra** en los logs con usuario, acción y motivo, sin datos personales del paciente.

## Los cuatro atributos de la v1

| # | Atributo | Descripción | Regla de origen |
|---|----------|-------------|-----------------|
| A1 | Propietario del recurso | Un profesional solo toca los turnos de su propia agenda. Un paciente solo opera sobre sus propios turnos y su ficha. | RN-35, RN-38, RN-50 |
| A2 | Consultorio | Ningún usuario accede a datos de otro consultorio. Se compara `consultorio_id` del token con el del recurso. | RN-55, RN-56 |
| A3 | Estado del turno | Por ejemplo, un turno `atendido` no se edita ni se cancela; `liberado` y `cancelado` son finales. | RN-18, RN-19 |
| A4 | Ventana temporal | El paciente cancela o reprograma hasta 24 horas antes; atendido y ausente solo desde la hora de inicio; el sobreturno exige autorización vigente. | RN-33, RN-39, RN-44 |

A2 se evalúa **siempre y primero**, en todas las acciones. Aun con rol habilitado, un recurso de otro consultorio se rechaza.

## Catálogo de funciones de política

Las firmas son ilustrativas. Todas devuelven un booleano (o un resultado con motivo de rechazo). `Usuario` proviene de los claims del JWT.

```python
# domain/policies/consultorio.py
def mismo_consultorio(usuario: Usuario, recurso) -> bool:
    """A2. usuario.consultorio_id == recurso.consultorio_id."""

# domain/policies/turno.py
def es_dueno_de_agenda(usuario: Usuario, turno: Turno) -> bool:
    """A1. Profesional: turno.profesional_id es el del usuario."""

def es_titular_del_turno(usuario: Usuario, turno: Turno) -> bool:
    """A1. Paciente: turno.paciente_id es la ficha vinculada al usuario."""

def turno_es_modificable(turno: Turno) -> bool:
    """A3. Falso si el estado es atendido, cancelado o liberado."""

def transicion_permitida(turno: Turno, nuevo_estado: Estado) -> bool:
    """A3. Valida la tabla de transiciones de RN-18."""

def dentro_de_ventana_paciente(turno: Turno, ahora: datetime, horas_limite: int) -> bool:
    """A4. ahora <= turno.inicio - horas_limite (por defecto 24 h)."""

def hora_de_inicio_alcanzada(turno: Turno, ahora: datetime) -> bool:
    """A4. ahora >= turno.inicio (para atendido y ausente)."""

# domain/policies/sobreturno.py
def puede_autorizar_sobreturno(usuario: Usuario) -> bool:
    """RBAC. Solo recepcion o administrador."""

def sobreturno_cumple_condiciones(turno: Turno, horario, bloqueos) -> bool:
    """A4 y RN-43. Dentro del horario semanal y fuera de bloqueos;
    exige profesional avisado y autorizante registrado."""

# domain/policies/paciente.py
def puede_ver_paciente(usuario: Usuario, paciente: Paciente, turnos_del_profesional) -> bool:
    """A1. Paciente: ficha propia. Profesional: tiene turnos con el paciente
    en su agenda. Recepcion y administrador: cualquiera del consultorio."""

# domain/policies/indicadores.py
def puede_ver_ausentismo(usuario: Usuario) -> bool:
    """RBAC. Solo administrador (administrativo reservado)."""

# domain/policies/acceso.py  (punto de entrada)
def autorizar(usuario: Usuario, accion: Accion, recurso=None, contexto=None) -> Decision:
    """Evalúa A2 primero, luego RBAC, luego A1, A3 y A4 según la acción."""
```

Cada función se prueba con casos de permitido y denegado por atributo (ver estrategia de pruebas en [08](08_arquitectura_propuesta.md)).

## Acciones del catálogo

| Código | Acción |
|--------|--------|
| `agenda.ver` | Ver la agenda de un profesional |
| `turno.ver` | Ver el detalle de un turno |
| `turno.crear` | Crear un turno |
| `turno.reprogramar` | Reprogramar un turno |
| `turno.cancelar` | Cancelar un turno |
| `turno.confirmar` | Confirmar un turno |
| `turno.atendido` | Marcar atendido |
| `turno.ausente` | Marcar ausente |
| `turno.corregir_ausente` | Pasar de `ausente` a `atendido` |
| `turno.liberar` | Liberar un turno sin confirmar (modo manual) |
| `sobreturno.autorizar` | Autorizar un sobreturno |
| `sobreturno.responder` | Aprobar o rechazar un aviso de sobreturno |
| `paciente.ver` | Ver una ficha |
| `paciente.editar` | Crear o editar una ficha |
| `paciente.vincular` | Vincular cuenta con ficha existente |
| `configuracion.gestionar` | Horarios, bloqueos, prestaciones, profesionales, usuarios, parámetros |
| `notificacion.gestionar` | Ver notificaciones, abrir WhatsApp y marcar enviada |
| `indicador.ausentismo` | Ver el indicador de ausentismo |

## Matriz de decisión: rol por acción por atributo

Leyenda: **Sí** permitido; **No** denegado; **Cond.** permitido si se cumplen los atributos indicados; **Res.** reservado (rol sin funciones en la v1). A2 (mismo consultorio) se exige en todas las celdas permitidas y no se repite.

| Acción | Administrador | Recepción | Profesional | Paciente | Administrativo |
|--------|---------------|-----------|-------------|----------|----------------|
| `agenda.ver` | Sí (todas) | Sí (todas) | Cond.: A1 propietario de la agenda | No | Res. |
| `turno.ver` | Sí | Sí | Cond.: A1 turno de su agenda | Cond.: A1 titular | Res. |
| `turno.crear` | Sí | Sí | No | Cond.: solo para sí mismo, correo verificado, horario válido (RN-02, RN-14) | Res. |
| `turno.reprogramar` | Cond.: A3 modificable (RN-34) | Cond.: A3 modificable (RN-34) | No | Cond.: A1 titular, A3 modificable, A4 ventana de 24 h (RN-33) | Res. |
| `turno.cancelar` | Cond.: A3 modificable (RN-34) | Cond.: A3 modificable (RN-34) | No | Cond.: A1 titular, A3 modificable, A4 ventana de 24 h (RN-33) | Res. |
| `turno.confirmar` | Cond.: A3 estado `pendiente` | Cond.: A3 estado `pendiente` | No | Cond.: A1 titular, A3 estado `pendiente` (RN-30) | Res. |
| `turno.atendido` | Cond.: A3 `pendiente` o `confirmado`, A4 hora de inicio alcanzada | Cond.: A3 y A4 como Administrador | Cond.: A1 turno de su agenda, A3 y A4 | No | Res. |
| `turno.ausente` | Cond.: A3 y A4 (RN-44) | Cond.: A3 y A4 (RN-44) | Cond.: A1 turno de su agenda, A3 y A4 | No | Res. |
| `turno.corregir_ausente` | Cond.: A3 estado `ausente`, queda en el historial | Cond.: A3 estado `ausente`, queda en el historial | No | No | Res. |
| `turno.liberar` | Cond.: A3 estado `pendiente` y modo manual | Cond.: A3 estado `pendiente` y modo manual | No | No | Res. |
| `sobreturno.autorizar` | Cond.: A4 autorización explícita, profesional avisado (RN-39, RN-40, RN-41, RN-43) | Cond.: igual que Administrador | No | No | No |
| `sobreturno.responder` | No | No | Cond.: A1 sobreturno que afecta su agenda | No | No |
| `paciente.ver` | Sí | Sí | Cond.: A1 paciente con turnos en su agenda | Cond.: A1 ficha propia | Res. |
| `paciente.editar` | Sí | Sí | No | Cond.: A1 ficha propia, solo teléfono y correo (RN-47) | Res. |
| `paciente.vincular` | Sí | Sí | No | No | Res. |
| `configuracion.gestionar` | Sí | No | No | No | Res. |
| `notificacion.gestionar` | Sí | Sí | No | No | No |
| `indicador.ausentismo` | Sí | No | No | No | Res. |

Casos de rechazo representativos (para pruebas):

| Caso | Resultado | Atributo que decide |
|------|-----------|---------------------|
| Profesional A pide la agenda del profesional B | 403 | A1 |
| Usuario con `consultorio_id` distinto al del recurso | 404 | A2 |
| Cualquier rol edita un turno `atendido` | 403 | A3 (RN-19) |
| Paciente cancela 23 h 59 min antes del turno | 403, con el teléfono del consultorio | A4 (RN-33) |
| Paciente cancela el turno de otro paciente | 404 | A1 (RN-35) |
| Profesional marca `ausente` antes de la hora de inicio | 409 | A4 (RN-44) |
| Paciente intenta generar un sobreturno | 403 | RBAC (RN-39) |
| Sobreturno sin profesional avisado | 422 | A4 y RN-40 |
| Recepción pide el indicador de ausentismo | 403 | RBAC (RN-46) |

## Dónde se evalúa cada capa

| Momento | Qué se evalúa |
|---------|---------------|
| Dependencia de la API (antes del caso de uso) | Autenticación del JWT y rol habilitado para el endpoint (RBAC). |
| Caso de uso (capa de aplicación) | `autorizar(usuario, accion, recurso, contexto)`: A2, A1, A3 y A4 con el recurso ya cargado. |
| Base de datos | Restricciones que respaldan las reglas críticas: exclusión de solapamientos, unicidad de DNI y `consultorio_id` obligatorio. |
| Frontend | Solo oculta o deshabilita acciones por comodidad. No es una barrera de seguridad. |

## Evolución prevista

- Rol Administrativo: al llegar sus funciones se agregan filas a la matriz; los atributos existentes se reutilizan.
- Multiconsultorio completo: A2 ya está presente; se suma la administración por consultorio.
- Auditoría Ley 25.326: el registro de decisiones y accesos a datos personales se apoya en el punto de entrada único `autorizar`.
