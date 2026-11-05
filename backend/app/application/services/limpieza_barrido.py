"""Retención periódica; cada clase de limpieza usa una transacción corta."""
from sqlalchemy import delete, select, update

from app.application.services.rate_limiter import PurgarIntentosIngreso
from app.infrastructure.db.limites_cuenta import PurgarIntentosRegistro
from app.infrastructure.db.models import TokenUsuarioModel, RefreshTokenModel


class LimpiarBarrido:
    def __init__(self, sesiones, reloj):
        self.sesiones, self.reloj = sesiones, reloj

    async def ejecutar(self, consultorio_id: int) -> None:
        now = self.reloj.ahora()
        async with self.sesiones() as session, session.begin():
            await session.execute(delete(TokenUsuarioModel).where(
                TokenUsuarioModel.consultorio_id==consultorio_id, TokenUsuarioModel.expira_en<=now))
        async with self.sesiones() as session, session.begin():
            expired = select(RefreshTokenModel.id).where(
                RefreshTokenModel.consultorio_id==consultorio_id, RefreshTokenModel.expira_en<=now)
            # La FK autorreferente no debe eliminar una credencial vigente.
            await session.execute(update(RefreshTokenModel).where(
                RefreshTokenModel.consultorio_id==consultorio_id,
                RefreshTokenModel.reemplazado_por_id.in_(expired)
            ).values(reemplazado_por_id=None))
            await session.execute(delete(RefreshTokenModel).where(
                RefreshTokenModel.consultorio_id==consultorio_id, RefreshTokenModel.expira_en<=now))
        for purge in (PurgarIntentosRegistro, PurgarIntentosIngreso):
            async with self.sesiones() as session, session.begin():
                await purge(session,self.reloj).ejecutar(consultorio_id)
