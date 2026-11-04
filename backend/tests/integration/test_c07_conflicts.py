import asyncio
from datetime import timedelta, time

import httpx
import pytest
from sqlalchemy import text

from app.infrastructure.db.models import HorarioSemanalModel
from app.infrastructure.db.repositorios import RepositorioTurnosSQL
from tests.integration.c07_support import INICIO, preparar_escenario
from tests.integration.fabricas import crear_profesional

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


@pytest.mark.parametrize("estado", ["pendiente", "confirmado", "atendido", "ausente", "cancelado", "liberado"])
@pytest.mark.parametrize("offset,duracion", [(15, 30), (-15, 30), (0, 30), (-15, 60), (0, 15)])
async def test_overlap_matrix_preserves_rows_and_history_on_rejection(escenario, sesiones, estado, offset, duracion):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        primera = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert primera.status_code == 201
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET estado=CAST(:estado AS estado_turno) WHERE id=:id"), {"estado": estado, "id": primera.json()["id"]})
            await sesion.commit()
        segunda = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(inicio=INICIO + timedelta(minutes=offset), duracion_min=duracion))
    ocupado = estado not in ("cancelado", "liberado")
    assert segunda.status_code == (409 if ocupado else 201), segunda.text
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (1 if ocupado else 2)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (1 if ocupado else 2)


@pytest.mark.parametrize("offset", [-30, 30])
async def test_adjacent_intervals_do_not_overlap(escenario, sesiones, offset):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        primera = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        segunda = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(inicio=INICIO + timedelta(minutes=offset)))
    assert primera.status_code == segunda.status_code == 201
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 2
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 2


async def test_regular_cannot_be_created_over_existing_active_overbooking(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        primera = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert primera.status_code == 201
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET es_sobreturno=true WHERE id=:id"), {"id": primera.json()["id"]})
            await sesion.commit()
        segunda = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert segunda.status_code == 409
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 1
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 1


@pytest.mark.parametrize("control", ["same", "professional", "consultorio"])
async def test_concurrent_requests_use_independent_sessions_and_commit_one_winner_without_partial_history(escenario, sesiones, engine, monkeypatch, control):
    second_payload = escenario.payload()
    second_headers = escenario.headers()
    if control == "professional":
        profesional = await crear_profesional(engine, box_id=99)
        async with sesiones() as sesion:
            sesion.add(HorarioSemanalModel(consultorio_id=1, profesional_id=profesional, dia_semana=1, hora_inicio=time(9), hora_fin=time(17)))
            await sesion.commit()
        second_payload["profesional_id"] = profesional
    elif control == "consultorio":
        second_payload, second_headers = escenario.payload(consultorio=2), escenario.headers(consultorio=2)
    barrier = asyncio.Barrier(2)
    sesiones_usadas, conexiones = [], []
    original = RepositorioTurnosSQL.guardar

    async def guardar_sincronizado(repo, nuevo):
        sesiones_usadas.append(repo._sesion)
        conexiones.append(await repo._sesion.scalar(text("SELECT pg_backend_pid()")))
        await barrier.wait()
        return await original(repo, nuevo)

    monkeypatch.setattr(RepositorioTurnosSQL, "guardar", guardar_sincronizado)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuestas = await asyncio.wait_for(asyncio.gather(
            client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload()),
            client.post("/api/v1/turnos", headers=second_headers, json=second_payload),
        ), timeout=15)
    assert sorted(r.status_code for r in respuestas) == ([201, 409] if control == "same" else [201, 201])
    assert len({id(s) for s in sesiones_usadas}) == len(set(conexiones)) == 2
    esperado = 1 if control == "same" else 2
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == esperado
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == esperado
        assert await sesion.scalar(text("SELECT count(*) FROM turno t JOIN turno_historial h ON t.id=h.turno_id WHERE h.accion='crear'")) == esperado
