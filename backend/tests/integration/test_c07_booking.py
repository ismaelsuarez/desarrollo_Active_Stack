import httpx
import pytest
from datetime import timedelta
from sqlalchemy import text
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.models import BloqueoAgendaModel, TurnoModel
from tests.integration.c07_support import AHORA

from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


async def test_staff_creates_turn_for_unlinked_patient_with_atomic_history(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert respuesta.status_code == 201, respuesta.text
    turno = respuesta.json()
    assert turno["estado"] == "pendiente"
    assert turno["es_sobreturno"] is False
    assert turno["ciclo_confirmacion"] == 1
    async with sesiones() as sesion:
        fila = (await sesion.execute(text("SELECT inicio, fin, creado_por_id, origen, creado_en FROM turno WHERE id=:id"), {"id": turno["id"]})).one()
        assert fila.inicio == INICIO
        assert (fila.fin - fila.inicio).total_seconds() == 1800
        assert fila.creado_por_id == escenario.usuarios[1, "recepcion"]
        assert fila.origen == "recepcion"
        assert fila.creado_en == escenario.reloj.ahora()
        hecho = (await sesion.execute(text("SELECT accion, usuario_id, estado_nuevo, ocurrido_en FROM turno_historial WHERE turno_id=:id"), {"id": turno["id"]})).one()
        assert (hecho.accion, hecho.usuario_id, hecho.estado_nuevo) == ("crear", escenario.usuarios[1, "recepcion"], "pendiente")
        assert hecho.ocurrido_en == escenario.reloj.ahora()


@pytest.mark.parametrize("rol,esperado", [("administrador", 201), ("profesional", 403), ("paciente", 422), ("administrativo", 403), (None, 401)])
async def test_booking_is_restricted_to_authenticated_staff(escenario, sesiones, rol, esperado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(rol) if rol else {}, json=escenario.payload())
    assert respuesta.status_code == esperado
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (1 if esperado == 201 else 0)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (1 if esperado == 201 else 0)


@pytest.mark.parametrize("campo,valor", [("consultorio_id", 2), ("fin", "2026-11-09T11:00:00-03:00"), ("es_sobreturno", True)])
async def test_booking_rejects_fields_owned_by_server(escenario, sesiones, campo, valor):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(**{campo: valor}))
    assert respuesta.status_code == 422
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 0


@pytest.mark.parametrize("campo", ["paciente_id", "profesional_id", "prestacion_id"])
@pytest.mark.parametrize("foreign", [True, False])
async def test_booking_hides_foreign_and_missing_references(escenario, sesiones, campo, foreign):
    payload = escenario.payload()
    payload[campo] = escenario.payload(consultorio=2)[campo] if foreign else 999999
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=payload)
    assert respuesta.status_code == 404
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 0


@pytest.mark.parametrize("hour,minute,expected", [(9, 0, 201), (11, 30, 201), (13, 0, 201), (9, 7, 422), (11, 45, 422), (12, 0, 422), (16, 45, 422)])
async def test_whole_interval_fits_one_block_and_anchored_grid(escenario, sesiones, hour, minute, expected):
    async with sesiones() as sesion:
        await sesion.execute(text("DELETE FROM horario_semanal WHERE consultorio_id=1"))
        await sesion.execute(text("INSERT INTO horario_semanal (consultorio_id, profesional_id, dia_semana, hora_inicio, hora_fin) VALUES (1,:p,1,'09:00','12:00'),(1,:p,1,'13:00','17:00')"), {"p": escenario.profesionales[1]})
        await sesion.commit()
    inicio = INICIO.replace(hour=hour, minute=minute)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(inicio=inicio))
    assert respuesta.status_code == expected
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (1 if expected == 201 else 0)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (1 if expected == 201 else 0)


@pytest.mark.parametrize("scope", ["global", "own", "foreign"])
@pytest.mark.parametrize("offset,length", [(-5, 10), (0, 30), (5, 5)])
async def test_global_and_own_blocks_reject_partial_and_full_intersection(escenario, sesiones, scope, offset, length):
    cid = 2 if scope == "foreign" else 1
    async with sesiones() as sesion:
        sesion.add(BloqueoAgendaModel(
            consultorio_id=cid, profesional_id=None if scope == "global" else escenario.profesionales[cid],
            tipo="bloqueo", inicio=INICIO + timedelta(minutes=offset),
            fin=INICIO + timedelta(minutes=offset + length),
            creado_por_id=escenario.usuarios[cid, "administrador"], creado_en=AHORA,
        ))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert respuesta.status_code == (201 if scope == "foreign" else 422)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (1 if scope == "foreign" else 0)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (1 if scope == "foreign" else 0)


