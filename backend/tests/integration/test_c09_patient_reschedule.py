"""Reprogramación propia RN-37/RN-64."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from tests.integration.c07_support import INICIO, AHORA
from tests.integration.test_c09_patient_booking import escenario, online

pytestmark = pytest.mark.integration


async def test_patient_reschedules_adjusted_duration_without_extra_place(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta = await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(duracion_min=45))
        assert alta.status_code == 201
        tid=alta.json()["id"]
        async with sesiones() as s:
            await s.execute(text("UPDATE consultorio SET max_turnos_activos_paciente=1 WHERE id=1"))
            await s.execute(text("UPDATE turno SET marcado_sin_confirmar_en=:a"),{"a":AHORA})
            await s.commit()
        destino=INICIO+timedelta(days=1)
        r=await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers("paciente"),json={"inicio":destino.isoformat()})
    assert r.status_code==200,r.text
    assert r.json()["id"]==tid
    assert r.json()["ciclo_confirmacion"]==2
    async with sesiones() as s:
        fila=(await s.execute(text("SELECT inicio,fin,marcado_sin_confirmar_en FROM turno"))).one()
        assert fila.inicio==destino and fila.fin==destino+timedelta(minutes=45)
        assert fila.marcado_sin_confirmar_en is None
        assert await s.scalar(text("SELECT count(*) FROM turno_historial"))==2
        assert await s.scalar(text("SELECT count(*) FROM notificacion"))==0


@pytest.mark.parametrize("extra",[{"duracion_min":None},{"duracion_min":30},{"paciente_id":1}])
async def test_patient_patch_rejects_extra_fields(escenario,extra):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())
        r=await c.patch(f'/api/v1/turnos/{alta.json()["id"]}',headers=escenario.headers("paciente"),json={"inicio":(INICIO+timedelta(days=1)).isoformat(),**extra})
    assert r.status_code==422


@pytest.mark.parametrize("dias,minutos,esperado",[(1,0,200),(61,0,422),(1,7,422)])
async def test_patient_patch_horizon_grid_and_unchanged_on_rejection(escenario,sesiones,dias,minutos,esperado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())
        tid=alta.json()["id"]
        r=await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers("paciente"),json={"inicio":(AHORA.replace(hour=10)+timedelta(days=dias,minutes=minutos)).isoformat()})
    assert r.status_code==esperado,r.text
    if esperado!=200:
        async with sesiones() as s:
            assert (await s.execute(text("SELECT inicio,ciclo_confirmacion FROM turno"))).one()==(INICIO,1)
            assert await s.scalar(text("SELECT count(*) FROM turno_historial"))==1


@pytest.mark.parametrize("minutos,codigo",[(24*60,200),(24*60-1,403)])
async def test_patient_patch_exact_window_and_contact(escenario,sesiones,minutos,codigo):
    async with sesiones() as s:
        await s.execute(text("UPDATE consultorio SET telefono='011-5555-0000' WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())
        escenario.reloj.fijar(INICIO-timedelta(minutes=minutos))
        r=await c.patch(f'/api/v1/turnos/{alta.json()["id"]}',headers=escenario.headers("paciente"),json={"inicio":(INICIO+timedelta(days=1)).isoformat()})
    assert r.status_code==codigo,r.text
    if codigo==403:
        assert "011-5555-0000" in r.text


@pytest.mark.parametrize("minutos,estado",[(48*60,"pendiente"),(48*60-1,"confirmado")])
async def test_reschedule_restarts_state_at_confirmation_threshold(escenario,minutos,estado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())
        destino=INICIO-timedelta(days=1)
        escenario.reloj.fijar(destino-timedelta(minutes=minutos))
        r=await c.patch(f'/api/v1/turnos/{alta.json()["id"]}',headers=escenario.headers("paciente"),json={"inicio":destino.isoformat()})
    assert r.status_code==200,r.text
    assert r.json()["estado"]==estado and r.json()["ciclo_confirmacion"]==2


@pytest.mark.parametrize("catalogo_inactivo",[False,True])
async def test_occupied_patch_preserves_every_original_field_and_offers_45min(escenario,sesiones,catalogo_inactivo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(duracion_min=45))
        tid=alta.json()["id"]
        assert (await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(inicio=INICIO+timedelta(days=1)))).status_code==201
        async with sesiones() as s:
            if catalogo_inactivo:
                await s.execute(text("UPDATE prestacion SET activa=false WHERE id=:id"),{"id":escenario.prestaciones[1]})
                await s.commit()
            antes=dict((await s.execute(text("SELECT * FROM turno WHERE id=:id"),{"id":tid})).mappings().one())
        r=await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers("paciente"),json={"inicio":(INICIO+timedelta(days=1)).isoformat()})
    assert r.status_code==409,r.text
    alternativas=r.json()["detail"]["alternativas"]
    from datetime import datetime
    assert all(datetime.fromisoformat(i["fin"])-datetime.fromisoformat(i["inicio"])==timedelta(minutes=45) for i in alternativas)
    assert len(alternativas)==3
    async with sesiones() as s:
        assert dict((await s.execute(text("SELECT * FROM turno WHERE id=:id"),{"id":tid})).mappings().one())==antes
        assert await s.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"),{"id":tid})==1


@pytest.mark.parametrize("failure",["history","hitos","commit"])
async def test_online_patch_rolls_back_complete_cycle(escenario,sesiones,engine,monkeypatch,failure):
    from app.api.v1.routers.turnos import get_gestion
    from app.application.use_cases.gestionar_turnos import GestionTurnos
    from app.infrastructure.db.historial import RepositorioHistorialSQL
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    from sqlalchemy.ext.asyncio import AsyncSession,async_sessionmaker
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,raise_app_exceptions=False),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload())
        tid=alta.json()["id"]
        async with sesiones() as s:
            await s.execute(text("UPDATE turno SET marcado_sin_confirmar_en=:a"),{"a":AHORA})
            await s.commit()
            antes=dict((await s.execute(text("SELECT * FROM turno WHERE id=:id"),{"id":tid})).mappings().one())
        if failure=="history":
            original=RepositorioHistorialSQL.agregar
            async def fallo(self,*args):
                await original(self,*args)
                raise RuntimeError("historial controlado")
            monkeypatch.setattr(RepositorioHistorialSQL,"agregar",fallo)
        class Hitos:
            async def planificar(self,unidad,turno,accion,ahora):
                assert turno.ciclo_confirmacion==2
                if failure=="hitos":
                    raise RuntimeError("hitos controlado")
        class Sesion(AsyncSession):
            async def commit(self):
                if failure=="commit":
                    await self.flush()
                    raise RuntimeError("commit controlado")
                await super().commit()
        fabrica=async_sessionmaker(engine,class_=Sesion,expire_on_commit=False)
        escenario.app.dependency_overrides[get_gestion]=lambda:GestionTurnos(lambda:UnidadDeTrabajoSQL(fabrica),escenario.reloj,hitos=Hitos())
        r=await c.patch(f"/api/v1/turnos/{tid}",headers=escenario.headers("paciente"),json={"inicio":(INICIO+timedelta(days=1)).isoformat()})
    assert r.status_code==500
    async with sesiones() as s:
        assert dict((await s.execute(text("SELECT * FROM turno WHERE id=:id"),{"id":tid})).mappings().one())==antes
        assert await s.scalar(text("SELECT count(*) FROM turno_historial"))==1
        assert await s.scalar(text("SELECT count(*) FROM notificacion"))==0


async def test_patient_patch_can_overlap_its_own_original_interval(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url="http://test") as c:
        alta=await c.post("/api/v1/turnos",headers=escenario.headers(),json=escenario.payload(duracion_min=45))
        r=await c.patch(f'/api/v1/turnos/{alta.json()["id"]}',headers=escenario.headers("paciente"),json={"inicio":(INICIO+timedelta(minutes=15)).isoformat()})
    assert r.status_code==200,r.text
    assert r.json()["id"]==alta.json()["id"] and r.json()["ciclo_confirmacion"]==2
