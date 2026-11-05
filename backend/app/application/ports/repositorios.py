from typing import Protocol
from datetime import datetime, time

from app.application.dto.agenda import FichaAgenda, ParametrosAgenda
from app.domain.entities.historial import HechoDeTurno
from app.domain.entities.prestacion import Prestacion
from app.domain.entities.profesional import Profesional
from app.domain.entities.turno import NuevoTurno, Turno


class RepositorioProfesionales(Protocol):
    async def obtener(
        self, consultorio_id: int, profesional_id: int, *, incluir_inactivos: bool = False
    ) -> Profesional | None:
        """Busca en el consultorio; solo las lecturas históricas incluyen inactivos."""
        ...


class RepositorioPrestaciones(Protocol):
    async def obtener(
        self, consultorio_id: int, prestacion_id: int, *, incluir_inactivos: bool = False
    ) -> Prestacion | None:
        """Busca en el consultorio; solo las lecturas históricas incluyen inactivas."""
        ...


class RepositorioTurnos(Protocol):
    async def contar_futuros_activos(self, consultorio_id: int, paciente_id: int, ahora: datetime) -> int: ...

    async def guardar(self, turno: NuevoTurno) -> Turno:
        """Guarda el turno; lanza HorarioOcupado si se superpone con otro activo."""
        ...

    async def obtener(self, consultorio_id: int, turno_id: int) -> Turno | None: ...

    async def listar(
        self, consultorio_id: int, profesional_id: int | None = None,
        paciente_id: int | None = None, desde: datetime | None = None,
        hasta: datetime | None = None, sin_confirmar: bool = False,
    ) -> list[Turno]: ...

    async def hay_solapamiento(
        self, consultorio_id: int, profesional_id: int, inicio: datetime,
        fin: datetime, excluir_id: int | None = None,
    ) -> bool: ...

    async def actualizar(self, original: Turno, cambios: dict[str, object]) -> Turno: ...


class RepositorioHistorial(Protocol):
    async def agregar(self, hecho: HechoDeTurno) -> None: ...

    async def listar(self, consultorio_id: int, turno_id: int) -> list[HechoDeTurno]: ...


class RepositorioAgendaTurnos(Protocol):
    async def ocupacion(self, consultorio_id: int, profesional_id: int,
                        desde: datetime, hasta: datetime) -> list[Turno]: ...

    async def obtener_configuracion(self, consultorio_id: int) -> ParametrosAgenda | None: ...

    async def obtener_paciente(self, consultorio_id: int, paciente_id: int) -> FichaAgenda | None: ...

    async def profesional_vinculado(self, consultorio_id: int, usuario_id: int, *,
                                   incluir_inactivos: bool = False) -> int | None: ...

    async def bloques(self, consultorio_id: int, profesional_id: int, dia: int) -> list[tuple[time, time]]: ...

    async def bloqueos(self, consultorio_id: int, profesional_id: int, *,
                       desde: datetime | None = None, hasta: datetime | None = None) -> list[tuple[datetime, datetime]]: ...

    async def pacientes_de_profesional(self, consultorio_id: int, profesional_id: int) -> frozenset[int]: ...
