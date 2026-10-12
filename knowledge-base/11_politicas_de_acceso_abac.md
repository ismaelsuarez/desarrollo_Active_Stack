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
- **La política recibe los datos que necesita ya cargados.** El token de acceso no lleva la ficha del paciente (RN-06): cuando una política necesita el vínculo entre la cuenta y su ficha, la capa de aplicación carga la ficha vigente de la cuenta (la que tiene `paciente.usuario_id` igual al del usuario) y se la pasa a la función pura como argumento. La función no accede a la base de datos.
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

Las firmas son ilustrativas. Todas devuelven un booleano (o un resultado con motivo de rechazo). `Usuario` proviene de los claims del JWT y no trae la ficha del paciente; las funciones que la necesitan la reciben como argumento.

```python
# domain/policies/consultorio.py
def mismo_consultorio(usuario: Usuario, recurso) -> bool:
    """A2. usuario.consultorio_id == recurso.consultorio_id."""

# domain/policies/turno.py
def es_dueno_de_agenda(usuario: Usuario, turno: Turno) -> bool:
    """A1. turno.profesional_id es el del profesional vinculado a la cuenta (profesional.usuario_id),
    que la capa de aplicación carga de la base. La cuenta es de rol profesional o, si el
    administrador también atiende, de rol administrador (DD-24)."""

def es_titular_del_turno(usuario: Usuario, turno: Turno, ficha_vigente_id: int | None) -> bool:
    """A1. Paciente: turno.paciente_id es ficha_vigente_id, la ficha vinculada a la cuenta en ese
    momento, que la capa de aplicación carga de la base (paciente.usuario_id); no es un dato del
    token. None si la cuenta no tiene ficha: una cuenta sin ficha, o desvinculada (RN-63), nunca es titular."""

def turno_es_modificable(turno: Turno) -> bool:
    """A3. Falso si el estado es atendido, ausente, cancelado o liberado (RN-19). Un turno ausente
    solo admite la corrección a atendido, que es otra acción (turno.corregir_ausente)."""

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
    """A1. Paciente: ficha propia, es decir paciente.usuario_id es el del usuario (el vínculo vigente
    de la ficha ya cargada, no un dato del token). Profesional: tiene turnos con el paciente
    en su agenda. Recepcion y administrador: cualquiera del consultorio."""

# domain/policies/indicadores.py
def puede_ver_ausentismo(usuario: Usuario) -> bool:
    """RBAC. Solo administrador (administrativo reservado)."""

# domain/policies/acceso.py  (punto de entrada)
def autorizar(usuario: Usuario, accion: Accion, recurso=None, contexto=None) -> Decision:
    """Evalúa A2 primero, luego RBAC, luego A1, A3 y A4 según la acción. El contexto trae lo que las
    funciones necesitan y no está en el token: el instante actual del puerto `Reloj` y la ficha vigente
    de la cuenta del paciente."""
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
| `turno.liberar` | Liberar un turno `pendiente` en modo manual, o con la marca "sin confirmar" en cualquiera de los dos modos (por ejemplo, un turno que no cumplió las condiciones de la liberación automática, RN-60) |
| `sobreturno.autorizar` | Autorizar un sobreturno |
| `sobreturno.responder` | Aprobar o rechazar un aviso de sobreturno |
| `paciente.ver` | Ver una ficha |
| `paciente.editar` | Crear o editar una ficha |
| `paciente.vincular` | Resolver una solicitud de vinculación de cuenta (RN-62): vincular la cuenta con la ficha existente o rechazar la solicitud |
| `paciente.desvincular` | Desvincular una cuenta de su ficha, con motivo obligatorio (RN-63) |
| `paciente.reactivar` | Reactivar una ficha inactiva (RN-63); la v1 no tiene una acción que desactive una ficha, así que sirve para recuperar una cargada o corregida fuera de la aplicación (SU-47) |
| `configuracion.gestionar` | Horarios, bloqueos, prestaciones, profesionales, usuarios, parámetros |
| `notificacion.gestionar` | Ver notificaciones, abrir WhatsApp y marcar enviada |
| `indicador.ausentismo` | Ver el indicador de ausentismo |

## Matriz de decisión: rol por acción por atributo

Leyenda: **Sí** permitido; **No** denegado; **Cond.** permitido si se cumplen los atributos indicados; **Res.** reservado (rol sin funciones en la v1). A2 (mismo consultorio) se exige en todas las celdas permitidas y no se repite.

| Acción | Administrador | Recepción | Profesional | Paciente | Administrativo |
|--------|---------------|-----------|-------------|----------|----------------|
| `agenda.ver` | Sí (todas) | Sí (todas) | Cond.: A1 propietario de la agenda | No | Res. |
| `turno.ver` | Sí | Sí | Cond.: A1 turno de su agenda | Cond.: A1 titular | Res. |
| `turno.crear` | Sí | Sí | No | Cond.: solo para sí mismo (la cuenta debe tener ficha, RN-62), correo verificado, horario válido (RN-02, RN-14) | Res. |
| `turno.reprogramar` | Cond.: A3 modificable (RN-34) | Cond.: A3 modificable (RN-34) | No | Cond.: A1 titular, A3 modificable, A4 ventana de 24 h (RN-33) | Res. |
| `turno.cancelar` | Cond.: A3 modificable (RN-34) | Cond.: A3 modificable (RN-34) | No | Cond.: A1 titular, A3 modificable, A4 ventana de 24 h (RN-33) | Res. |
| `turno.confirmar` | Cond.: A3 estado `pendiente` | Cond.: A3 estado `pendiente` | No | Cond.: A1 titular, A3 estado `pendiente` (RN-30) | Res. |
| `turno.atendido` | Cond.: A3 `pendiente` o `confirmado`, A4 hora de inicio alcanzada | Cond.: A3 y A4 como Administrador | Cond.: A1 turno de su agenda, A3 y A4 | No | Res. |
| `turno.ausente` | Cond.: A3 y A4 (RN-44) | Cond.: A3 y A4 (RN-44) | Cond.: A1 turno de su agenda, A3 y A4 | No | Res. |
| `turno.corregir_ausente` | Cond.: A3 estado `ausente`, queda en el historial | Cond.: A3 estado `ausente`, queda en el historial | No | No | Res. |
| `turno.liberar` | Cond.: A3 estado `pendiente` y (consultorio en modo manual, o marca "sin confirmar" en cualquier modo, RN-60) | Cond.: A3 estado `pendiente` y (consultorio en modo manual, o marca "sin confirmar" en cualquier modo, RN-60) | No | No | Res. |
| `sobreturno.autorizar` | Cond.: A4 autorización explícita, profesional avisado (RN-39, RN-40, RN-41, RN-43) | Cond.: igual que Administrador | No | No | No |
| `sobreturno.responder` | Cond.: A1 solo el sobreturno que afecta su propia agenda, si el administrador tiene una (DD-24); nunca el de otro profesional | No | Cond.: A1 sobreturno que afecta su agenda | No | No |
| `paciente.ver` | Sí, con la cuenta vinculada (RN-63) | Sí, con la cuenta vinculada (RN-63) | Cond.: A1 paciente con turnos en su agenda, sin datos de la cuenta | Cond.: A1 ficha propia, sin el bloque de la cuenta | Res. |
| `paciente.editar` | Sí | Sí | No | Cond.: A1 ficha propia, solo teléfono y correo (RN-47) | Res. |
| `paciente.vincular` | Sí | Sí | No | No | Res. |
| `paciente.desvincular` | Sí | Sí | No | No | Res. |
| `paciente.reactivar` | Sí | Sí | No | No | Res. |
| `configuracion.gestionar` | Sí | No | No | No | Res. |
| `notificacion.gestionar` | Sí | Sí | No | No | No |
| `indicador.ausentismo` | Sí | No | No | No | Res. |

Casos de rechazo representativos (para pruebas). Regla de códigos, con tres cláusulas que no se solapan:

- **404** cuando revelar que el recurso existe expondría datos: los turnos y las fichas de otra persona y cualquier recurso de otro consultorio.
- **403** cuando la existencia del recurso ya es conocida dentro del consultorio y solo se deniega la acción: la agenda de otro profesional, una acción que el rol no puede hacer y los rechazos por estado o por ventana de tiempo.
- **409** para los conflictos con el estado actual de los datos que se detectan al escribir: horario ocupado, una escritura condicional que no afecta ninguna fila y el límite de turnos activos de RN-64 (d). El 409 no es un código de política.

422 es una entrada inválida. La última columna de la tabla indica qué cláusula aplica a cada caso.

| Caso | Resultado | Atributo que decide | Cláusula de la regla |
|------|-----------|---------------------|----------------------|
| Profesional A pide la agenda del profesional B | 403 | A1 | 403: la agenda de B existe en el consultorio y solo se deniega la acción |
| Usuario con `consultorio_id` distinto al del recurso | 404 | A2 | 404: recurso de otro consultorio |
| Cualquier rol edita un turno `atendido` | 403 | A3 (RN-19) | 403: rechazo por estado |
| Paciente cancela 23 h 59 min antes del turno | 403, con el teléfono del consultorio | A4 (RN-33) | 403: rechazo por ventana de tiempo |
| Paciente cancela el turno de otro paciente | 404 | A1 (RN-35) | 404: turno de otra persona |
| Profesional opera por identificador un turno de la agenda de otro profesional | 404 | A1 | 404: turno de otra persona |
| Cuenta desvinculada, con un token de acceso emitido antes, pide su antigua ficha o uno de sus turnos por identificador | 404 | A1 (RN-06, RN-63) | 404: ficha y turnos de otra persona (la cuenta ya no es la titular) |
| Cuenta sin ficha vinculada (solicitud `pendiente` o `rechazada`, o desvinculada) lista sus turnos con `GET /turnos` | 200 con lista vacía | A1 (RN-06, RN-63) | Ninguna: no es un rechazo, la lista se filtra por el vínculo vigente |
| Profesional marca `ausente` antes de la hora de inicio | 403 | A4 (RN-44) | 403: rechazo por ventana de tiempo |
| Paciente intenta generar un sobreturno | 403 | RBAC (RN-39) | 403: acción que el rol no puede hacer |
| Profesional o Paciente desvincula una cuenta o reactiva una ficha | 403 | RBAC (RN-63) | 403: acción que el rol no puede hacer |
| Pedido de sobreturno sin motivo o sin autorización explícita | 422 | Validación de entrada (RN-39, RN-41); el aviso al profesional lo registra el servidor en la misma operación (DD-30) | 422: entrada inválida |
| Recepción pide el indicador de ausentismo | 403 | RBAC (RN-46) | 403: acción que el rol no puede hacer |
| Un paciente con el máximo de turnos activos reserva otro (RN-64 d) | 409, con el máximo | Regla de negocio, no una política | 409: conflicto con el estado actual de los datos |
| Dos reservas simultáneas del mismo horario | 409 | Restricción de exclusión (RN-24) | 409: conflicto detectado al escribir |

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
