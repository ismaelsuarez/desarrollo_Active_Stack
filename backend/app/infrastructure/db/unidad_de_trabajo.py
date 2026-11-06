from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.exc import IntegrityError
from app.domain.errors import HorarioOcupado
from app.domain.ports.reloj import Reloj

from app.infrastructure.db.historial import RepositorioHistorialSQL
from app.infrastructure.db.agenda_turnos import RepositorioAgendaTurnosSQL
from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL
from app.infrastructure.db.cuentas import RepositorioCuentas
from app.infrastructure.db.pacientes import RepositorioPacientesSQL
from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
from app.infrastructure.db.sobreturnos import RepositorioSobreturnosSQL

from app.infrastructure.db.repositorios import (
    RepositorioPrestacionesSQL,
    RepositorioProfesionalesSQL,
    RepositorioTurnosSQL,
    es_solapamiento_de_turnos,
)


class UnidadDeTrabajoSQL:
    """Abre una sesión propia en cada uso: dos tareas nunca comparten sesión."""

    def __init__(self, sesiones: async_sessionmaker[AsyncSession], reloj: Reloj | None = None) -> None:
        self._sesiones = sesiones
        self._reloj = reloj

    async def __aenter__(self) -> Self:
        self._sesion = self._sesiones()
        self.profesionales = RepositorioProfesionalesSQL(self._sesion)
        self.prestaciones = RepositorioPrestacionesSQL(self._sesion)
        self.turnos = RepositorioTurnosSQL(self._sesion, self._reloj)
        self.historial = RepositorioHistorialSQL(self._sesion)
        self.agenda = RepositorioAgendaTurnosSQL(self._sesion)
        self.vinculos = RepositorioVinculacionSQL(self._sesion)
        self.cuentas = RepositorioCuentas(self._sesion)
        self.pacientes = RepositorioPacientesSQL(self._sesion)
        self.notificaciones = RepositorioAvisosDeTurnoSQL(self._sesion)
        self.sobreturnos = RepositorioSobreturnosSQL(self._sesion)
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        try:
            if error is None:
                try:
                    await self._sesion.commit()
                except BaseException as fallo:
                    await self._sesion.rollback()
                    if isinstance(fallo, IntegrityError) and es_solapamiento_de_turnos(fallo):
                        raise HorarioOcupado() from fallo
                    raise
            else:
                await self._sesion.rollback()
        finally:
            await self._sesion.close()
