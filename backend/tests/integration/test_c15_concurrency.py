"""Caracterización de leases y barridos concurrentes sobre PostgreSQL real."""
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.notificaciones import DespacharNotificacion
from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.account_models import BarridoEstadoModel, NotificacionModel
from tests.integration.test_notificaciones import AHORA, CorreoGrabado, configuracion, leer, preparar

pytestmark = pytest.mark.integration


async def test_two_sweeps_and_immediate_dispatch_claim_different_rows(sesiones, monkeypatch):
    ids = [await preparar(sesiones, destinatario=f"fila-{i}@example.test") for i in range(3)]
    barrier = asyncio.Barrier(3)
    ready = asyncio.Event()
    release = asyncio.Event()
    pids = set()
    starts = []
    original = AsyncSession.scalar
    joined = 0
    async def synchronized_claim(self, statement, *args, **kwargs):
        nonlocal joined
        if getattr(statement, "_for_update_arg", None) is not None and joined < 3:
            joined += 1
            pids.add(await original(self, text("SELECT pg_backend_pid()")))
            await barrier.wait()
        return await original(self, statement, *args, **kwargs)
    monkeypatch.setattr(AsyncSession, "scalar", synchronized_claim)
    class Transporte:
        async def enviar(self, destinatario, *_):
            # A separate transaction takes NOWAIT: the dispatcher has already
            # committed its claim and is not holding the row during transport.
            async with sesiones() as s, s.begin():
                row = await s.scalar(select(NotificacionModel).where(
                    NotificacionModel.destinatario == destinatario).with_for_update(nowait=True))
                assert row.estado == "enviando" and row.intentos == 1
            starts.append(destinatario)
            # The immediate dispatch may legitimately lose its only row to a
            # sweep. Two simultaneous transports already prove independent
            # progress; the remaining row is processed after release.
            if len(starts) >= 2:
                ready.set()
            await release.wait()
    settings = configuracion()
    assert settings.redis_url is None
    clock = RelojSimulado(AHORA)
    sender = Transporte()
    a = DespacharNotificacion(sesiones, clock, sender, settings)
    b = DespacharNotificacion(sesiones, clock, sender, settings)
    tasks = [asyncio.create_task(EjecutarBarrido(sesiones, clock, d, settings).ejecutar(1)) for d in (a,b)]
    tasks.append(asyncio.create_task(a.ejecutar(1, ids[0])))
    try:
        await asyncio.wait_for(ready.wait(), 8)
        assert len(pids) == 3
        assert len(set(starts)) == len(starts) >= 2
    finally:
        release.set()
        results = await asyncio.wait_for(asyncio.gather(*tasks), 8)
    assert sum(r.enviadas for r in results[:2]) + int(results[2]) == 3
    assert len(starts) == 3
    assert [(await leer(sesiones, i)).intentos for i in ids] == [1,1,1]


@pytest.mark.parametrize("late_error", [False, True])
async def test_expired_claim_late_result_cannot_overwrite_new_owner(sesiones, late_error):
    identifier = await preparar(sesiones)
    started, release = asyncio.Event(), asyncio.Event()
    class TransporteAnterior:
        async def enviar(self, *_):
            started.set()
            await release.wait()
            if late_error:
                raise ConnectionError("private-error")
    settings = configuracion()
    old = DespacharNotificacion(sesiones, RelojSimulado(AHORA), TransporteAnterior(), settings)
    task = asyncio.create_task(old.ejecutar_detallado(1, identifier))
    await asyncio.wait_for(started.wait(), 5)
    sender = CorreoGrabado()
    new = DespacharNotificacion(sesiones, RelojSimulado(AHORA+timedelta(seconds=121)),sender,settings)
    try:
        replacement = await new.ejecutar_detallado(1,identifier)
        assert replacement.estado == "enviada"
    finally:
        release.set()
        previous = await asyncio.wait_for(task, 5)
    assert previous.reclamada and previous.estado is None
    assert previous.motivo == "reclamacion_perdida"
    row = await leer(sesiones,identifier)
    assert row.estado == "enviada" and row.intentos == 2
    assert row.reclamada_en is None and row.ultimo_error is None
    assert row.enviada_en == AHORA+timedelta(seconds=121)


