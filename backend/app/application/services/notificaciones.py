"""Despacho durable de correo con reclamación por fila (RN-61)."""
from datetime import datetime, time, timedelta
from dataclasses import dataclass
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.domain.ports.correo import EnviadorCorreo
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.account_models import NotificacionModel, TIPOS_CUENTA
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel, TurnoModel, PacienteModel, TokenUsuarioModel
from app.domain.services.auth_crypto import calcular_token_hash, generar_token_opaco

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoDespacho:
    reclamada: bool = False
    estado: str | None = None
    motivo: str = 'no_disponible'


class DespacharNotificacion:
    """Una sesión por transacción; el transporte se ejecuta entre ambas."""

    def __init__(self, sesiones: async_sessionmaker[AsyncSession], reloj: Reloj,
                 enviador: EnviadorCorreo, settings: Settings):
        self.sesiones = sesiones
        self.reloj = reloj
        self.enviador = enviador
        self.settings = settings

    async def ejecutar(self, consultorio_id: int, notificacion_id: int) -> bool:
        resultado = await self.ejecutar_detallado(consultorio_id, notificacion_id)
        return resultado.estado == 'enviada'

    async def ejecutar_detallado(self, consultorio_id: int, notificacion_id: int) -> ResultadoDespacho:
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
                return ResultadoDespacho()
            consultorio = await session.get(ConsultorioModel, consultorio_id)
            if row.tipo in ('solicitud_confirmacion', 'recordatorio'):
                estados = ('pendiente',) if row.tipo == 'solicitud_confirmacion' else ('pendiente', 'confirmado')
                turno = await session.scalar(select(TurnoModel).where(
                    TurnoModel.id == row.turno_id,
                    TurnoModel.consultorio_id == consultorio_id,
                    TurnoModel.estado.in_(estados),
                    TurnoModel.ciclo_confirmacion == row.ciclo,
                    TurnoModel.inicio > ahora,
                )) if row.ciclo is not None else None
                siguiente_hito = (consultorio.horas_recordatorio if row.tipo == 'solicitud_confirmacion'
                                  else consultorio.horas_liberacion)
                if turno is None or ahora >= turno.inicio - timedelta(hours=siguiente_hito):
                    await self._cerrar_sin_envio(session, row, 'omitida')
                    return ResultadoDespacho(estado='omitida', motivo='no_vigente')
            if row.tipo == 'vinculacion_rechazada':
                verified = await session.scalar(select(UsuarioModel.email_verificado).where(
                    UsuarioModel.id == row.usuario_id,
                    UsuarioModel.consultorio_id == consultorio_id,
                ))
                if not verified:
                    await self._cerrar_sin_envio(session, row, 'omitida')
                    return ResultadoDespacho(estado='omitida', motivo='no_vigente')
            if row.intentos >= self.settings.notification_max_attempts:
                await self._cerrar_sin_envio(session, row, 'fallida')
                return ResultadoDespacho(estado='fallida', motivo='intentos_agotados')
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
                return ResultadoDespacho(motivo='cupo_total')
            if row.tipo in TIPOS_CUENTA:
                cuentas = await session.scalar(uso.where(NotificacionModel.tipo.in_(TIPOS_CUENTA)))
                if cuentas >= self.settings.email_daily_limit_account:
                    return ResultadoDespacho(motivo='cupo_cuenta')
            if total + 1 >= self.settings.email_daily_limit * self.settings.email_daily_alert_ratio:
                logger.warning('cupo_correo_alerta', extra={'consultorio_id': consultorio_id})
            row.estado = 'enviando'
            row.reclamada_en = ahora
            row.intentos += 1
            destinatario, cuerpo = row.destinatario, row.mensaje or ''
            intentos = row.intentos
            if row.tipo == 'solicitud_confirmacion':
                paciente = await session.scalar(select(PacienteModel).where(
                    PacienteModel.id == turno.paciente_id,
                    PacienteModel.consultorio_id == consultorio_id))
                raw = generar_token_opaco()
                session.add(TokenUsuarioModel(consultorio_id=consultorio_id,
                    usuario_id=paciente.usuario_id, tipo='confirmar_turno',
                    token_hash=calcular_token_hash(raw), turno_id=turno.id,
                    ciclo=row.ciclo, creado_en=ahora, expira_en=turno.inicio))
                horario = turno.inicio.astimezone(zona).strftime('%d/%m/%Y %H:%M')
                enlace = f'{self.settings.frontend_base_url.rstrip("/")}/confirmar-turno#token={raw}'
                cuerpo = f'Tu turno es el {horario}. Confirmá tu asistencia: {enlace}'
            elif row.tipo == 'recordatorio':
                horario = turno.inicio.astimezone(zona).strftime('%d/%m/%Y %H:%M')
                cuerpo = f'Recordatorio de tu turno: {horario}.'
                if turno.estado == 'pendiente':
                    cuerpo += ' Confirmá tu asistencia.'
                    enviada = await session.scalar(select(NotificacionModel.id).where(
                        NotificacionModel.consultorio_id == consultorio_id,
                        NotificacionModel.turno_id == turno.id,
                        NotificacionModel.tipo == 'solicitud_confirmacion',
                        NotificacionModel.canal == 'email',
                        NotificacionModel.ciclo == turno.ciclo_confirmacion,
                        NotificacionModel.estado == 'enviada'))
                    if consultorio.modo_liberacion == 'automatico' and enviada is not None and turno.marcado_sin_confirmar_en is None:
                        cuerpo += f' Si no confirmás será liberado {consultorio.horas_liberacion} horas antes del inicio.'
            tipo, turno_id, ciclo = row.tipo, row.turno_id, row.ciclo

        error = None
        try:
            await self.enviador.enviar(destinatario, 'Notificación del consultorio', cuerpo)
        except Exception as exc:
            # Provider messages can include credentials or personal addresses.
            error = type(exc).__name__

        estado = 'enviada' if error is None else (
            'fallida' if intentos >= self.settings.notification_max_attempts else 'programada')

        async with self.sesiones() as session, session.begin():
            registrada_en = self.reloj.ahora()
            result = await session.execute(update(NotificacionModel).where(
                NotificacionModel.id == notificacion_id,
                NotificacionModel.consultorio_id == consultorio_id,
                NotificacionModel.estado == 'enviando',
                NotificacionModel.reclamada_en == ahora,
            ).values(estado=estado,
                     enviada_en=registrada_en if error is None else None,
                     reclamada_en=None, ultimo_error=error))
            if result.rowcount != 1:
                logger.warning('reclamacion_perdida')
                return ResultadoDespacho(True, motivo='reclamacion_perdida')
            if error is None and tipo in ('solicitud_confirmacion', 'recordatorio'):
                campo = 'confirmacion_solicitada_en' if tipo == 'solicitud_confirmacion' else 'recordatorio_enviado_en'
                await session.execute(update(TurnoModel).where(
                    TurnoModel.id == turno_id, TurnoModel.consultorio_id == consultorio_id,
                    TurnoModel.ciclo_confirmacion == ciclo,
                ).values(**{campo: registrada_en}))
            return ResultadoDespacho(True, estado, 'entregada' if error is None else 'error_transporte')

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
