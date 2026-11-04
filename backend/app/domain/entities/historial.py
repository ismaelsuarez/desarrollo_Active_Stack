from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects.estado_turno import EstadoTurno


@dataclass(frozen=True, slots=True)
class HechoDeTurno:
    """Hecho inmutable de un turno; no contiene datos personales de la ficha."""

    consultorio_id: int
    turno_id: int
    usuario_id: int | None
    accion: str
    estado_anterior: EstadoTurno | None
    estado_nuevo: EstadoTurno
    detalle: dict[str, object] | None
    ocurrido_en: datetime
    id: int | None = None
