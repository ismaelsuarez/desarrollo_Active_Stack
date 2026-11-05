from collections.abc import Callable
from types import TracebackType
from typing import Protocol, Self
from app.application.ports.vinculacion import RepositorioVinculacion
from app.infrastructure.db.cuentas import RepositorioCuentas
from app.application.ports.pacientes import RepositorioPacientes
from app.application.ports.avisos_turno import RepositorioAvisosDeTurno

from app.application.ports.repositorios import (
    RepositorioPrestaciones,
    RepositorioProfesionales,
    RepositorioTurnos,
    RepositorioHistorial,
    RepositorioAgendaTurnos,
)


class UnidadDeTrabajo(Protocol):
    """Una transacción: confirma al salir sin error y revierte si hubo una excepción."""

    profesionales: RepositorioProfesionales
    prestaciones: RepositorioPrestaciones
    turnos: RepositorioTurnos
    historial: RepositorioHistorial
    agenda: RepositorioAgendaTurnos
    vinculos: RepositorioVinculacion
    cuentas: RepositorioCuentas
    pacientes: RepositorioPacientes
    notificaciones: RepositorioAvisosDeTurno

    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None: ...


FabricaDeUnidadesDeTrabajo = Callable[[], UnidadDeTrabajo]
