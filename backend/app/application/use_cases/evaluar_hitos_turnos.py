"""Decisiones RN-60 acotadas; la actualización condicional es el reclamo."""
from datetime import timedelta

from sqlalchemy import select, update

from app.domain.policies.decision_hitos import decidir_sin_confirmar
from app.infrastructure.db.models import ConsultorioModel, TurnoModel, TurnoHistorialModel
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
from app.infrastructure.db.repositorios import RepositorioTurnosSQL


class EvaluarHitosTurnos:
    def __init__(self, sesiones, reloj):
        self.sesiones, self.reloj = sesiones, reloj

    async def seleccionar_candidatos(self, consultorio_id: int) -> list[tuple[int,int]]:
        ahora = self.reloj.ahora()
        async with self.sesiones() as session:
            config = await session.get(ConsultorioModel, consultorio_id)
            if config is None:
                return []
            rows = await session.execute(select(TurnoModel.id,TurnoModel.ciclo_confirmacion).where(
                TurnoModel.consultorio_id==consultorio_id, TurnoModel.estado=='pendiente',
                TurnoModel.marcado_sin_confirmar_en.is_(None), TurnoModel.inicio>ahora,
                TurnoModel.inicio<=ahora+timedelta(hours=config.horas_liberacion),
            ).order_by(TurnoModel.inicio,TurnoModel.id).limit(100))
            return [(row.id,row.ciclo_confirmacion) for row in rows]

    async def ejecutar(self, consultorio_id: int) -> None:
        for turno_id,ciclo in await self.seleccionar_candidatos(consultorio_id):
            await self.evaluar(consultorio_id,turno_id,ciclo)

    async def evaluar(self, consultorio_id: int, turno_id: int, ciclo: int) -> bool:
        async with self.sesiones() as session, session.begin():
            config = await session.get(ConsultorioModel,consultorio_id)
            turno = await session.scalar(select(TurnoModel).where(
                TurnoModel.id==turno_id,TurnoModel.consultorio_id==consultorio_id))
            if config is None or turno is None or turno.ciclo_confirmacion != ciclo:
                return False
            enviada = select(NotificacionModel.id).where(
                NotificacionModel.consultorio_id==consultorio_id,
                NotificacionModel.turno_id==turno_id,NotificacionModel.ciclo==ciclo,
                NotificacionModel.tipo=='solicitud_confirmacion',
                NotificacionModel.canal=='email',NotificacionModel.estado=='enviada').exists()
            solicitud_enviada = await session.scalar(select(enviada))
            ahora = self.reloj.ahora()
            accion = decidir_sin_confirmar(estado=turno.estado,inicio=turno.inicio,
                ahora=ahora,marca=turno.marcado_sin_confirmar_en,modo=config.modo_liberacion,
                solicitud_enviada=solicitud_enviada,horas_liberacion=config.horas_liberacion)
            if accion is None:
                return False
            statement = update(TurnoModel).where(
                TurnoModel.consultorio_id==consultorio_id,TurnoModel.id==turno_id,
                TurnoModel.estado=='pendiente',TurnoModel.marcado_sin_confirmar_en.is_(None),
                TurnoModel.ciclo_confirmacion==ciclo,TurnoModel.inicio>ahora,
                TurnoModel.inicio<=ahora+timedelta(hours=config.horas_liberacion),
            )
            if accion == 'liberar':
                statement=statement.where(enviada).values(estado='liberado',liberado_en=ahora,actualizado_en=ahora)
            else:
                statement=statement.values(marcado_sin_confirmar_en=ahora,actualizado_en=ahora)
            statement=statement.returning(TurnoModel)
            actualizado = await session.scalar(statement)
            if actualizado is None:
                return False
            session.add(TurnoHistorialModel(consultorio_id=consultorio_id,turno_id=turno_id,
                usuario_id=None,accion=accion,estado_anterior='pendiente',estado_nuevo=actualizado.estado,
                ocurrido_en=ahora))
            if accion == 'liberar':
                avisos=RepositorioAvisosDeTurnoSQL(session)
                entidad=RepositorioTurnosSQL._entidad(actualizado)
                await avisos.omitir_hitos(entidad,ciclo)
                await avisos.programar_aviso_liberacion(entidad,ahora)
            return True
