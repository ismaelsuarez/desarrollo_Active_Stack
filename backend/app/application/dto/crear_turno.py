from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class SolicitudDeTurno:
    """Datos para crear un turno. El fin no se indica: lo fija la prestación (RN-13)."""

    consultorio_id: int
    paciente_id: int
    profesional_id: int
    prestacion_id: int
    inicio: datetime
