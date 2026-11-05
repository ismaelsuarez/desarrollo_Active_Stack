"""Programación transaccional de un hecho ya ocurrido; nunca hace commit ni SMTP."""
from datetime import datetime
import logging
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.turno import Turno
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import ConsultorioModel, PacienteModel, ProfesionalModel


class RepositorioAvisosDeTurnoSQL:
    def __init__(self, sesion: AsyncSession):
        self.sesion = sesion

    async def programar_aviso_reserva(self, turno: Turno, ahora: datetime) -> int | None:
        return await self._programar_hecho(turno, "resumen_reserva", "reservado", ahora)

    async def programar_aviso_cancelacion_paciente(self, turno: Turno, ahora: datetime) -> int | None:
        return await self._programar_hecho(turno, "cancelacion_por_paciente", "cancelado", ahora)

    async def programar_aviso_liberacion(self, turno: Turno, ahora: datetime) -> int | None:
        return await self._programar_hecho(turno, "liberacion", "liberado", ahora)

    async def _programar_hecho(self, turno: Turno, tipo: str, descripcion: str,
                              ahora: datetime, *,
                              evento_sin_contacto: str = "aviso_turno_sin_contacto") -> int | None:
        paciente = await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.id == turno.paciente_id, PacienteModel.consultorio_id == turno.consultorio_id))
        if paciente is None or not paciente.email or "@" not in paciente.email:
            logging.getLogger(__name__).info(evento_sin_contacto, extra={"turno_id": turno.id})
            return None
        profesional = await self.sesion.scalar(select(ProfesionalModel).where(
            ProfesionalModel.id == turno.profesional_id, ProfesionalModel.consultorio_id == turno.consultorio_id))
        consultorio = await self.sesion.get(ConsultorioModel, turno.consultorio_id)
        horario = turno.inicio.astimezone(ZoneInfo(consultorio.zona_horaria)).strftime("%d/%m/%Y %H:%M")
        mensaje = (f"Hola {paciente.nombre} {paciente.apellido}. Tu turno fue {descripcion}: {horario}. "
                   f"Profesional: {profesional.nombre} {profesional.apellido}. Consultorio: {consultorio.nombre}.")
        return await self.sesion.scalar(insert(NotificacionModel).values(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            tipo=tipo, canal="email", ciclo=turno.ciclo_confirmacion,
            estado="programada", destinatario=paciente.email, mensaje=mensaje,
            programada_para=ahora, intentos=0,
        ).on_conflict_do_nothing(constraint="uq_notificacion_turno_tipo_canal_ciclo").returning(NotificacionModel.id))

    async def omitir_hitos(self, turno: Turno, ciclo: int) -> None:
        await self.sesion.execute(update(NotificacionModel).where(
            NotificacionModel.consultorio_id == turno.consultorio_id,
            NotificacionModel.turno_id == turno.id, NotificacionModel.ciclo == ciclo,
            NotificacionModel.tipo.in_(("solicitud_confirmacion", "recordatorio")),
            NotificacionModel.estado.in_(("programada", "preparada")),
        ).values(estado="omitida", reclamada_en=None))

    async def programar_hito(self, turno: Turno, tipo: str, para: datetime) -> int | None:
        paciente = await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.id == turno.paciente_id, PacienteModel.consultorio_id == turno.consultorio_id))
        if paciente is None or not paciente.email or "@" not in paciente.email:
            logging.getLogger(__name__).info("hito_sin_contacto", extra={"turno_id": turno.id})
            return None
        return await self.sesion.scalar(insert(NotificacionModel).values(
            consultorio_id=turno.consultorio_id, turno_id=turno.id,
            tipo=tipo, canal="email", ciclo=turno.ciclo_confirmacion,
            estado="programada", destinatario=paciente.email,
            programada_para=para, intentos=0,
        ).on_conflict_do_nothing(constraint="uq_notificacion_turno_tipo_canal_ciclo").returning(NotificacionModel.id))

    async def programar_aviso_personal(self, turno: Turno, accion: str, ahora: datetime) -> int | None:
        return await self._programar_hecho(
            turno,
            "cancelacion_por_personal" if accion == "cancelar" else "reprogramacion_por_personal",
            "cancelado" if accion == "cancelar" else "reprogramado",
            ahora, evento_sin_contacto="aviso_personal_sin_contacto",
        )
