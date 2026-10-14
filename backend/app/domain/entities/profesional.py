from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Profesional:
    """Profesional del consultorio, con su box fijo (RN-10)."""

    id: int
    consultorio_id: int
    box_id: int
    nombre: str
    apellido: str
