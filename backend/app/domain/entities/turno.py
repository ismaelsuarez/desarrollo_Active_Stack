from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.errors import InicioSinZonaHoraria
from app.domain.value_objects.estado_turno import EstadoTurno


@dataclass(frozen=True, slots=True)
class Turno:
    """Reserva de un paciente con un profesional."""

    id: int
    consultorio_id: int
    paciente_id: int
    profesional_id: int
    box_id: int
    prestacion_id: int
    inicio: datetime
    fin: datetime
    estado: EstadoTurno
    es_sobreturno: bool


@dataclass(frozen=True, slots=True)
class NuevoTurno:
    """Turno todavía sin guardar: la base asigna el identificador y el estado inicial."""

    consultorio_id: int
    paciente_id: int
    profesional_id: int
    box_id: int
    prestacion_id: int
    inicio: datetime
    fin: datetime


def calcular_fin(inicio: datetime, duracion_min: int) -> datetime:
    """El fin de un turno es su inicio más la duración de la prestación (RN-13)."""
    return inicio + timedelta(minutes=duracion_min)


def exigir_zona_horaria(inicio: datetime) -> None:
    """Un inicio sin zona horaria dependería de la configuración del servidor."""
    if inicio.utcoffset() is None:
        raise InicioSinZonaHoraria()
