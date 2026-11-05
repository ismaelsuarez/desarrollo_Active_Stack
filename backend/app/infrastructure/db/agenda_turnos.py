from datetime import datetime, time
from dataclasses import fields

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.agenda import FichaAgenda, ParametrosAgenda
from app.domain.entities.turno import Turno
from app.infrastructure.db.models import (
    BloqueoAgendaModel, ConsultorioModel, HorarioSemanalModel, PacienteModel,
    ProfesionalModel, TurnoModel,
)


class RepositorioAgendaTurnosSQL:
    """Datos operativos mínimos para reservar y leer la agenda de un consultorio."""

    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener_configuracion(self, consultorio_id: int) -> ParametrosAgenda | None:
        modelo = await self._sesion.scalar(select(ConsultorioModel).where(
            ConsultorioModel.id == consultorio_id,
        ))
        if modelo is None:
            return None
        return ParametrosAgenda(
            id=modelo.id, consultorio_id=modelo.id, zona_horaria=modelo.zona_horaria,
            horas_confirmacion=modelo.horas_confirmacion,
            horas_recordatorio=modelo.horas_recordatorio,
            horas_liberacion=modelo.horas_liberacion,
            horas_limite_paciente=modelo.horas_limite_paciente,
            minutos_granularidad=modelo.minutos_granularidad,
            modo_liberacion=modelo.modo_liberacion,
            telefono=modelo.telefono,
            dias_anticipacion_maxima=modelo.dias_anticipacion_maxima,
            max_turnos_activos_paciente=modelo.max_turnos_activos_paciente,
        )

    async def obtener_paciente(self, consultorio_id: int, paciente_id: int) -> FichaAgenda | None:
        fila = (await self._sesion.execute(select(
            PacienteModel.id, PacienteModel.consultorio_id, PacienteModel.nombre, PacienteModel.apellido,
        ).where(PacienteModel.id == paciente_id, PacienteModel.consultorio_id == consultorio_id))).one_or_none()
        return FichaAgenda(*fila) if fila is not None else None

    async def profesional_vinculado(self, consultorio_id: int, usuario_id: int, *,
                                    incluir_inactivos: bool = False) -> int | None:
        consulta = select(ProfesionalModel.id).where(
            ProfesionalModel.consultorio_id == consultorio_id,
            ProfesionalModel.usuario_id == usuario_id,
        )
        if not incluir_inactivos:
            consulta = consulta.where(ProfesionalModel.activo.is_(True))
        return await self._sesion.scalar(consulta)

    async def bloques(self, consultorio_id: int, profesional_id: int, dia: int) -> list[tuple[time, time]]:
        filas = await self._sesion.execute(select(HorarioSemanalModel.hora_inicio, HorarioSemanalModel.hora_fin).where(
            HorarioSemanalModel.consultorio_id == consultorio_id,
            HorarioSemanalModel.profesional_id == profesional_id,
            HorarioSemanalModel.dia_semana == dia,
        ).order_by(HorarioSemanalModel.hora_inicio))
        return [(fila.hora_inicio, fila.hora_fin) for fila in filas]

    async def bloqueos(self, consultorio_id: int, profesional_id: int, *,
                       desde: datetime | None = None, hasta: datetime | None = None) -> list[tuple[datetime, datetime]]:
        consulta = select(BloqueoAgendaModel.inicio, BloqueoAgendaModel.fin).where(
            BloqueoAgendaModel.consultorio_id == consultorio_id,
            or_(BloqueoAgendaModel.profesional_id == profesional_id, BloqueoAgendaModel.profesional_id.is_(None)),
        )
        if desde is not None:
            consulta = consulta.where(BloqueoAgendaModel.fin > desde)
        if hasta is not None:
            consulta = consulta.where(BloqueoAgendaModel.inicio < hasta)
        filas = await self._sesion.execute(consulta.order_by(BloqueoAgendaModel.inicio, BloqueoAgendaModel.id))
        return [(fila.inicio, fila.fin) for fila in filas]

    async def pacientes_de_profesional(self, consultorio_id: int, profesional_id: int) -> frozenset[int]:
        pacientes = await self._sesion.scalars(select(TurnoModel.paciente_id).where(
            TurnoModel.consultorio_id == consultorio_id,
            TurnoModel.profesional_id == profesional_id,
        ).distinct())
        return frozenset(pacientes)

    async def ocupacion(self, consultorio_id: int, profesional_id: int,
                        desde: datetime, hasta: datetime) -> list[Turno]:
        filas = await self._sesion.scalars(select(TurnoModel).where(
            TurnoModel.consultorio_id == consultorio_id,
            TurnoModel.profesional_id == profesional_id,
            TurnoModel.inicio < hasta, TurnoModel.fin > desde,
        ).order_by(TurnoModel.inicio, TurnoModel.id))
        return [Turno(**{campo.name: getattr(fila, campo.name) for campo in fields(Turno)}) for fila in filas]
