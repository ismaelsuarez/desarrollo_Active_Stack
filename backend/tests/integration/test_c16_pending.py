"""Lista dedicada de pendientes marcados, scope y resolución existentes."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.application.errors_turnos import RechazoDeTurno
from app.application.use_cases.consultar_turnos import ConsultarTurnos
from app.domain.entities.auth import Principal,RolUsuario
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

from tests.integration.c07_support import AHORA, INICIO, preparar_escenario
from tests.integration.test_c07_agenda import registrar_turno

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones,url_base)


async def marcar(sesiones, tid):
    async with sesiones() as s:
        await s.execute(text("UPDATE turno SET marcado_sin_confirmar_en=:ahora WHERE id=:id"),{"id":tid,"ahora":AHORA})
        await s.commit()


async def test_list_filters_mark_state_and_clinic_in_chronological_order(escenario,sesiones):
    futuro = await registrar_turno(sesiones,escenario,inicio=INICIO)
    pasado = await registrar_turno(sesiones,escenario,inicio=AHORA-timedelta(days=1))
    await marcar(sesiones,futuro)
    await marcar(sesiones,pasado)
    await registrar_turno(sesiones,escenario,inicio=INICIO+timedelta(hours=1))
    for hora,estado in ((2,"confirmado"),(3,"cancelado"),(4,"liberado")):
        tid = await registrar_turno(sesiones,escenario,inicio=INICIO+timedelta(hours=hora),estado=estado)
        await marcar(sesiones,tid)
    ajeno = await registrar_turno(sesiones,escenario,cid=2,inicio=INICIO)
    await marcar(sesiones,ajeno)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r = await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers())
    assert r.status_code == 200,r.text
    assert [t["id"] for t in r.json()] == [pasado,futuro]
    assert all(t["estado"] == "pendiente" and t["marcado_sin_confirmar_en"] for t in r.json())
    assert all(privado not in r.text for privado in ("dni","email","telefono","obra_social","usuario_id","notas"))


@pytest.mark.parametrize("rol,codigo", [("recepcion",200),("administrador",200),("profesional",403),("paciente",403),("administrativo",403)])
async def test_only_reception_and_admin_can_request_filter(escenario,sesiones,rol,codigo):
    tid = await registrar_turno(sesiones,escenario)
    await marcar(sesiones,tid)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r = await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers(rol))
    assert r.status_code == codigo
    if codigo == 200:
        assert [t["id"] for t in r.json()] == [tid]
    else:
        assert "paciente_nombre" not in r.text


@pytest.mark.parametrize("rol", ["profesional","paciente","administrativo"])
async def test_application_policy_also_rejects_filter_without_router(escenario,sesiones,rol):
    consulta = ConsultarTurnos(lambda:UnidadDeTrabajoSQL(sesiones),escenario.reloj)
    principal = Principal(escenario.usuarios[1,rol],1,RolUsuario(rol))
    with pytest.raises(RechazoDeTurno) as error:
        await consulta.listar(principal,sin_confirmar=True)
    assert error.value.codigo == 403


@pytest.mark.parametrize("rol", ["recepcion","administrador","profesional","paciente"])
async def test_false_and_absent_filter_preserve_previous_role_scope(escenario,sesiones,rol):
    propio = await registrar_turno(sesiones,escenario)
    await registrar_turno(sesiones,escenario,cid=2)
    async with sesiones() as s:
        await s.execute(text("UPDATE paciente SET usuario_id=:u WHERE id=:id"),{"u":escenario.usuarios[1,"paciente"],"id":escenario.pacientes[1]})
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        normal = await c.get("/api/v1/turnos",headers=escenario.headers(rol))
        explicito = await c.get("/api/v1/turnos?sin_confirmar=false",headers=escenario.headers(rol))
    assert normal.status_code == explicito.status_code == 200
    assert normal.json() == explicito.json()
    assert [t["id"] for t in normal.json()] == [propio]


@pytest.mark.parametrize("accion", ["confirmar","cancelar","liberar","reprogramar"])
async def test_existing_actions_resolve_dedicated_list(escenario,sesiones,accion):
    tid = await registrar_turno(sesiones,escenario)
    await marcar(sesiones,tid)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        assert [t["id"] for t in (await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers())).json()] == [tid]
        if accion == "reprogramar":
            r = await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers(),json={"inicio":(INICIO+timedelta(days=1)).isoformat()})
        else:
            r = await c.post(f"/api/v1/turnos/{tid}/{accion}",headers=escenario.headers(),json={})
        assert r.status_code == 200,r.text
        assert (await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers())).json() == []
    if accion == "reprogramar":
        async with sesiones() as s:
            assert (await s.execute(text("SELECT ciclo_confirmacion,marcado_sin_confirmar_en FROM turno WHERE id=:id"),{"id":tid})).one() == (2,None)


async def test_rescheduled_marked_turn_reenters_decision_in_new_cycle(escenario,sesiones):
    from app.application.use_cases.evaluar_hitos_turnos import EvaluarHitosTurnos
    tid = await registrar_turno(sesiones,escenario)
    await marcar(sesiones,tid)
    destino = INICIO+timedelta(days=1)
    async with sesiones() as s:
        await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r = await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers(),json={"inicio":destino.isoformat()})
        assert r.status_code == 200
        assert (await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers())).json() == []
        evaluador = EvaluarHitosTurnos(sesiones,escenario.reloj)
        assert await evaluador.seleccionar_candidatos(1) == []
        escenario.reloj.fijar(destino-timedelta(hours=12))
        assert await evaluador.seleccionar_candidatos(1) == [(tid,2)]
        await evaluador.ejecutar(1)
        assert [t["id"] for t in (await c.get("/api/v1/turnos?sin_confirmar=true",headers=escenario.headers())).json()] == [tid]
    async with sesiones() as s:
        assert (await s.execute(text("SELECT ciclo_confirmacion,marcado_sin_confirmar_en FROM turno WHERE id=:id"),{"id":tid})).one() == (2,escenario.reloj.ahora())
        assert await s.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id AND accion='marcar_sin_confirmar'"),{"id":tid}) == 1


async def test_filter_is_documented_and_validated_as_boolean(escenario):
    schema = escenario.app.openapi()["paths"]["/api/v1/turnos"]["get"]
    parametro = next(p for p in schema["parameters"] if p["name"] == "sin_confirmar")
    assert parametro["in"] == "query" and parametro["schema"]["type"] == "boolean" and parametro["schema"]["default"] is False
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        assert (await c.get("/api/v1/turnos?sin_confirmar=invalid",headers=escenario.headers())).status_code == 422
        assert (await c.get("/api/v1/turnos?sin_confirmar=true")).status_code == 401
