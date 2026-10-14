from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Prestacion:
    """Servicio del catálogo, con la duración que toman sus turnos (RN-13)."""

    id: int
    consultorio_id: int
    nombre: str
    duracion_min: int
