"""Barrido finito, resultados propios y recuperación durable."""
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select, update

from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.account_models import NotificacionModel, BarridoEstadoModel
from tests.integration.test_notificaciones import AHORA, CorreoGrabado, configuracion, leer, preparar

pytestmark = pytest.mark.integration


async def test_barrido_despacha_atraso_y_conserva_futuro(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    due = await preparar(sesiones, programada_para=AHORA-timedelta(hours=3))
    future = await preparar(sesiones, programada_para=AHORA+timedelta(seconds=1))
    sender = CorreoGrabado()
    clock, settings = RelojSimulado(AHORA), configuracion()
    sweep = EjecutarBarrido(sesiones, clock, DespacharNotificacion(sesiones, clock, sender, settings), settings)
    result = await sweep.ejecutar(1)
    assert (result.reclamadas,result.enviadas,result.reintentadas,result.omitidas,result.fallidas)==(1,1,0,0,0)
    assert (await leer(sesiones,future)).estado == 'programada'
    repeated = await sweep.ejecutar(1)
    assert repeated.enviadas == 0
    assert len(sender.mensajes)==1


async def test_cuatro_grupos_acotados_y_futuros_ajenos_excluidos(sesiones):
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    await preparar(sesiones)
    async with sesiones() as session, session.begin():
        session.add_all(NotificacionModel(consultorio_id=1,tipo=tipo,canal='email',estado=estado,
            programada_para=AHORA-timedelta(hours=3),reclamada_en=AHORA-timedelta(seconds=121) if estado=='enviando' else None,
            destinatario='test@example.test',intentos=1) for estado in ('programada','enviando')
            for tipo in ('verificacion_email','cancelacion_por_personal') for _ in range(105))
    sweep=EjecutarBarrido(sesiones,RelojSimulado(AHORA),None,configuracion())
    ids=await sweep.seleccionar_candidatos(1)
    assert len(ids)==400
    assert len(set(ids))==400
    assert ids==await sweep.seleccionar_candidatos(1)


async def test_lote_mixto_y_reintento_una_vez_por_ejecucion(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    sent=await preparar(sesiones)
    retry=await preparar(sesiones,destinatario='retry@example.test')
    exhausted=await preparar(sesiones,intentos=3,estado='enviando',reclamada_en=AHORA-timedelta(hours=3))
    omitted=await preparar(sesiones,tipo='vinculacion_rechazada')
    class Parcial(CorreoGrabado):
        async def enviar(self, destinatario,*args):
            if destinatario.startswith('retry'):
                raise ConnectionError('NOLOG')
            await super().enviar(destinatario,*args)
    sender=Parcial()
    clock,settings=RelojSimulado(AHORA),configuracion()
    sweep=EjecutarBarrido(sesiones,clock,DespacharNotificacion(sesiones,clock,sender,settings),settings)
    result=await sweep.ejecutar(1)
    assert (result.reclamadas,result.enviadas,result.reintentadas,result.omitidas,result.fallidas)==(2,1,1,1,1)
    assert (await leer(sesiones,retry)).intentos==1


async def test_ultimo_barrido_durable_y_error_sin_texto_sensible(sesiones):
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    await preparar(sesiones)
    class Fallo:
        async def ejecutar_detallado(self,*args):
            raise RuntimeError('NO_PERSISTIR_SECRETO')
    sweep=EjecutarBarrido(sesiones,RelojSimulado(AHORA),Fallo(),configuracion())
    with pytest.raises(RuntimeError):
        await sweep.ejecutar(1)
    async with sesiones() as session:
        state=await session.get(BarridoEstadoModel,1)
        assert state.estado=='error'
        assert state.iniciado_en==state.finalizado_en==AHORA
        assert state.reclamadas==0


async def test_fin_viejo_no_sustituye_barrido_posterior(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    await preparar(sesiones)
    start,finish=asyncio.Event(),asyncio.Event()
    class Lento(CorreoGrabado):
        async def enviar(self,*args):
            start.set()
            await finish.wait()
    clock,settings=RelojSimulado(AHORA),configuracion()
    old=EjecutarBarrido(sesiones,clock,DespacharNotificacion(sesiones,clock,Lento(),settings),settings)
    task=asyncio.create_task(old.ejecutar(1))
    await asyncio.wait_for(start.wait(),5)
    clock2=RelojSimulado(AHORA+timedelta(seconds=1))
    new=EjecutarBarrido(sesiones,clock2,DespacharNotificacion(sesiones,clock2,CorreoGrabado(),settings),settings)
    try:
        result=await new.ejecutar(1)
    finally:
        finish.set()
        await task
    async with sesiones() as session:
        state=await session.get(BarridoEstadoModel,1)
        assert state.ejecucion_id==result.ejecucion_id
        assert state.estado=='exitoso'
        assert state.enviadas==0
