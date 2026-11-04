from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.historial import HechoDeTurno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.models import TurnoHistorialModel


class RepositorioHistorialSQL:
    """Bitácora append-only: sólo inserción y lectura acotada (RN-21)."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def agregar(self, hecho: HechoDeTurno) -> None:
        self._sesion.add(TurnoHistorialModel(
            consultorio_id=hecho.consultorio_id, turno_id=hecho.turno_id,
            usuario_id=hecho.usuario_id, accion=hecho.accion,
            estado_anterior=hecho.estado_anterior.value if hecho.estado_anterior else None,
            estado_nuevo=hecho.estado_nuevo.value, detalle=hecho.detalle,
            ocurrido_en=hecho.ocurrido_en,
        ))
        await self._sesion.flush()

    async def listar(self, consultorio_id: int, turno_id: int) -> list[HechoDeTurno]:
        filas = await self._sesion.scalars(select(TurnoHistorialModel).where(
            TurnoHistorialModel.consultorio_id == consultorio_id,
            TurnoHistorialModel.turno_id == turno_id,
        ).order_by(TurnoHistorialModel.ocurrido_en, TurnoHistorialModel.id))
        return [HechoDeTurno(
            id=f.id, consultorio_id=f.consultorio_id, turno_id=f.turno_id,
            usuario_id=f.usuario_id, accion=f.accion,
            estado_anterior=EstadoTurno(f.estado_anterior) if f.estado_anterior else None,
            estado_nuevo=EstadoTurno(f.estado_nuevo), detalle=f.detalle,
            ocurrido_en=f.ocurrido_en,
        ) for f in filas]
