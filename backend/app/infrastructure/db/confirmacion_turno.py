"""Persistencia transaccional de una confirmación por enlace."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.models import TokenUsuarioModel, TurnoHistorialModel, TurnoModel


class RepositorioConfirmacionTurnoSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def localizar(self, token_hash: str) -> TokenUsuarioModel | None:
        return await self._sesion.scalar(select(TokenUsuarioModel).where(
            TokenUsuarioModel.token_hash == token_hash,
            TokenUsuarioModel.tipo == "confirmar_turno",
        ))

    async def obtener(self, token_hash: str) -> tuple[TokenUsuarioModel | None, TurnoModel | None]:
        token = await self.localizar(token_hash)
        if token is None:
            return None, None
        turno = await self._sesion.scalar(select(TurnoModel).where(
            TurnoModel.id == token.turno_id,
            TurnoModel.consultorio_id == token.consultorio_id,
        ).with_for_update().execution_options(populate_existing=True))
        # El turno se bloquea antes que el token: dos enlaces del mismo turno
        # serializan sin invertir el orden de adquisición. Recargar es necesario
        # porque localizar pudo haber leído el token antes de esperar el bloqueo.
        token = await self._sesion.scalar(select(TokenUsuarioModel).where(
            TokenUsuarioModel.id == token.id,
            TokenUsuarioModel.consultorio_id == token.consultorio_id,
        ).with_for_update().execution_options(populate_existing=True))
        return token, turno

    async def confirmar(self, token: TokenUsuarioModel, turno: TurnoModel, ahora: datetime) -> None:
        turno.estado = EstadoTurno.CONFIRMADO
        turno.confirmado_en = ahora
        turno.actualizado_en = ahora
        token.usado_en = ahora
        self._sesion.add(TurnoHistorialModel(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            usuario_id=token.usuario_id, accion="confirmar", estado_anterior="pendiente",
            estado_nuevo="confirmado", ocurrido_en=ahora,
            detalle={"medio": "enlace", "actor": "paciente" if token.usuario_id is not None else "paciente_sin_cuenta"},
        ))
