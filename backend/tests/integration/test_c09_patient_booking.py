"""Reserva online RN-62/RN-64 con PostgreSQL real."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from tests.integration.c07_support import AHORA, INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    e = await preparar_escenario(sesiones, url_base)
    async with sesiones() as s:
        await s.execute(text("UPDATE paciente SET usuario_id=:u WHERE id=:p"),
                        {"u": e.usuarios[1, "paciente"], "p": e.pacientes[1]})
        await s.execute(text("UPDATE usuario SET email_verificado=true WHERE id=:u"),
                        {"u": e.usuarios[1, "paciente"]})
        await s.commit()
    return e


def online(e, inicio=INICIO):
    return {"profesional_id": e.profesionales[1], "prestacion_id": e.prestaciones[1],
            "inicio": inicio.isoformat()}


async def test_verified_patient_books_for_current_record(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json=online(escenario))
    assert r.status_code == 201, r.text
    assert r.json()["paciente_id"] == escenario.pacientes[1]
    async with sesiones() as s:
        assert (await s.execute(text("SELECT origen,estado FROM turno"))).one() == ("online", "pendiente")
        assert await s.scalar(text("SELECT count(*) FROM turno_historial")) == 1


@pytest.mark.parametrize("campo", ["paciente_id", "duracion_min", "confirmar", "origen", "fin", "consultorio_id"])
@pytest.mark.parametrize("valor", [None, 1])
async def test_patient_cannot_send_staff_or_server_fields(escenario, sesiones, campo, valor):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json={**online(escenario), campo: valor})
    assert r.status_code == 422
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno")) == 0


@pytest.mark.parametrize("vinculada,verificada", [(True, False), (False, True), (False, False)])
async def test_patient_requires_current_record_and_verified_email(escenario, sesiones, vinculada, verificada):
    async with sesiones() as s:
        await s.execute(text("UPDATE usuario SET email_verificado=:v WHERE id=:u"), {"v": verificada, "u": escenario.usuarios[1,"paciente"]})
        if not vinculada:
            await s.execute(text("UPDATE paciente SET usuario_id=null WHERE id=:p"), {"p": escenario.pacientes[1]})
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json=online(escenario))
    assert r.status_code == 403
    assert "dni" not in r.text.lower() and "rechazada" not in r.text
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno_historial")) == 0


async def test_third_future_booking_exceeds_configured_maximum(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        rs = [await c.post("/api/v1/turnos", headers=escenario.headers("paciente"),
                           json=online(escenario, INICIO+timedelta(hours=n))) for n in range(3)]
    assert [r.status_code for r in rs] == [201, 201, 409]
    assert "2" in rs[-1].text
    assert isinstance(rs[-1].json()["detail"], str)
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno")) == 2
        assert await s.scalar(text("SELECT count(*) FROM turno_historial")) == 2


@pytest.mark.parametrize("dias,codigo", [(60,201),(61,422),(-1,422)])
async def test_online_horizon_uses_local_date(escenario, dias, codigo):
    inicio = AHORA.replace(hour=10) + timedelta(days=dias)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json=online(escenario, inicio))
    assert r.status_code == codigo, r.text


@pytest.mark.parametrize("estado,cuenta", [("cancelado",False),("liberado",False),("atendido",False),("ausente",False),("pendiente",True),("confirmado",True)])
async def test_only_future_active_states_use_limit_including_staff(escenario, sesiones, estado, cuenta):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        staff = await c.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert staff.status_code == 201
        async with sesiones() as s:
            await s.execute(text("UPDATE consultorio SET max_turnos_activos_paciente=1 WHERE id=1"))
            await s.execute(text("UPDATE turno SET estado=:e"), {"e":estado})
            await s.commit()
        r = await c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json=online(escenario,INICIO+timedelta(hours=1)))
    assert r.status_code == (409 if cuenta else 201), r.text


async def test_two_real_connections_cannot_consume_last_place_twice(escenario, sesiones, monkeypatch):
    import asyncio
    from app.infrastructure.db.cuentas import RepositorioCuentas
    original = RepositorioCuentas.ficha_de_usuario
    barrera = asyncio.Barrier(2)
    conexiones = set()
    async def sincronizada(self, cid, uid):
        conexiones.add(await self.sesion.scalar(text("SELECT pg_backend_pid()")))
        await barrera.wait()
        return await original(self,cid,uid)
    monkeypatch.setattr(RepositorioCuentas,"ficha_de_usuario",sincronizada)
    async with sesiones() as s:
        await s.execute(text("UPDATE consultorio SET max_turnos_activos_paciente=1 WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        rs = await asyncio.wait_for(asyncio.gather(*[
            c.post("/api/v1/turnos", headers=escenario.headers("paciente"), json=online(escenario,INICIO+timedelta(hours=n))) for n in range(2)]),10)
    assert len(conexiones)==2
    assert sorted(r.status_code for r in rs)==[201,409]
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno"))==1
        assert await s.scalar(text("SELECT count(*) FROM turno_historial"))==1


@pytest.mark.parametrize("minutos,estado",[(48*60,"pendiente"),(48*60-1,"confirmado")])
async def test_online_initial_state_exact_threshold(escenario,minutos,estado):
    escenario.reloj.fijar(INICIO-timedelta(minutes=minutos))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r=await c.post("/api/v1/turnos",headers=escenario.headers("paciente"),json=online(escenario))
    assert r.status_code==201,r.text
    assert r.json()["estado"]==estado


@pytest.mark.parametrize("dias,minuto,codigo",[(61,0,201),(0,7,422)])
async def test_staff_retains_horizon_exemption_but_not_grid(escenario,dias,minuto,codigo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(inicio=INICIO+timedelta(days=dias,minutes=minuto)))
    assert r.status_code==codigo,r.text


@pytest.mark.parametrize("failure",[None,"history","hitos","commit"])
async def test_online_creation_integration_is_atomic_without_notifications(escenario,sesiones,engine,monkeypatch,failure):
    from app.api.v1.routers.turnos import get_gestion
    from app.application.use_cases.gestionar_turnos import GestionTurnos
    from app.infrastructure.db.historial import RepositorioHistorialSQL
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker
    llamadas=[]
    class Hitos:
        async def planificar(self,unidad,turno,accion,ahora):
            llamadas.append((accion,turno.ciclo_confirmacion))
            if failure=="hitos":
                raise RuntimeError("hitos controlado")
    if failure=="history":
        original=RepositorioHistorialSQL.agregar
        async def fallo(self,*args):
            await original(self,*args)
            raise RuntimeError("historial controlado")
        monkeypatch.setattr(RepositorioHistorialSQL,"agregar",fallo)
    class Sesion(AsyncSession):
        async def commit(self):
            if failure=="commit":
                await self.flush()
                raise RuntimeError("commit controlado")
            await super().commit()
    fabrica=async_sessionmaker(engine,class_=Sesion,expire_on_commit=False)
    escenario.app.dependency_overrides[get_gestion]=lambda:GestionTurnos(lambda:UnidadDeTrabajoSQL(fabrica),escenario.reloj,hitos=Hitos())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,raise_app_exceptions=False),base_url="http://test") as c:
        r=await c.post("/api/v1/turnos",headers=escenario.headers("paciente"),json=online(escenario))
    assert r.status_code==(500 if failure else 201),r.text
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno"))==(0 if failure else 1)
        assert await s.scalar(text("SELECT count(*) FROM turno_historial"))==(0 if failure else 1)
        assert await s.scalar(text("SELECT count(*) FROM notificacion"))==0
    if failure!="history":
        assert llamadas==[("crear",1)]


async def test_openapi_documents_both_creation_payloads(escenario):
    schema=escenario.app.openapi()
    request=schema["paths"]["/api/v1/turnos"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    assert {p["$ref"].rsplit("/",1)[-1] for p in request["anyOf"]}=={"TurnoEntrada","TurnoOnlineEntrada"}


@pytest.mark.parametrize("sobreturno",[False,True])
async def test_occupied_online_booking_offers_private_alternatives(escenario,sesiones,sobreturno):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        assert (await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())).status_code==201
        if sobreturno:
            async with sesiones() as s:
                await s.execute(text("UPDATE turno SET es_sobreturno=true"))
                await s.commit()
        r=await c.post("/api/v1/turnos",headers=escenario.headers("paciente"),json=online(escenario))
    assert r.status_code==409,r.text
    detail=r.json()["detail"]
    assert detail["motivo"]=="horario ocupado"
    assert len(detail["alternativas"])==3
    assert set(detail["alternativas"][0])=={"inicio","fin"}
    assert detail["alternativas"][0]["inicio"].startswith("2026-11-09T10:30")


async def test_online_rejects_off_grid_start(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        r=await c.post("/api/v1/turnos",headers=escenario.headers("paciente"),json=online(escenario,INICIO+timedelta(minutes=7)))
    assert r.status_code==422


async def test_past_staff_reservation_does_not_consume_future_limit(escenario,sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        assert (await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(inicio=INICIO-timedelta(days=7)))).status_code==201
        async with sesiones() as s:
            await s.execute(text("UPDATE consultorio SET max_turnos_activos_paciente=1 WHERE id=1"))
            await s.commit()
        assert (await c.post("/api/v1/turnos",headers=escenario.headers("paciente"),json=online(escenario))).status_code==201
