from dataclasses import dataclass
from enum import StrEnum


class RolUsuario(StrEnum):
    ADMINISTRADOR = "administrador"
    RECEPCION = "recepcion"
    PROFESIONAL = "profesional"
    PACIENTE = "paciente"
    ADMINISTRATIVO = "administrativo"


@dataclass(frozen=True, slots=True)
class Principal:
    """Identidad autenticada de un usuario dentro del contexto de un consultorio."""

    usuario_id: int
    consultorio_id: int
    rol: RolUsuario
