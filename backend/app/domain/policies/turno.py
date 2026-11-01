from datetime import datetime, timedelta
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno

TRANSICIONES_PERMITIDAS: dict[EstadoTurno, frozenset[EstadoTurno]] = {
    EstadoTurno.PENDIENTE: frozenset(
        {
            EstadoTurno.CONFIRMADO,
            EstadoTurno.ATENDIDO,
            EstadoTurno.AUSENTE,
            EstadoTurno.CANCELADO,
            EstadoTurno.LIBERADO,
        }
    ),
    EstadoTurno.CONFIRMADO: frozenset(
        {
            EstadoTurno.ATENDIDO,
            EstadoTurno.AUSENTE,
            EstadoTurno.CANCELADO,
        }
    ),
    EstadoTurno.AUSENTE: frozenset(
        {
            EstadoTurno.ATENDIDO,  # Solo corregir_ausente (RN-19)
        }
    ),
    EstadoTurno.ATENDIDO: frozenset(),  # Estado terminal
    EstadoTurno.CANCELADO: frozenset(),  # Estado terminal
    EstadoTurno.LIBERADO: frozenset(),  # Estado terminal
}


def es_dueno_de_agenda(usuario: Principal, turno: Turno, profesional_id: int | None = None) -> bool:
    """A1. Verifica si el turno pertenece a la agenda del profesional o administrador con agenda."""
    if usuario is None or turno is None or profesional_id is None:
        return False

    if usuario.rol not in (RolUsuario.PROFESIONAL, RolUsuario.ADMINISTRADOR):
        return False

    return turno.profesional_id == profesional_id


def es_titular_del_turno(usuario: Principal, turno: Turno, ficha_vigente_id: int | None) -> bool:
    """A1. Verifica si el turno pertenece a la ficha del paciente autenticado."""
    if usuario is None or turno is None or ficha_vigente_id is None:
        return False

    if usuario.rol != RolUsuario.PACIENTE:
        return False

    return turno.paciente_id == ficha_vigente_id


def turno_es_modificable(turno: Turno) -> bool:
    """A3. Falso si el estado es atendido, ausente, cancelado o liberado (RN-19)."""
    if turno is None:
        return False
    return turno.estado in (EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO)


def transicion_permitida(turno: Turno, nuevo_estado: EstadoTurno) -> bool:
    """A3. Valida si la transición de estado solicitada cumple con la tabla de transiciones de RN-18."""
    if turno is None or nuevo_estado is None:
        return False
    destinos_validos = TRANSICIONES_PERMITIDAS.get(turno.estado, frozenset())
    return nuevo_estado in destinos_validos


def dentro_de_ventana_paciente(turno: Turno, ahora: datetime, horas_limite: int = 24) -> bool:
    """A4. Verifica si el instante 'ahora' está dentro de la ventana permitida para el paciente."""
    if turno is None or ahora is None:
        return False
    if ahora.tzinfo is None or turno.inicio.tzinfo is None:
        raise ValueError("ahora y turno.inicio deben tener zona horaria explícita")

    limite = turno.inicio - timedelta(hours=horas_limite)
    return ahora <= limite


def hora_de_inicio_alcanzada(turno: Turno, ahora: datetime) -> bool:
    """A4. Verifica si el instante 'ahora' alcanzó o superó el inicio del turno (RN-44)."""
    if turno is None or ahora is None:
        return False
    if ahora.tzinfo is None or turno.inicio.tzinfo is None:
        raise ValueError("ahora y turno.inicio deben tener zona horaria explícita")

    return ahora >= turno.inicio


def puede_liberar_turno(
    usuario: Principal | None,
    turno: Turno | None,
    modo_manual: bool = False,
    sin_confirmar: bool = False,
) -> bool:
    """RN-60. Recepción y Administrador liberan un 'pendiente' en modo manual o con marca 'sin confirmar'."""
    if usuario is None or turno is None:
        return False

    if usuario.rol not in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
        return False

    if turno.estado != EstadoTurno.PENDIENTE:
        return False

    return modo_manual or sin_confirmar
