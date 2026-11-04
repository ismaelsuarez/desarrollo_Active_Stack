"""Escrituras condicionales de vínculos, siempre dentro de la UoW del llamador."""
from datetime import datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, UsuarioModel


class RepositorioVinculacionSQL:
    def __init__(self, sesion: AsyncSession):
        self.sesion = sesion

    async def desvincular_ficha(self, consultorio_id: int, paciente_id: int,
                               usuario_id: int) -> bool:
        identificador = await self.sesion.scalar(update(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id,
            PacienteModel.id == paciente_id, PacienteModel.usuario_id == usuario_id,
        ).values(usuario_id=None).returning(PacienteModel.id))
        return identificador is not None

    async def registrar_desvinculacion(self, consultorio_id: int, usuario_id: int,
                                     paciente_id: int, dni: str, actor_id: int,
                                     ahora: datetime, motivo: str) -> bool:
        valores = dict(estado="rechazada", paciente_id=paciente_id,
                       motivo_rechazo=motivo, resuelta_por_id=actor_id, resuelta_en=ahora)
        sentencia = insert(SolicitudVinculacionModel).values(
            consultorio_id=consultorio_id, usuario_id=usuario_id,
            dni_declarado=dni, creada_en=ahora, **valores,
        ).on_conflict_do_update(index_elements=[SolicitudVinculacionModel.usuario_id],
            set_=valores, where=and_(
                SolicitudVinculacionModel.consultorio_id == consultorio_id,
                SolicitudVinculacionModel.estado == "vinculada",
            )).returning(SolicitudVinculacionModel.id)
        return await self.sesion.scalar(sentencia) is not None

    async def listar_solicitudes(self, consultorio_id: int, estado: str | None,
                                limit: int, offset: int):
        coincidente, vinculada = aliased(PacienteModel), aliased(PacienteModel)
        solicitud = SolicitudVinculacionModel
        consulta = select(solicitud, UsuarioModel, coincidente, vinculada).join(
            UsuarioModel, and_(UsuarioModel.id == solicitud.usuario_id,
                              UsuarioModel.consultorio_id == consultorio_id),
        ).outerjoin(coincidente, and_(
            coincidente.consultorio_id == consultorio_id,
            coincidente.dni == solicitud.dni_declarado,
        )).outerjoin(vinculada, and_(
            vinculada.consultorio_id == consultorio_id,
            vinculada.id == solicitud.paciente_id,
        )).where(solicitud.consultorio_id == consultorio_id)
        if estado is not None:
            consulta = consulta.where(solicitud.estado == estado)
        total = await self.sesion.scalar(select(func.count()).select_from(consulta.subquery()))
        filas = (await self.sesion.execute(consulta.order_by(
            solicitud.creada_en, solicitud.id).limit(limit).offset(offset))).all()
        return filas, total

    async def obtener_solicitud(self, consultorio_id: int, solicitud_id: int):
        return await self.sesion.scalar(select(SolicitudVinculacionModel).where(
            SolicitudVinculacionModel.consultorio_id == consultorio_id,
            SolicitudVinculacionModel.id == solicitud_id,
        ).execution_options(populate_existing=True))

    async def bloquear_ficha(self, consultorio_id: int, paciente_id: int):
        return await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id,
            PacienteModel.id == paciente_id,
        ).execution_options(populate_existing=True).with_for_update())

    async def vincular_solicitud(self, consultorio_id: int, solicitud_id: int,
                                estado_leido: str, paciente_id: int,
                                actor_id: int, ahora: datetime) -> bool:
        identificador = await self.sesion.scalar(update(SolicitudVinculacionModel).where(
            SolicitudVinculacionModel.consultorio_id == consultorio_id,
            SolicitudVinculacionModel.id == solicitud_id,
            SolicitudVinculacionModel.estado == estado_leido,
            SolicitudVinculacionModel.estado.in_(("pendiente", "rechazada")),
        ).values(estado="vinculada", paciente_id=paciente_id,
                 resuelta_por_id=actor_id, resuelta_en=ahora)
          .returning(SolicitudVinculacionModel.id))
        return identificador is not None

    async def vincular_ficha(self, consultorio_id: int, paciente_id: int,
                            usuario_id: int, ahora: datetime) -> bool:
        identificador = await self.sesion.scalar(update(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id,
            PacienteModel.id == paciente_id,
            PacienteModel.activo.is_(True),
            PacienteModel.usuario_id.is_(None),
        ).values(usuario_id=usuario_id, actualizado_en=ahora).returning(PacienteModel.id))
        return identificador is not None

    async def rechazar_solicitud(self, consultorio_id: int, solicitud_id: int,
                                estado_leido: str, actor_id: int, ahora: datetime,
                                motivo: str | None) -> bool:
        identificador = await self.sesion.scalar(update(SolicitudVinculacionModel).where(
            SolicitudVinculacionModel.consultorio_id == consultorio_id,
            SolicitudVinculacionModel.id == solicitud_id,
            SolicitudVinculacionModel.estado == estado_leido,
            SolicitudVinculacionModel.estado == "pendiente",
        ).values(estado="rechazada", motivo_rechazo=motivo,
                 resuelta_por_id=actor_id, resuelta_en=ahora)
          .returning(SolicitudVinculacionModel.id))
        return identificador is not None

    async def programar_rechazo(self, consultorio_id: int, usuario_id: int,
                               destinatario: str, cuerpo: str, ahora: datetime) -> int:
        fila = NotificacionModel(consultorio_id=consultorio_id, usuario_id=usuario_id,
                    turno_id=None, tipo="vinculacion_rechazada", canal="email",
                    estado="programada", destinatario=destinatario, mensaje=cuerpo,
                    programada_para=ahora, intentos=0)
        self.sesion.add(fila)
        await self.sesion.flush()
        return fila.id
