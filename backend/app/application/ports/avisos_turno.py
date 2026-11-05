"""Avisos del personal, independientes de los hitos de confirmación."""
from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno

if TYPE_CHECKING:
    from app.application.ports.unidad_de_trabajo import UnidadDeTrabajo


class ProgramadorAvisosDeTurno(Protocol):
    async def programar(self, unidad: "UnidadDeTrabajo", principal: Principal,
                        turno: Turno, accion: str, ahora: datetime) -> None: ...


class ProgramadorAvisosStaff:
    async def programar(self, unidad: "UnidadDeTrabajo", principal: Principal,
                        turno: Turno, accion: str, ahora: datetime) -> None:
        if principal.rol in (RolUsuario.RECEPCION, RolUsuario.ADMINISTRADOR):
            await unidad.notificaciones.programar_aviso_personal(turno, accion, ahora)


class RepositorioAvisosDeTurno(Protocol):
    async def programar_aviso_personal(self, turno: Turno, accion: str, ahora: datetime) -> int | None: ...
