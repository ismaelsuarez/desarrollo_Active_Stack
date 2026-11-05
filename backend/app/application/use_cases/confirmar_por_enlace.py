"""La posesión del enlace autoriza únicamente confirmar su turno y ciclo."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.errors_turnos import RechazoDeTurno
from app.domain.ports.reloj import Reloj
from app.domain.services.auth_crypto import calcular_token_hash
from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.confirmacion_turno import RepositorioConfirmacionTurnoSQL


@dataclass(frozen=True)
class ResultadoConfirmacion:
    turno_id: int
    estado: str = "confirmado"


class ConfirmarTurnoPorEnlace:
    def __init__(self, sesiones: async_sessionmaker[AsyncSession], reloj: Reloj) -> None:
        self._sesiones = sesiones
        self._reloj = reloj

    async def ejecutar(self, raw: str) -> ResultadoConfirmacion:
        async with self._sesiones() as sesion, sesion.begin():
            repositorio = RepositorioConfirmacionTurnoSQL(sesion)
            token, turno = await repositorio.obtener(calcular_token_hash(raw))
            ahora = self._reloj.ahora()
            if (token is None or turno is None or token.usado_en is not None
                    or token.expira_en <= ahora or token.ciclo != turno.ciclo_confirmacion):
                raise RechazoDeTurno(400, "Enlace inválido o vencido")
            if turno.estado != EstadoTurno.PENDIENTE:
                mensaje = "El turno ya fue liberado; debés reservar de nuevo" if turno.estado == EstadoTurno.LIBERADO else "El turno no puede confirmarse en su estado actual"
                raise RechazoDeTurno(409, mensaje)
            await repositorio.confirmar(token, turno, ahora)
            return ResultadoConfirmacion(turno.id)
