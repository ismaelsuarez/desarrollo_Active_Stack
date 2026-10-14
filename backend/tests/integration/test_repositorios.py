from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.domain.entities.prestacion import Prestacion
from app.domain.entities.profesional import Profesional
from app.domain.entities.turno import NuevoTurno, Turno
from app.domain.errors import HorarioOcupado
from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.repositorios import (
    RepositorioPrestacionesSQL,
    RepositorioProfesionalesSQL,
)
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.fabricas import (
    contar_turnos,
    crear_prestacion,
    crear_profesional,
    crear_turno,
    hora,
)

pytestmark = pytest.mark.integration


async def test_obtiene_un_profesional_de_su_consultorio(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine, consultorio_id=1, box_id=7)

    async with sesiones() as sesion:
        profesional = await RepositorioProfesionalesSQL(sesion).obtener(
            consultorio_id=1, profesional_id=profesional_id
        )

    assert profesional == Profesional(
        id=profesional_id, consultorio_id=1, box_id=7, nombre="Ana", apellido="Paz"
    )


async def test_un_profesional_de_otro_consultorio_no_existe(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine, consultorio_id=2)

    async with sesiones() as sesion:
        profesional = await RepositorioProfesionalesSQL(sesion).obtener(
            consultorio_id=1, profesional_id=profesional_id
        )

    assert profesional is None


async def test_obtiene_una_prestacion_de_su_consultorio(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    prestacion_id = await crear_prestacion(engine, consultorio_id=1, duracion_min=60)

    async with sesiones() as sesion:
        prestacion = await RepositorioPrestacionesSQL(sesion).obtener(
            consultorio_id=1, prestacion_id=prestacion_id
        )

    assert prestacion == Prestacion(
        id=prestacion_id,
        consultorio_id=1,
        nombre="Consulta de 60 minutos",
        duracion_min=60,
    )


async def test_una_prestacion_de_otro_consultorio_no_existe(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    prestacion_id = await crear_prestacion(engine, consultorio_id=2)

    async with sesiones() as sesion:
        prestacion = await RepositorioPrestacionesSQL(sesion).obtener(
            consultorio_id=1, prestacion_id=prestacion_id
        )

    assert prestacion is None


def turno_nuevo(profesional_id: int, prestacion_id: int, inicio: datetime) -> NuevoTurno:
    return NuevoTurno(
        consultorio_id=1,
        paciente_id=1,
        profesional_id=profesional_id,
        box_id=1,
        prestacion_id=prestacion_id,
        inicio=inicio,
        fin=inicio + timedelta(minutes=30),
    )


async def test_un_turno_guardado_es_visible_desde_otra_unidad_de_trabajo(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine)

    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        turno = await unidad.turnos.guardar(
            turno_nuevo(profesional_id, prestacion_id, hora(10))
        )

    assert turno == Turno(
        id=turno.id,
        consultorio_id=1,
        paciente_id=1,
        profesional_id=profesional_id,
        box_id=1,
        prestacion_id=prestacion_id,
        inicio=hora(10),
        fin=hora(10, 30),
        estado=EstadoTurno.PENDIENTE,
        es_sobreturno=False,
    )
    assert turno.id > 0
    assert await contar_turnos(engine, profesional_id) == 1


async def test_una_unidad_de_trabajo_que_falla_no_guarda_el_turno(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine)

    with pytest.raises(RuntimeError):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            await unidad.turnos.guardar(
                turno_nuevo(profesional_id, prestacion_id, hora(10))
            )
            raise RuntimeError("falla después de guardar")

    assert await contar_turnos(engine, profesional_id) == 0


async def test_guardar_sobre_un_horario_ocupado_lanza_horario_ocupado(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine)
    await crear_turno(
        engine, profesional_id=profesional_id, prestacion_id=prestacion_id, inicio=hora(10)
    )

    with pytest.raises(HorarioOcupado):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            await unidad.turnos.guardar(
                turno_nuevo(profesional_id, prestacion_id, hora(10, 15))
            )

    assert await contar_turnos(engine, profesional_id) == 1


async def test_otro_error_de_integridad_no_se_informa_como_horario_ocupado(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession]
):
    profesional_id = await crear_profesional(engine)
    prestacion_inexistente = 999

    with pytest.raises(IntegrityError) as error:
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            await unidad.turnos.guardar(
                turno_nuevo(profesional_id, prestacion_inexistente, hora(10))
            )

    assert error.value.orig.sqlstate == "23503"
    assert await contar_turnos(engine) == 0
