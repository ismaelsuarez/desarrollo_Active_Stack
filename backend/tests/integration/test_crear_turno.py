from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.application.dto.crear_turno import SolicitudDeTurno
from app.application.use_cases.crear_turno import CrearTurno
from app.domain.errors import (
    HorarioOcupado,
    InicioSinZonaHoraria,
    PrestacionInexistente,
    ProfesionalInexistente,
)
from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.fabricas import (
    contar_turnos,
    crear_prestacion,
    crear_profesional,
    crear_turno,
    hora,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def caso_de_uso(sesiones: async_sessionmaker[AsyncSession]) -> CrearTurno:
    return CrearTurno(lambda: UnidadDeTrabajoSQL(sesiones))


def solicitud(
    profesional_id: int,
    prestacion_id: int,
    inicio: datetime,
    *,
    consultorio_id: int = 1,
) -> SolicitudDeTurno:
    return SolicitudDeTurno(
        consultorio_id=consultorio_id,
        paciente_id=1,
        profesional_id=profesional_id,
        prestacion_id=prestacion_id,
        inicio=inicio,
    )


async def test_crea_un_turno_en_un_horario_libre(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine, box_id=7)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)

    turno = await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10)))

    assert turno.id > 0
    assert turno.estado is EstadoTurno.PENDIENTE
    assert turno.es_sobreturno is False
    assert turno.box_id == 7
    assert (turno.inicio, turno.fin) == (hora(10), hora(10, 30))
    assert await contar_turnos(engine, profesional_id) == 1


async def test_otro_profesional_puede_tener_un_turno_en_el_mismo_horario(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_a = await crear_profesional(engine, box_id=1)
    profesional_b = await crear_profesional(engine, box_id=2)
    prestacion_id = await crear_prestacion(engine)
    turno_a = await caso_de_uso.ejecutar(solicitud(profesional_a, prestacion_id, hora(10)))

    turno_b = await caso_de_uso.ejecutar(solicitud(profesional_b, prestacion_id, hora(10)))

    assert turno_b.profesional_id == profesional_b
    assert turno_b.id != turno_a.id
    assert await contar_turnos(engine, profesional_a) == 1
    assert await contar_turnos(engine, profesional_b) == 1


# --- Rechazar un turno superpuesto del mismo profesional (RN-17) ---


@pytest.mark.parametrize(
    ("existente", "duracion_existente", "nuevo", "duracion_nueva"),
    [
        pytest.param(hora(10), 30, hora(10, 15), 30, id="superposicion-parcial"),
        pytest.param(hora(10), 30, hora(10), 30, id="mismo-horario-exacto"),
        pytest.param(hora(10, 15), 30, hora(10), 60, id="nuevo-contiene-al-existente"),
    ],
)
async def test_rechaza_un_turno_superpuesto_del_mismo_profesional(
    engine: AsyncEngine,
    caso_de_uso: CrearTurno,
    existente: datetime,
    duracion_existente: int,
    nuevo: datetime,
    duracion_nueva: int,
):
    profesional_id = await crear_profesional(engine)
    prestacion_existente = await crear_prestacion(engine, duracion_min=duracion_existente)
    prestacion_nueva = (
        prestacion_existente
        if duracion_nueva == duracion_existente
        else await crear_prestacion(engine, duracion_min=duracion_nueva)
    )
    await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_existente, existente))

    with pytest.raises(HorarioOcupado) as error:
        await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_nueva, nuevo))

    assert str(error.value) == "horario ocupado"
    assert await contar_turnos(engine, profesional_id) == 1


# --- Los turnos contiguos no se superponen ---


async def test_acepta_un_turno_que_empieza_cuando_termina_otro(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)
    await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10)))

    turno = await caso_de_uso.ejecutar(
        solicitud(profesional_id, prestacion_id, hora(10, 30))
    )

    assert (turno.inicio, turno.fin) == (hora(10, 30), hora(11))
    assert await contar_turnos(engine, profesional_id) == 2


async def test_acepta_un_turno_que_termina_cuando_empieza_otro(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)
    await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10, 30)))

    turno = await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10)))

    assert (turno.inicio, turno.fin) == (hora(10), hora(10, 30))
    assert await contar_turnos(engine, profesional_id) == 2


# --- Los turnos cancelados y liberados no ocupan el horario (RN-17, RN-22) ---


@pytest.mark.parametrize("estado_previo", ["cancelado", "liberado"])
async def test_el_horario_de_un_turno_cancelado_o_liberado_queda_libre(
    engine: AsyncEngine, caso_de_uso: CrearTurno, estado_previo: str
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)
    await crear_turno(
        engine,
        profesional_id=profesional_id,
        prestacion_id=prestacion_id,
        inicio=hora(10),
        estado=estado_previo,
    )

    turno = await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10)))

    assert turno.estado is EstadoTurno.PENDIENTE
    assert await contar_turnos(engine, profesional_id) == 2


# --- El profesional y la prestación pertenecen al consultorio (RN-55) ---


async def test_rechaza_un_profesional_inexistente(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    prestacion_id = await crear_prestacion(engine)

    with pytest.raises(ProfesionalInexistente) as error:
        await caso_de_uso.ejecutar(solicitud(999, prestacion_id, hora(10)))

    assert str(error.value) == "profesional inexistente"
    assert await contar_turnos(engine) == 0


async def test_rechaza_una_prestacion_de_otro_consultorio(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine, consultorio_id=1)
    prestacion_ajena = await crear_prestacion(engine, consultorio_id=2)

    with pytest.raises(PrestacionInexistente) as error:
        await caso_de_uso.ejecutar(
            solicitud(profesional_id, prestacion_ajena, hora(10), consultorio_id=1)
        )

    assert str(error.value) == "prestación inexistente"
    assert await contar_turnos(engine) == 0


# --- El inicio del turno es un instante con zona horaria ---


async def test_rechaza_un_inicio_sin_zona_horaria(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine)

    with pytest.raises(InicioSinZonaHoraria) as error:
        await caso_de_uso.ejecutar(
            solicitud(profesional_id, prestacion_id, datetime(2026, 11, 2, 10, 0))
        )

    assert str(error.value) == "el inicio debe indicar zona horaria"
    assert await contar_turnos(engine) == 0


async def test_el_mismo_instante_en_otra_zona_horaria_tambien_esta_ocupado(
    engine: AsyncEngine, caso_de_uso: CrearTurno
):
    profesional_id = await crear_profesional(engine)
    prestacion_id = await crear_prestacion(engine, duracion_min=30)
    await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, hora(10)))
    las_trece_utc = datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc)

    with pytest.raises(HorarioOcupado):
        await caso_de_uso.ejecutar(solicitud(profesional_id, prestacion_id, las_trece_utc))

    assert await contar_turnos(engine, profesional_id) == 1
