"""Una cancelación de lifespan deja la reclamación recuperable por TTL."""
import asyncio
from datetime import timedelta

import pytest

from app.application.services.notificaciones import DespacharNotificacion
from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
from app.domain.ports.reloj import RelojSimulado
from app.main import create_app
from tests.integration.test_notificaciones import AHORA, CorreoGrabado, configuracion, leer, preparar

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("edad,recuperada", [(119,False), (121,True)])
async def test_shutdown_awaits_send_cancellation_and_recovery_uses_ttl(sesiones, edad, recuperada):
    identifier = await preparar(sesiones)
    entered, cancelled = asyncio.Event(), asyncio.Event()
    class EnvioEnCurso:
        async def enviar(self, *args):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cancelled.set()
    clock = RelojSimulado(AHORA)
    settings = configuracion(sweep_in_process_enabled=True)
    app = create_app(settings)
    app.state.barrido = EjecutarBarrido(sesiones,clock,
        DespacharNotificacion(sesiones,clock,EnvioEnCurso(),settings),settings)
    async with app.router.lifespan_context(app):
        await asyncio.wait_for(entered.wait(), 5)
        task = app.state.sweep_task
        assert (await leer(sesiones,identifier)).estado == "enviando"
    assert task.cancelled()
    assert cancelled.is_set()
    original = await leer(sesiones,identifier)
    assert original.estado == "enviando" and original.intentos == 1
    clock.avanzar(timedelta(seconds=edad))
    sender = CorreoGrabado()
    result = await EjecutarBarrido(sesiones,clock,
        DespacharNotificacion(sesiones,clock,sender,settings),settings).ejecutar(1)
    assert result.enviadas == int(recuperada)
    assert len(sender.mensajes) == int(recuperada)
    final = await leer(sesiones,identifier)
    assert final.estado == ("enviada" if recuperada else "enviando")
    assert final.intentos == (2 if recuperada else 1)
