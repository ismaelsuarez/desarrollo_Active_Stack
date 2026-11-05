"""Barrido acotado dentro de la API; la reclamación pertenece al despacho."""
from dataclasses import asdict, dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.db.account_models import BarridoEstadoModel, NotificacionModel, TIPOS_CUENTA
from app.application.services.limpieza_barrido import LimpiarBarrido
from app.application.use_cases.evaluar_hitos_turnos import EvaluarHitosTurnos


@dataclass
class ResumenBarrido:
    ejecucion_id: UUID
    reclamadas: int = 0
    enviadas: int = 0
    reintentadas: int = 0
    omitidas: int = 0
    fallidas: int = 0


class EjecutarBarrido:
    def __init__(self, sesiones, reloj, despacho, settings):
        self.sesiones = sesiones
        self.reloj = reloj
        self.despacho = despacho
        self.settings = settings
        self.limpieza = LimpiarBarrido(sesiones, reloj)
        self.evaluacion = EvaluarHitosTurnos(sesiones, reloj)

    async def seleccionar_candidatos(self, consultorio_id: int) -> list[int]:
        ids = []
        now = self.reloj.ahora()
        async with self.sesiones() as session:
            for estado in ('programada', 'enviando'):
                for cuenta in (True, False):
                    query = select(NotificacionModel.id).where(
                        NotificacionModel.consultorio_id == consultorio_id,
                        NotificacionModel.estado == estado,
                        NotificacionModel.canal == 'email',
                        NotificacionModel.programada_para <= now,
                        NotificacionModel.tipo.in_(TIPOS_CUENTA) if cuenta else NotificacionModel.tipo.not_in(TIPOS_CUENTA),
                    )
                    if estado == 'enviando':
                        query = query.where(NotificacionModel.reclamada_en < now-timedelta(seconds=self.settings.notification_claim_ttl_seconds))
                    ids.extend((await session.scalars(query.order_by(
                        NotificacionModel.reclamada_en if estado == 'enviando' else NotificacionModel.programada_para,
                        NotificacionModel.id).limit(100))).all())
        return list(dict.fromkeys(ids))

    async def ejecutar(self, consultorio_id: int) -> ResumenBarrido:
        result = ResumenBarrido(uuid4())
        await self._iniciar(consultorio_id, result)
        try:
            await self.limpieza.ejecutar(consultorio_id)
            await self.evaluacion.ejecutar(consultorio_id)
            ids = await self.seleccionar_candidatos(consultorio_id)
            for identifier in ids:
                item = await self.despacho.ejecutar_detallado(consultorio_id, identifier)
                result.reclamadas += int(item.reclamada)
                field = {'enviada':'enviadas','programada':'reintentadas','omitida':'omitidas','fallida':'fallidas'}.get(item.estado)
                if field:
                    setattr(result, field, getattr(result, field)+1)
        except Exception:
            await self._finalizar(consultorio_id, result, 'error')
            raise
        await self._finalizar(consultorio_id, result, 'exitoso')
        return result

    async def _iniciar(self, consultorio_id, result):
        values = dict(consultorio_id=consultorio_id, **asdict(result),
                      iniciado_en=self.reloj.ahora(), finalizado_en=None, estado='en_curso')
        statement = insert(BarridoEstadoModel).values(**values)
        async with self.sesiones() as session, session.begin():
            await session.execute(statement.on_conflict_do_update(
                index_elements=['consultorio_id'],
                set_={key:value for key,value in values.items() if key!='consultorio_id'},
                where=BarridoEstadoModel.iniciado_en <= statement.excluded.iniciado_en,
            ))

    async def _finalizar(self, consultorio_id, result, estado):
        async with self.sesiones() as session, session.begin():
            await session.execute(update(BarridoEstadoModel).where(
                BarridoEstadoModel.consultorio_id==consultorio_id,
                BarridoEstadoModel.ejecucion_id==result.ejecucion_id,
            ).values(**asdict(result), estado=estado, finalizado_en=self.reloj.ahora()))
