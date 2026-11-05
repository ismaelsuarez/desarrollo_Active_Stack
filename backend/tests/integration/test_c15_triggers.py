"""El disparador interno no abre trabajo sin su credencial de servidor."""
from dataclasses import dataclass
from uuid import UUID

import httpx
import pytest

from tests.integration.c07_support import preparar_escenario

pytestmark = pytest.mark.integration


@dataclass
class Resumen:
    ejecucion_id: UUID = UUID("11111111-1111-1111-1111-111111111111")
    reclamadas: int = 2
    enviadas: int = 1
    reintentadas: int = 1
    omitidas: int = 0
    fallidas: int = 0


class BarridoControlado:
    def __init__(self, error=False):
        self.consultorios = []
        self.error = error

    async def ejecutar(self, cid):
        self.consultorios.append(cid)
        if self.error:
            raise RuntimeError("smtp://private-password@private-email.test")
        return Resumen()


@pytest.fixture
async def contexto(sesiones, url_base):
    e = await preparar_escenario(sesiones, url_base)
    return e


@pytest.mark.parametrize("secret", [None, "incorrecto"])
async def test_missing_or_wrong_secret_rejects_without_work(contexto, secret):
    worker = BarridoControlado()
    contexto.app.state.barrido = worker
    from pydantic import SecretStr
    contexto.app.state.settings.sweep_shared_secret = SecretStr("sweep-test")
    headers = {} if secret is None else {"X-Sweep-Secret": secret}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
        response = await c.post("/internal/barrido", headers=headers)
    assert response.status_code == 403
    assert worker.consultorios == []


async def test_configured_secret_runs_only_server_consultorio_and_hides_openapi(contexto):
    from pydantic import SecretStr
    contexto.app.state.settings.sweep_shared_secret = SecretStr("sweep-test")
    worker = BarridoControlado()
    contexto.app.state.barrido = worker
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
        response = await c.post("/internal/barrido", headers={"X-Sweep-Secret": "sweep-test"})
        schema = await c.get("/openapi.json")
    assert response.status_code == 200, response.text
    assert response.json() == {"ejecucion_id": str(Resumen.ejecucion_id), "reclamadas": 2,
                               "enviadas": 1, "reintentadas": 1, "omitidas": 0, "fallidas": 0}
    assert worker.consultorios == [1]
    assert "/internal/barrido" not in schema.json()["paths"]


@pytest.mark.parametrize("secret", [None, ""])
async def test_unconfigured_http_secret_never_runs(contexto, secret):
    from pydantic import SecretStr
    contexto.app.state.settings.sweep_shared_secret = None if secret is None else SecretStr(secret)
    worker = BarridoControlado()
    contexto.app.state.barrido = worker
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
        response = await c.post("/internal/barrido", headers={"X-Sweep-Secret": "sweep-test"})
    assert response.status_code == 403
    assert worker.consultorios == []


@pytest.mark.parametrize("query,body", [("?consultorio_id=2", None), ("", {"consultorio_id": 2}), ("", {})])
async def test_query_and_body_are_forbidden_without_processing(contexto, query, body):
    from pydantic import SecretStr
    contexto.app.state.settings.sweep_shared_secret = SecretStr("sweep-test")
    worker = BarridoControlado()
    contexto.app.state.barrido = worker
    kwargs = {} if body is None else {"json": body}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
        response = await c.post("/internal/barrido"+query, headers={"X-Sweep-Secret": "sweep-test"}, **kwargs)
    assert response.status_code == 422
    assert worker.consultorios == []


async def test_infrastructure_error_is_safe_and_does_not_leak(contexto, caplog):
    from pydantic import SecretStr
    contexto.app.state.settings.sweep_shared_secret = SecretStr("sweep-test")
    worker = BarridoControlado(error=True)
    contexto.app.state.barrido = worker
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
        response = await c.post("/internal/barrido", headers={"X-Sweep-Secret": "sweep-test"})
    assert response.status_code == 503
    assert worker.consultorios == [1]
    for private in ("private-password", "private-email.test", "sweep-test"):
        assert private not in response.text + caplog.text


async def test_http_and_lifespan_use_same_real_composition(contexto, sesiones, monkeypatch):
    import asyncio
    from pydantic import SecretStr
    from sqlalchemy import text
    from app.infrastructure.barrido import componer_barrido
    from app.infrastructure.planificador import BucleBarrido
    settings = contexto.app.state.settings
    settings.sweep_shared_secret = SecretStr("sweep-test")
    settings.sweep_in_process_enabled = True
    actual = componer_barrido(contexto.app, contexto.reloj, settings)
    invoked, waiting = asyncio.Event(), asyncio.Event()
    original = BucleBarrido.ejecutar
    async def observar(self):
        assert self.planificador is actual
        invoked.set()
        await waiting.wait()
        await original(self)
    monkeypatch.setattr(BucleBarrido, "ejecutar", observar)
    async with contexto.app.router.lifespan_context(contexto.app):
        await asyncio.wait_for(invoked.wait(), 3)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url="http://test") as c:
            response = await c.post("/internal/barrido", headers={"X-Sweep-Secret":"sweep-test"})
        assert response.status_code == 200, response.text
        assert contexto.app.state.barrido is actual
        async with sesiones() as s:
            row = (await s.execute(text("SELECT ejecucion_id,estado FROM barrido_estado WHERE consultorio_id=1"))).one()
            assert str(row.ejecucion_id) == response.json()["ejecucion_id"]
            assert row.estado == "exitoso"
