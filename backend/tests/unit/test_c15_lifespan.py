"""El ciclo de vida conserva y espera sólo su tarea opcional de barrido."""
import asyncio

import pytest

from app.main import create_app
from tests.unit.test_c15_settings import settings


class BarridoBloqueado:
    def __init__(self):
        self.entrada = asyncio.Event()
        self.cancelada = asyncio.Event()
        self.cid = None

    async def ejecutar(self, cid):
        self.cid = cid
        self.entrada.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.cancelada.set()


async def test_disabled_loop_never_starts_a_task():
    app = create_app(settings())
    worker = BarridoBloqueado()
    app.state.barrido = worker
    async with app.router.lifespan_context(app):
        await asyncio.sleep(0)
        assert not worker.entrada.is_set()
    assert not worker.cancelada.is_set()


async def test_enabled_loop_runs_server_consultorio_and_awaits_cancelled_send():
    app = create_app(settings(sweep_in_process_enabled=True))
    worker = BarridoBloqueado()
    app.state.barrido = worker
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(worker.entrada.wait(), 2)
        task = app.state.sweep_task
        assert worker.cid == 1
        assert not task.done()
    assert worker.cancelada.is_set()
    assert task.done()
    assert task.cancelled()


async def test_recoverable_failure_waits_interval_then_retries_without_secret_logs(monkeypatch, caplog):
    from app.infrastructure.planificador import BucleBarrido
    calls, intervals = [], []
    second = asyncio.Event()
    async def execute(cid):
        calls.append(cid)
        if len(calls) == 1:
            raise RuntimeError("private-password@private-email.test")
        second.set()
        await asyncio.Event().wait()
    async def wait(seconds):
        intervals.append(seconds)
        await asyncio.sleep(0)
    class Planner:
        ejecutar = staticmethod(execute)
    loop = BucleBarrido(Planner(), 7, 17, esperar=wait)
    task = asyncio.create_task(loop.ejecutar())
    await asyncio.wait_for(second.wait(), 2)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert calls == [7, 7]
    assert intervals == [17]
    assert "private-password" not in caplog.text
    assert "private-email.test" not in caplog.text


async def test_lifespan_disposes_its_own_engine_only_after_awaiting_task(monkeypatch):
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    from app.infrastructure import barrido
    started, cancelled, disposed = asyncio.Event(), asyncio.Event(), asyncio.Event()
    class Engine:
        async def dispose(self):
            assert cancelled.is_set()
            disposed.set()
    engine = Engine()
    monkeypatch.setattr(barrido, "crear_engine", lambda _: engine)
    monkeypatch.setattr(barrido, "crear_fabrica_de_sesiones", lambda _: object())
    async def run(self, cid):
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()
    monkeypatch.setattr(EjecutarBarrido, "ejecutar", run)
    app = create_app(settings(sweep_in_process_enabled=True))
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(started.wait(), 2)
        assert not disposed.is_set()
    assert disposed.is_set()


async def test_lifespan_does_not_dispose_an_externally_owned_factory():
    class Engine:
        async def dispose(self):
            raise AssertionError("La aplicación no es dueña de este recurso")
    app = create_app(settings(sweep_in_process_enabled=True))
    app.state.engine = Engine()
    app.state.session_factory = object()
    worker = BarridoBloqueado()
    app.state.barrido = worker
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(worker.entrada.wait(), 2)
    assert worker.cancelada.is_set()