async def test_cancelled_sweep_leaves_durable_in_progress_then_later_execution_replaces_it(sesiones):
    identifier = await preparar(sesiones)
    entered = asyncio.Event()
    class Bloqueado:
        async def enviar(self, *_):
            entered.set()
            await asyncio.Event().wait()
    clock, settings = RelojSimulado(AHORA), configuracion()
    sweep = EjecutarBarrido(sesiones, clock, DespacharNotificacion(sesiones,clock,Bloqueado(),settings),settings)
    task = asyncio.create_task(sweep.ejecutar(1))
    await asyncio.wait_for(entered.wait(), 5)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    async with sesiones() as s:
        mark = await s.get(BarridoEstadoModel,1)
        old_id = mark.ejecucion_id
        assert mark.estado == "en_curso" and mark.finalizado_en is None
    clock.avanzar(timedelta(seconds=121))
    result = await EjecutarBarrido(sesiones,clock,
        DespacharNotificacion(sesiones,clock,CorreoGrabado(),settings),settings).ejecutar(1)
    assert result.enviadas == 1
    async with sesiones() as s:
        mark = await s.get(BarridoEstadoModel,1)
        assert mark.ejecucion_id != old_id and mark.ejecucion_id == result.ejecucion_id
        assert mark.estado == "exitoso"
    assert (await leer(sesiones, identifier)).estado == "enviada"


async def test_account_quota_does_not_starve_turns_and_repeated_batches_advance(sesiones):
    await preparar(sesiones, estado="enviada", enviada_en=AHORA)
    accounts = [await preparar(sesiones) for _ in range(2)]
    async with sesiones() as s, s.begin():
        s.add_all(NotificacionModel(consultorio_id=1, tipo="cancelacion_por_personal", canal="email",
            estado="programada", destinatario="turno@example.test", programada_para=AHORA-timedelta(hours=3),
            intentos=0, mensaje="hecho") for _ in range(103))
    clock = RelojSimulado(AHORA)
    settings = configuracion(email_daily_limit=500,email_daily_limit_account=1)
    sender = CorreoGrabado()
    sweep = EjecutarBarrido(sesiones,clock,DespacharNotificacion(sesiones,clock,sender,settings),settings)
    first = await sweep.ejecutar(1)
    second = await sweep.ejecutar(1)
    third = await sweep.ejecutar(1)
    assert [first.enviadas,second.enviadas,third.enviadas] == [100,3,0]
    assert len(sender.mensajes) == 103
    assert [(await leer(sesiones, id_)).intentos for id_ in accounts] == [0,0]
    assert [(await leer(sesiones, id_)).estado for id_ in accounts] == ["programada","programada"]


async def test_sweep_does_not_attribute_another_claims_success_to_its_summary(sesiones):
    identifier = await preparar(sesiones)
    entered, release = asyncio.Event(), asyncio.Event()
    class Lento:
        async def enviar(self, *_):
            entered.set()
            await release.wait()
    settings = configuracion()
    clock = RelojSimulado(AHORA)
    old = EjecutarBarrido(sesiones,clock,DespacharNotificacion(sesiones,clock,Lento(),settings),settings)
    task = asyncio.create_task(old.ejecutar(1))
    await asyncio.wait_for(entered.wait(), 5)
    new_clock = RelojSimulado(AHORA+timedelta(seconds=121))
    try:
        assert await DespacharNotificacion(sesiones,new_clock,CorreoGrabado(),settings).ejecutar(1,identifier)
    finally:
        release.set()
        previous = await asyncio.wait_for(task, 5)
    assert previous.reclamadas == 1
    assert (previous.enviadas,previous.reintentadas,previous.omitidas,previous.fallidas) == (0,0,0,0)
    assert (await leer(sesiones,identifier)).estado == "enviada"
