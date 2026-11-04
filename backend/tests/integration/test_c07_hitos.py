from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.api.v1.routers.turnos import get_gestion
from app.application.use_cases.gestionar_turnos import GestionTurnos
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("failure", [None, "crear", "reprogramar"])
async def test_hito_planning_shares_transaction_and_failure_rolls_back_all_effects(sesiones, url_base, failure):
    escenario = await preparar_escenario(sesiones, url_base)
    observados = []

    class Planificador:
        async def planificar(self, unidad, turno, accion, ahora):
            observados.append((accion, turno.id, ahora))
            propio = await unidad.turnos.obtener(turno.consultorio_id, turno.id)
            assert propio.inicio == turno.inicio
            async with sesiones() as independiente:
                inicio_visible = await independiente.scalar(text("SELECT inicio FROM turno WHERE id=:id"), {"id": turno.id})
                assert inicio_visible == (None if accion == "crear" else INICIO)
            if accion == failure:
                raise RuntimeError("planificador controlado")

    escenario.app.dependency_overrides[get_gestion] = lambda: GestionTurnos(
        lambda: UnidadDeTrabajoSQL(sesiones, escenario.reloj), escenario.reloj,
        hitos=Planificador(),
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert alta.status_code == (500 if failure == "crear" else 201)
        if failure != "crear":
            identificador = alta.json()["id"]
            respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": (INICIO + timedelta(days=1)).isoformat()})
            assert respuesta.status_code == (500 if failure == "reprogramar" else 200)
    assert [o[0] for o in observados] == (["crear"] if failure == "crear" else ["crear", "reprogramar"])
    assert all(o[2] == escenario.reloj.ahora() for o in observados)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (0 if failure == "crear" else 1)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (0 if failure == "crear" else 1 if failure == "reprogramar" else 2)
        if failure != "crear":
            assert await sesion.scalar(text("SELECT inicio FROM turno")) == (INICIO if failure == "reprogramar" else INICIO + timedelta(days=1))
