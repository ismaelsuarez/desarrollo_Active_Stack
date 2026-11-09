from dataclasses import fields
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.prestacion import Prestacion
from app.domain.entities.profesional import Profesional
from app.domain.entities.turno import NuevoTurno, Turno
from app.domain.errors import HorarioOcupado
from app.domain.errors_turnos import ConflictoDeTurno
from app.domain.ports.reloj import Reloj, RelojSistema
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
        self, consultorio_id: int, profesional_id: int, *, incluir_inactivos: bool = False
    ) -> Profesional | None:
        consulta = select(ProfesionalModel).where(
            ProfesionalModel.id == profesional_id,
            ProfesionalModel.consultorio_id == consultorio_id,
        )
        if not incluir_inactivos:
            consulta = consulta.where(ProfesionalModel.activo.is_(True))
        modelo = await self._sesion.scalar(consulta)
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

    async def obtener_varios(self, consultorio_id: int, ids: set[int]) -> dict[int, Prestacion]:
        modelos = await self._sesion.scalars(select(PrestacionModel).where(
            PrestacionModel.consultorio_id == consultorio_id, PrestacionModel.id.in_(ids)))
        return {modelo.id: Prestacion(id=modelo.id, consultorio_id=modelo.consultorio_id,
                                     nombre=modelo.nombre, duracion_min=modelo.duracion_min)
                for modelo in modelos}

    async def obtener(
        self, consultorio_id: int, prestacion_id: int, *, incluir_inactivos: bool = False
    ) -> Prestacion | None:
        consulta = select(PrestacionModel).where(
            PrestacionModel.id == prestacion_id,
            PrestacionModel.consultorio_id == consultorio_id,
        )
        if not incluir_inactivos:
            consulta = consulta.where(PrestacionModel.activa.is_(True))
        modelo = await self._sesion.scalar(consulta)
        if modelo is None:
            return None
        return Prestacion(
            id=modelo.id,
            consultorio_id=modelo.consultorio_id,
            nombre=modelo.nombre,
            duracion_min=modelo.duracion_min,
        )


class RepositorioTurnosSQL:
    def __init__(self, sesion: AsyncSession, reloj: Reloj | None = None) -> None:
        self._sesion = sesion
        self._reloj = reloj or RelojSistema()

    @staticmethod
    def _entidad(modelo: TurnoModel) -> Turno:
        return Turno(**{campo.name: getattr(modelo, campo.name) for campo in fields(Turno)})

    async def obtener(self, consultorio_id: int, turno_id: int) -> Turno | None:
        modelo = await self._sesion.scalar(select(TurnoModel).where(
            TurnoModel.id == turno_id, TurnoModel.consultorio_id == consultorio_id,
        ))
        return self._entidad(modelo) if modelo is not None else None

    async def contar_futuros_activos(self, consultorio_id: int, paciente_id: int, ahora: datetime) -> int:
        return await self._sesion.scalar(select(func.count()).select_from(TurnoModel).where(
            TurnoModel.consultorio_id == consultorio_id, TurnoModel.paciente_id == paciente_id,
            TurnoModel.inicio > ahora, TurnoModel.estado.in_(("pendiente", "confirmado")),
        ))

    async def listar(
        self, consultorio_id: int, profesional_id: int | None = None,
        paciente_id: int | None = None, desde: datetime | None = None,
        hasta: datetime | None = None, sin_confirmar: bool = False,
        limit: int | None = None, offset: int = 0,
    ) -> list[Turno]:
        consulta = select(TurnoModel).where(TurnoModel.consultorio_id == consultorio_id)
        if sin_confirmar:
            consulta = consulta.where(TurnoModel.estado == "pendiente", TurnoModel.marcado_sin_confirmar_en.is_not(None))
        if profesional_id is not None:
            consulta = consulta.where(TurnoModel.profesional_id == profesional_id)
        if paciente_id is not None:
            consulta = consulta.where(TurnoModel.paciente_id == paciente_id)
        if desde is not None:
            consulta = consulta.where(TurnoModel.inicio >= desde)
        if hasta is not None:
            consulta = consulta.where(TurnoModel.inicio < hasta)
        consulta = consulta.order_by(TurnoModel.inicio, TurnoModel.id).offset(offset)
        if limit is not None:
            consulta = consulta.limit(limit)
        filas = await self._sesion.scalars(consulta)
        return [self._entidad(modelo) for modelo in filas]

    async def hay_solapamiento(
        self, consultorio_id: int, profesional_id: int, inicio: datetime,
        fin: datetime, excluir_id: int | None = None,
    ) -> bool:
        consulta = select(TurnoModel.id).where(
            TurnoModel.consultorio_id == consultorio_id,
            TurnoModel.profesional_id == profesional_id,
            TurnoModel.estado.in_(("pendiente", "confirmado", "atendido", "ausente")),
            TurnoModel.inicio < fin, TurnoModel.fin > inicio,
        )
        if excluir_id is not None:
            consulta = consulta.where(TurnoModel.id != excluir_id)
        return await self._sesion.scalar(consulta.limit(1)) is not None

    async def actualizar(self, original: Turno, cambios: dict[str, object]) -> Turno:
        consulta = update(TurnoModel).where(
            TurnoModel.id == original.id,
            TurnoModel.consultorio_id == original.consultorio_id,
            TurnoModel.estado == original.estado,
            TurnoModel.ciclo_confirmacion == original.ciclo_confirmacion,
            TurnoModel.inicio == original.inicio,
            TurnoModel.fin == original.fin,
            TurnoModel.marcado_sin_confirmar_en.is_not_distinct_from(original.marcado_sin_confirmar_en),
        ).values(**cambios).returning(TurnoModel).execution_options(populate_existing=True)
        try:
            modelo = await self._sesion.scalar(consulta)
        except IntegrityError as error:
            if es_solapamiento_de_turnos(error):
                raise HorarioOcupado() from error
            raise
        if modelo is None:
            raise ConflictoDeTurno()
        return self._entidad(modelo)

    async def guardar(self, turno: NuevoTurno) -> Turno:
        modelo = TurnoModel(
            consultorio_id=turno.consultorio_id,
            paciente_id=turno.paciente_id,
            profesional_id=turno.profesional_id,
            box_id=turno.box_id,
            prestacion_id=turno.prestacion_id,
            inicio=turno.inicio,
            fin=turno.fin,
            estado=turno.estado,
            es_sobreturno=turno.es_sobreturno,
            origen=turno.origen,
            creado_por_id=turno.creado_por_id,
            creado_en=turno.creado_en or self._reloj.ahora(),
            actualizado_en=turno.actualizado_en,
            confirmado_en=turno.confirmado_en,
        )
        self._sesion.add(modelo)
        try:
            await self._sesion.flush()
        except IntegrityError as error:
            if es_solapamiento_de_turnos(error):
                raise HorarioOcupado() from error
            raise
        await self._sesion.refresh(modelo)
        return self._entidad(modelo)