@pytest.mark.parametrize("catalogo,ajuste,esperado,duracion", [(30, None, 201, 30), (60, None, 201, 60), (30, 45, 201, 45), (20, None, 201, 20), (30, 20, 422, None), (30, 0, 422, None), (30, -1, 422, None)])
async def test_catalog_duration_and_staff_adjustment_without_rounding(escenario, sesiones, catalogo, ajuste, esperado, duracion):
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE prestacion SET duracion_min=:duracion WHERE id=:id"), {"duracion": catalogo, "id": escenario.prestaciones[1]})
        await sesion.commit()
    extras = {} if ajuste is None else {"duracion_min": ajuste}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(**extras))
    assert respuesta.status_code == esperado, respuesta.text
    async with sesiones() as sesion:
        if esperado == 201:
            assert await sesion.scalar(text("SELECT extract(epoch from fin-inicio)/60 FROM turno")) == duracion
            await sesion.execute(text("UPDATE prestacion SET duracion_min=90 WHERE id=:id"), {"id": escenario.prestaciones[1]})
            await sesion.commit()
            assert await sesion.scalar(text("SELECT extract(epoch from fin-inicio)/60 FROM turno")) == duracion
        else:
            assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0
            assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 0


@pytest.mark.parametrize("minutes,manual,expected,motivo", [(2879, False, "confirmado", "RN-29"), (2880, False, "pendiente", "RN-23"), (2881, False, "pendiente", "RN-23"), (2881, True, "confirmado", "confirmacion_manual")])
async def test_initial_state_uses_exact_clock_threshold_and_distinguishes_manual_confirmation(escenario, sesiones, minutes, manual, expected, motivo):
    escenario.reloj.fijar(INICIO - timedelta(minutes=minutes))
    extras = {"confirmar": True} if manual else {}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(**extras))
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["estado"] == expected
    async with sesiones() as sesion:
        fila = (await sesion.execute(text("SELECT confirmado_en,creado_en FROM turno"))).one()
        assert fila.creado_en == escenario.reloj.ahora()
        assert fila.confirmado_en == (escenario.reloj.ahora() if expected == "confirmado" else None)
        hecho = (await sesion.execute(text("SELECT usuario_id,detalle FROM turno_historial"))).one()
        assert hecho.usuario_id == escenario.usuarios[1, "recepcion"]
        assert hecho.detalle == {"motivo": motivo}


@pytest.mark.parametrize("invalid", [False, True])
async def test_staff_can_book_third_active_turn_at_61_days_but_still_requires_valid_grid(escenario, sesiones, invalid):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        for dias in (3, 4):
            respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(inicio=AHORA.replace(hour=10) + timedelta(days=dias)))
            assert respuesta.status_code == 201
        destino = (AHORA + timedelta(days=61)).replace(hour=9, minute=7 if invalid else 0)
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers("administrador"), json=escenario.payload(inicio=destino))
    assert respuesta.status_code == (422 if invalid else 201)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (2 if invalid else 3)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (2 if invalid else 3)


async def test_booking_openapi_documents_strict_staff_payload_and_conflicts(escenario):
    schema = escenario.app.openapi()
    alta = schema["paths"]["/api/v1/turnos"]["post"]
    assert {"201", "401", "403", "404", "409", "422"} <= set(alta["responses"])
    entrada = schema["components"]["schemas"]["TurnoEntrada"]
    assert entrada["additionalProperties"] is False
    assert "consultorio_id" not in entrada["properties"]
    assert "fin" not in entrada["properties"]
    assert "duracion_min" in entrada["properties"]
    assert "confirmar" in entrada["properties"]


@pytest.mark.parametrize("failure,expected", [("runtime", 500), ("exclusion", 409)])
async def test_api_does_not_report_success_before_commit_and_rolls_back_late_errors(escenario, sesiones, engine, failure, expected):
    class FallaCommit(AsyncSession):
        async def commit(self):
            await self.flush()
            if failure == "runtime":
                raise RuntimeError("falla controlada de commit")
            fila = await self.scalar(select(TurnoModel))
            self.add(TurnoModel(
                consultorio_id=fila.consultorio_id, paciente_id=fila.paciente_id,
                profesional_id=fila.profesional_id, box_id=fila.box_id,
                prestacion_id=fila.prestacion_id, inicio=fila.inicio, fin=fila.fin,
                creado_en=fila.creado_en,
            ))
            await super().commit()

    escenario.app.state.session_factory = async_sessionmaker(engine, class_=FallaCommit, expire_on_commit=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert respuesta.status_code == expected
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 0
