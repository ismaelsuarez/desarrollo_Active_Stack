from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.repositorios import (
    RepositorioPrestacionesSQL,
    RepositorioProfesionalesSQL,
    RepositorioTurnosSQL,
)


class UnidadDeTrabajoSQL:
    """Abre una sesión propia en cada uso: dos tareas nunca comparten sesión."""

    def __init__(self, sesiones: async_sessionmaker[AsyncSession]) -> None:
        self._sesiones = sesiones

    async def __aenter__(self) -> Self:
        self._sesion = self._sesiones()
        self.profesionales = RepositorioProfesionalesSQL(self._sesion)
        self.prestaciones = RepositorioPrestacionesSQL(self._sesion)
        self.turnos = RepositorioTurnosSQL(self._sesion)
        return self

    async def __aexit__(
        self,
        tipo: type[BaseException] | None,
        error: BaseException | None,
        traza: TracebackType | None,
    ) -> None:
        try:
            if error is None:
                await self._sesion.commit()
            else:
                await self._sesion.rollback()
        finally:
            await self._sesion.close()
