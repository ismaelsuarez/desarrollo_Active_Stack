"""Despacho durable de correo con reclamación por fila (RN-61)."""
from datetime import datetime, time, timedelta
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.ports.correo import EnviadorCorreo
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.account_models import NotificacionModel, TIPOS_CUENTA
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel

logger = logging.getLogger(__name__)


class DespacharNotificacion:
    """Una sesión por transacción; el transporte se ejecuta entre ambas."""

    def __init__(self, sesiones: async_sessionmaker[AsyncSession], reloj: Reloj,
                 enviador: EnviadorCorreo, settings: Settings):
        self.sesiones = sesiones
        self.reloj = reloj
        self.enviador = enviador
        self.settings = settings

    async def ejecutar(self, consultorio_id: int, notificacion_id: int) -> bool:
        ahora = self.reloj.ahora()
        vencida_antes = ahora - timedelta(seconds=self.settings.notification_claim_ttl_seconds)
        async with self.sesiones() as session, session.begin():
            row = await session.scalar(select(NotificacionModel).where(
                NotificacionModel.id == notificacion_id,
                NotificacionModel.consultorio_id == consultorio_id,
                NotificacionModel.canal == 'email',
                or_(NotificacionModel.estado == 'programada', and_(
                    NotificacionModel.estado == 'enviando',
                    NotificacionModel.reclamada_en < vencida_antes)),
                NotificacionModel.programada_para <= ahora,
            ).with_for_update(skip_locked=True))
            if row is None:
                return False
            if row.tipo == 'vinculacion_rechazada':
                verified = await session.scalar(select(UsuarioModel.email_verificado).where(
                    UsuarioModel.id == row.usuario_id,
                    UsuarioModel.consultorio_id == consultorio_id,
                ))
                if not verified:
                    await self._cerrar_sin_envio(session, row, 'omitida')
                    return False
            if row.intentos >= self.settings.notification_max_attempts:
                await self._cerrar_sin_envio(session, row, 'fallida')
                return False
            consultorio = await session.get(ConsultorioModel, consultorio_id)
            zona = ZoneInfo(consultorio.zona_horaria)
            fecha = ahora.astimezone(zona).date()
            inicio_dia = datetime.combine(fecha, time.min, zona)
            fin_dia = inicio_dia + timedelta(days=1)
            uso = select(func.count(NotificacionModel.id)).where(
                NotificacionModel.consultorio_id == consultorio_id,
                NotificacionModel.canal == 'email',
                or_(and_(NotificacionModel.estado == 'enviada',
                         NotificacionModel.enviada_en >= inicio_dia,
                         NotificacionModel.enviada_en < fin_dia),
                    and_(NotificacionModel.estado == 'enviando',
                         NotificacionModel.reclamada_en >= vencida_antes)),
            )
            total = await session.scalar(uso)
            if total >= self.settings.email_daily_limit:
                return False
            if row.tipo in TIPOS_CUENTA:
                cuentas = await session.scalar(uso.where(NotificacionModel.tipo.in_(TIPOS_CUENTA)))
                if cuentas >= self.settings.email_daily_limit_account:
                    return False
            if total + 1 >= self.settings.email_daily_limit * self.settings.email_daily_alert_ratio:
                logger.warning('cupo_correo_alerta', extra={'consultorio_id': consultorio_id})
            row.estado = 'enviando'
            row.reclamada_en = ahora
            row.intentos += 1
            destinatario, cuerpo = row.destinatario, row.mensaje or ''
            intentos = row.intentos

        error = None
        try:
            await self.enviador.enviar(destinatario, 'Notificación del consultorio', cuerpo)
        except Exception as exc:
            # Provider messages can include credentials or personal addresses.
            error = type(exc).__name__

        estado = 'enviada' if error is None else (
            'fallida' if intentos >= self.settings.notification_max_attempts else 'programada')

        async with self.sesiones() as session, session.begin():
            result = await session.execute(update(NotificacionModel).where(
                NotificacionModel.id == notificacion_id,
                NotificacionModel.consultorio_id == consultorio_id,
                NotificacionModel.estado == 'enviando',
                NotificacionModel.reclamada_en == ahora,
            ).values(estado=estado,
                     enviada_en=self.reloj.ahora() if error is None else None,
                     reclamada_en=None, ultimo_error=error))
            if result.rowcount != 1:
                logger.warning('reclamacion_perdida')
                return False
            return error is None

    @staticmethod
    async def _cerrar_sin_envio(session: AsyncSession, row: NotificacionModel,
                               estado: str) -> None:
        # The row lock orders reclamation; the predicate also preserves the
        # ownership contract explicitly for stale claims resolved without SMTP.
        await session.execute(update(NotificacionModel).where(
            NotificacionModel.id == row.id,
            NotificacionModel.consultorio_id == row.consultorio_id,
            NotificacionModel.estado == row.estado,
            NotificacionModel.reclamada_en == row.reclamada_en,
        ).values(estado=estado, reclamada_en=None))
