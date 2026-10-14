import asyncio

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.dto.crear_turno import SolicitudDeTurno
from app.application.use_cases.crear_turno import CrearTurno
from app.domain.entities.turno import Turno
from app.domain.errors import HorarioOcupado
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.fabricas import (
    contar_turnos,
    crear_prestacion,
    crear_profesional,
    hora,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("reservas", [2, 10])
async def test_solo_una_de_las_reservas_simultaneas_prospera(
    engine: AsyncEngine, sesiones: async_sessionmaker[AsyncSession], reservas: int
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)
    caso_de_uso = CrearTurno(lambda: UnidadDeTrabajoSQL(sesiones))
    solicitud = SolicitudDeTurno(
        consultorio_id=1,
        paciente_id=1,
        profesional_id=profesional_id,
        prestacion_id=prestacion_id,
        inicio=hora(10),
    )

    resultados = await asyncio.gather(
        *(caso_de_uso.ejecutar(solicitud) for _ in range(reservas)),
        return_exceptions=True,
    )

    creados = [resultado for resultado in resultados if isinstance(resultado, Turno)]
    rechazados = [
        resultado for resultado in resultados if isinstance(resultado, HorarioOcupado)
    ]
    assert len(creados) == 1
    assert len(rechazados) == reservas - 1
    assert await contar_turnos(engine, profesional_id) == 1
