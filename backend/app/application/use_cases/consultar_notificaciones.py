"""Lecturas operativas mínimas, restringidas por la política central."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, or_, select

from app.application.errors_turnos import RechazoDeTurno
from app.domain.entities.auth import Principal
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.infrastructure.db.account_models import BarridoEstadoModel, NotificacionModel
from app.infrastructure.db.models import ConsultorioModel


class ConsultarNotificaciones:
    def __init__(self, sesiones, reloj, settings):
        self.sesiones = sesiones
        self.reloj = reloj
        self.settings = settings

    @staticmethod
    def _autorizar(principal: Principal):
        decision = autorizar(principal, Accion.NOTIFICACION_GESTIONAR)
        if not decision.permitido:
            raise RechazoDeTurno(decision.codigo_http, decision.motivo)

    async def listar(self, principal: Principal, estado=None, limit=50, offset=0):
        self._autorizar(principal)
        columnas = (NotificacionModel.id, NotificacionModel.turno_id, NotificacionModel.tipo,
                    NotificacionModel.canal, NotificacionModel.estado, NotificacionModel.intentos,
                    NotificacionModel.programada_para, NotificacionModel.reclamada_en, NotificacionModel.enviada_en)
        query = select(*columnas).where(NotificacionModel.consultorio_id == principal.consultorio_id)
        if estado is not None:
            query = query.where(NotificacionModel.estado == estado)
        async with self.sesiones() as sesion:
            return (await sesion.execute(query.order_by(NotificacionModel.id.desc()).limit(limit).offset(offset))).mappings().all()

    async def indicadores(self, principal: Principal):
        self._autorizar(principal)
        ahora = self.reloj.ahora()
        cid = principal.consultorio_id
        async with self.sesiones() as sesion:
            consultorio = await sesion.get(ConsultorioModel, cid)
            zona = ZoneInfo(consultorio.zona_horaria)
            inicio = datetime.combine(ahora.astimezone(zona).date(), time.min, zona)
            ttl = ahora-timedelta(seconds=self.settings.notification_claim_ttl_seconds)
            n = NotificacionModel
            resultado = (await sesion.execute(select(
                func.count(n.id).filter(n.estado == "fallida").label("fallidas"),
                func.min(n.programada_para).filter(n.estado == "programada").label("programada"),
                func.count(n.id).filter(n.estado == "enviando").label("enviando"),
                func.min(n.reclamada_en).filter(n.estado == "enviando").label("reclamada"),
                func.count(n.id).filter(n.canal == "email", or_(
                    and_(n.estado == "enviada", n.enviada_en >= inicio, n.enviada_en < inicio+timedelta(days=1)),
                    and_(n.estado == "enviando", n.reclamada_en >= ttl),
                )).label("correos_del_dia"),
            ).where(n.consultorio_id == cid))).mappings().one()
            ultimo = await sesion.get(BarridoEstadoModel, cid)
            # Detach only the explicit operational fields; never serialize ORM
            # internals, exception text or personal notification payloads.
            estado = None if ultimo is None else {
                campo: getattr(ultimo, campo) for campo in (
                    "ejecucion_id", "iniciado_en", "finalizado_en", "estado",
                    "reclamadas", "enviadas", "reintentadas", "omitidas", "fallidas")}
        def antiguedad(instante):
            return None if instante is None else max(0.0, (ahora-instante).total_seconds())
        uso = resultado["correos_del_dia"]
        return {"fallidas": resultado["fallidas"],
                "programada_mas_antigua_segundos": antiguedad(resultado["programada"]),
                "enviando": resultado["enviando"],
                "enviando_mas_antigua_segundos": antiguedad(resultado["reclamada"]),
                "correos_del_dia": uso, "limite_diario": self.settings.email_daily_limit,
                "limite_cuenta": self.settings.email_daily_limit_account,
                "alerta": uso >= self.settings.email_daily_limit*self.settings.email_daily_alert_ratio,
                "ultimo_barrido": estado}
