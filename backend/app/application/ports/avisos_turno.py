"""Avisos de hechos consumados, independientes de los hitos de confirmación."""
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
        if accion == "crear":
            await unidad.notificaciones.programar_aviso_reserva(turno, ahora)
        elif accion == "liberar":
            await unidad.notificaciones.programar_aviso_liberacion(turno, ahora)
        elif accion == "cancelar" and principal.rol == RolUsuario.PACIENTE:
            await unidad.notificaciones.programar_aviso_cancelacion_paciente(turno, ahora)
        elif principal.rol in (RolUsuario.RECEPCION, RolUsuario.ADMINISTRADOR):
            await unidad.notificaciones.programar_aviso_personal(turno, accion, ahora)


class RepositorioAvisosDeTurno(Protocol):
    async def programar_aviso_liberacion(self, turno: Turno, ahora: datetime) -> int | None: ...

    async def programar_aviso_cancelacion_paciente(self, turno: Turno, ahora: datetime) -> int | None: ...

    async def programar_aviso_reserva(self, turno: Turno, ahora: datetime) -> int | None: ...

    async def omitir_hitos(self, turno: Turno, ciclo: int) -> None: ...

    async def programar_hito(self, turno: Turno, tipo: str, para: datetime) -> int | None: ...

    async def programar_aviso_personal(self, turno: Turno, accion: str, ahora: datetime) -> int | None: ...
