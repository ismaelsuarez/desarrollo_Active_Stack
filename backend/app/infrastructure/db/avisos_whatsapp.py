"""Persistencia transaccional de trabajos WhatsApp con snapshot del hecho."""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.turno import Turno
from app.domain.services.mensaje_whatsapp import construir_mensaje_whatsapp
from app.domain.value_objects.telefono import normalizar_telefono
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import ConsultorioModel, PacienteModel, ProfesionalModel


class RepositorioAvisosWhatsAppSQL:
    def __init__(self, sesion: AsyncSession):
        self.sesion = sesion

    async def programar_hito(self, turno: Turno, tipo: str, para: datetime) -> int | None:
        paciente = await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.id == turno.paciente_id,
            PacienteModel.consultorio_id == turno.consultorio_id,
        ))
        telefono = normalizar_telefono(paciente.telefono) if paciente else None
        if telefono is None:
            return None
        return await self.sesion.scalar(insert(NotificacionModel).values(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            tipo=tipo, canal='whatsapp', ciclo=turno.ciclo_confirmacion,
            estado='programada', destinatario=telefono,
            programada_para=para, intentos=0,
        ).on_conflict_do_nothing(
            constraint='uq_notificacion_turno_tipo_canal_ciclo'
        ).returning(NotificacionModel.id))

    async def programar_hecho(self, turno: Turno, tipo: str, ahora: datetime) -> int | None:
        paciente = await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.id == turno.paciente_id,
            PacienteModel.consultorio_id == turno.consultorio_id,
        ))
        telefono = normalizar_telefono(paciente.telefono) if paciente else None
        if telefono is None:
            return None
        profesional = await self.sesion.scalar(select(ProfesionalModel).where(
            ProfesionalModel.id == turno.profesional_id,
            ProfesionalModel.consultorio_id == turno.consultorio_id,
        ))
        consultorio = await self.sesion.get(ConsultorioModel, turno.consultorio_id)
        mensaje, enlace = construir_mensaje_whatsapp(
            telefono=telefono, paciente=f'{paciente.nombre} {paciente.apellido}',
            profesional=f'{profesional.nombre} {profesional.apellido}',
            consultorio=consultorio.nombre, fecha_hora=turno.inicio,
            zona_horaria=consultorio.zona_horaria, accion=tipo,
        )
        return await self.sesion.scalar(insert(NotificacionModel).values(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            tipo=tipo, canal='whatsapp', ciclo=turno.ciclo_confirmacion,
            estado='programada', destinatario=telefono, mensaje=mensaje,
            enlace_whatsapp=enlace, programada_para=ahora, intentos=0,
        ).on_conflict_do_nothing(
            constraint='uq_notificacion_turno_tipo_canal_ciclo'
        ).returning(NotificacionModel.id))
