from enum import StrEnum


class EstadoTurno(StrEnum):
    """Estados de un turno (RN-18)."""

    PENDIENTE = "pendiente"
    CONFIRMADO = "confirmado"
    AUSENTE = "ausente"
    ATENDIDO = "atendido"
    CANCELADO = "cancelado"
    LIBERADO = "liberado"


# Los turnos cancelados y liberados no ocupan el horario (RN-17, RN-22).
ESTADOS_ACTIVOS = frozenset(
    {
        EstadoTurno.PENDIENTE,
        EstadoTurno.CONFIRMADO,
        EstadoTurno.ATENDIDO,
        EstadoTurno.AUSENTE,
    }
)
