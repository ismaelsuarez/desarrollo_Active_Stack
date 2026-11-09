from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import AutorizacionSobreturnoModel


class RepositorioSobreturnosSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_varios(self, consultorio_id: int, turno_ids: set[int]) -> dict[int, AutorizacionSobreturnoModel]:
        filas = await self._sesion.scalars(select(AutorizacionSobreturnoModel).where(
            AutorizacionSobreturnoModel.consultorio_id == consultorio_id,
            AutorizacionSobreturnoModel.turno_id.in_(turno_ids)))
        return {fila.turno_id: fila for fila in filas}

    async def agregar(self, consultorio_id, turno_id, usuario_id, ahora, motivo) -> None:
        self._sesion.add(AutorizacionSobreturnoModel(
            consultorio_id=consultorio_id, turno_id=turno_id,
            autorizado_por_id=usuario_id, autorizado_en=ahora,
            avisado_en=ahora, motivo=motivo,
        ))
        await self._sesion.flush()

    async def obtener(self, consultorio_id: int, turno_id: int) -> AutorizacionSobreturnoModel | None:
        return await self._sesion.scalar(select(AutorizacionSobreturnoModel).where(
            AutorizacionSobreturnoModel.consultorio_id == consultorio_id,
            AutorizacionSobreturnoModel.turno_id == turno_id,
        ))

    async def responder(self, autorizacion, respuesta, usuario_id, ahora, comentario):
        autorizacion.respuesta = respuesta
        autorizacion.respondido_por_id = usuario_id
        autorizacion.respondido_en = ahora
        autorizacion.comentario = comentario
        await self._sesion.flush()
