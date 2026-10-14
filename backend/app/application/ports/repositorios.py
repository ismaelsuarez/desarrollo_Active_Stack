from typing import Protocol

from app.domain.entities.prestacion import Prestacion
from app.domain.entities.profesional import Profesional
from app.domain.entities.turno import NuevoTurno, Turno


class RepositorioProfesionales(Protocol):
    async def obtener(
        self, consultorio_id: int, profesional_id: int
    ) -> Profesional | None:
        """Devuelve el profesional solo si pertenece al consultorio."""
        ...


class RepositorioPrestaciones(Protocol):
    async def obtener(
        self, consultorio_id: int, prestacion_id: int
    ) -> Prestacion | None:
        """Devuelve la prestación solo si pertenece al consultorio."""
        ...


class RepositorioTurnos(Protocol):
    async def guardar(self, turno: NuevoTurno) -> Turno:
        """Guarda el turno; lanza HorarioOcupado si se superpone con otro activo."""
        ...
