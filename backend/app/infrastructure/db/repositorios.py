from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.prestacion import Prestacion
from app.domain.entities.profesional import Profesional
from app.domain.entities.turno import NuevoTurno, Turno
from app.domain.errors import HorarioOcupado
from app.infrastructure.db.models import (
    RESTRICCION_SIN_SOLAPAMIENTO,
    PrestacionModel,
    ProfesionalModel,
    TurnoModel,
)

# SQLSTATE de PostgreSQL para la violación de una restricción de exclusión.
VIOLACION_DE_EXCLUSION = "23P01"


def es_solapamiento_de_turnos(error: IntegrityError) -> bool:
    """Distingue el solapamiento de turnos de cualquier otro error de integridad."""
    original = error.orig
    if getattr(original, "sqlstate", None) != VIOLACION_DE_EXCLUSION:
        return False
    restriccion = getattr(original.__cause__, "constraint_name", None)
    return restriccion == RESTRICCION_SIN_SOLAPAMIENTO


class RepositorioProfesionalesSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener(
        self, consultorio_id: int, profesional_id: int
    ) -> Profesional | None:
        modelo = await self._sesion.scalar(
            select(ProfesionalModel).where(
                ProfesionalModel.id == profesional_id,
                ProfesionalModel.consultorio_id == consultorio_id,
            )
        )
        if modelo is None:
            return None
        return Profesional(
            id=modelo.id,
            consultorio_id=modelo.consultorio_id,
            box_id=modelo.box_id,
            nombre=modelo.nombre,
            apellido=modelo.apellido,
        )


class RepositorioPrestacionesSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def obtener(
        self, consultorio_id: int, prestacion_id: int
    ) -> Prestacion | None:
        modelo = await self._sesion.scalar(
            select(PrestacionModel).where(
                PrestacionModel.id == prestacion_id,
                PrestacionModel.consultorio_id == consultorio_id,
            )
        )
        if modelo is None:
            return None
        return Prestacion(
            id=modelo.id,
            consultorio_id=modelo.consultorio_id,
            nombre=modelo.nombre,
            duracion_min=modelo.duracion_min,
        )


class RepositorioTurnosSQL:
    def __init__(self, sesion: AsyncSession) -> None:
        self._sesion = sesion

    async def guardar(self, turno: NuevoTurno) -> Turno:
        modelo = TurnoModel(
            consultorio_id=turno.consultorio_id,
            paciente_id=turno.paciente_id,
            profesional_id=turno.profesional_id,
            box_id=turno.box_id,
            prestacion_id=turno.prestacion_id,
            inicio=turno.inicio,
            fin=turno.fin,
        )
        self._sesion.add(modelo)
        try:
            await self._sesion.flush()
        except IntegrityError as error:
            if es_solapamiento_de_turnos(error):
                raise HorarioOcupado() from error
            raise
        await self._sesion.refresh(modelo)
        return Turno(
            id=modelo.id,
            consultorio_id=modelo.consultorio_id,
            paciente_id=modelo.paciente_id,
            profesional_id=modelo.profesional_id,
            box_id=modelo.box_id,
            prestacion_id=modelo.prestacion_id,
            inicio=modelo.inicio,
            fin=modelo.fin,
            estado=modelo.estado,
            es_sobreturno=modelo.es_sobreturno,
        )
