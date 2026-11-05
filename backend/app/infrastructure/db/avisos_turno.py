"""Programación transaccional de un hecho ya ocurrido; nunca hace commit ni SMTP."""
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.turno import Turno
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import ConsultorioModel, PacienteModel, ProfesionalModel


class RepositorioAvisosDeTurnoSQL:
    def __init__(self, sesion: AsyncSession):
        self.sesion = sesion

    async def programar_aviso_personal(self, turno: Turno, accion: str, ahora: datetime) -> int | None:
        paciente = await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.id == turno.paciente_id, PacienteModel.consultorio_id == turno.consultorio_id))
        if paciente is None or not paciente.email or "@" not in paciente.email:
            logging.getLogger(__name__).info("aviso_personal_sin_contacto", extra={"turno_id": turno.id})
            return None
        profesional = await self.sesion.scalar(select(ProfesionalModel).where(
            ProfesionalModel.id == turno.profesional_id, ProfesionalModel.consultorio_id == turno.consultorio_id))
        consultorio = await self.sesion.get(ConsultorioModel, turno.consultorio_id)
        horario = turno.inicio.astimezone(ZoneInfo(consultorio.zona_horaria)).strftime("%d/%m/%Y %H:%M")
        descripcion = "cancelado" if accion == "cancelar" else "reprogramado"
        mensaje = (f"Hola {paciente.nombre} {paciente.apellido}. Tu turno fue {descripcion}: {horario}. "
                   f"Profesional: {profesional.nombre} {profesional.apellido}. Consultorio: {consultorio.nombre}.")
        statement = insert(NotificacionModel).values(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            tipo="cancelacion_por_personal" if accion == "cancelar" else "reprogramacion_por_personal", canal="email", ciclo=turno.ciclo_confirmacion,
            estado="programada", destinatario=paciente.email, mensaje=mensaje,
            programada_para=ahora, intentos=0,
        ).on_conflict_do_nothing(constraint="uq_notificacion_turno_tipo_canal_ciclo").returning(NotificacionModel.id)
        return await self.sesion.scalar(statement)
