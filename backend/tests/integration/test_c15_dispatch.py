"""Contrato detallado y vigencia de correo C15, PostgreSQL real."""
from datetime import timedelta
import asyncio
import httpx

import pytest

from app.application.services.notificaciones import DespacharNotificacion
from app.domain.ports.reloj import RelojSimulado
from sqlalchemy import select, update
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import TurnoModel
from tests.integration.c07_support import preparar_escenario
from tests.integration.test_notificaciones import (
    AHORA, CorreoGrabado, configuracion, leer, preparar,
)

pytestmark = pytest.mark.integration


async def test_resultado_detallado_de_entrega_y_no_reenvio(sesiones):
    identifier = await preparar(sesiones)
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    result = await dispatcher.ejecutar_detallado(1, identifier)
    assert (result.reclamada, result.estado, result.motivo) == (True, 'enviada', 'entregada')
    repeated = await dispatcher.ejecutar_detallado(1, identifier)
    assert (repeated.reclamada, repeated.estado) == (False, None)
    assert len(sender.mensajes) == 1


@pytest.mark.parametrize('falla,intentos,estado', [(False,0,'enviada'),(True,0,'programada'),(True,2,'fallida'),(False,3,'fallida')])
async def test_resultados_compatibles_con_bool(sesiones, falla, intentos, estado):
    identifier = await preparar(sesiones, intentos=intentos)
    class Transporte(CorreoGrabado):
        async def enviar(self, *args):
            if falla:
                raise ConnectionError('NO_LOG_ADDRESS@example.test')
            await super().enviar(*args)
    sender = Transporte()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    result = await dispatcher.ejecutar_detallado(1, identifier)
    assert (result.reclamada, result.estado) == (intentos < 3, estado)
    assert (await leer(sesiones, identifier)).reclamada_en is None
    assert await dispatcher.ejecutar(2, identifier) is False


@pytest.mark.parametrize('tipo,estado,ciclo,desfase,esperado', [
    ('solicitud_confirmacion','pendiente',1,1,'omitida'),
    ('solicitud_confirmacion','pendiente',1,48*3600,'enviada'),
    ('solicitud_confirmacion','confirmado',1,1,'omitida'),
    ('recordatorio','confirmado',1,1,'omitida'),
    ('recordatorio','confirmado',1,24*3600,'enviada'),
    ('recordatorio','pendiente',1,0,'omitida'),
    ('recordatorio','pendiente',1,-1,'omitida'),
    ('recordatorio','cancelado',1,1,'omitida'),
    ('recordatorio','liberado',1,1,'omitida'),
    ('recordatorio','atendido',1,1,'omitida'),
    ('recordatorio','ausente',1,1,'omitida'),
    ('recordatorio','pendiente',2,1,'omitida'),
    ('recordatorio','pendiente',None,1,'omitida'),
])
@pytest.mark.parametrize('vencida', [False,True])
async def test_vigencia_portipo_en_primera_toma_y_recuperacion(sesiones,url_base,tipo,estado,ciclo,desfase,esperado,vencida):
    escenario = await preparar_escenario(sesiones,url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url='http://test') as client:
        response = await client.post('/api/v1/turnos',headers=escenario.headers(),json=escenario.payload())
    assert response.status_code == 201
    tid = response.json()['id']
    now = escenario.reloj.ahora()
    async with sesiones() as session, session.begin():
        await session.execute(update(TurnoModel).where(TurnoModel.id==tid).values(
            estado=estado,inicio=now+timedelta(seconds=desfase),fin=now+timedelta(seconds=desfase,minutes=30)))
    identifier = await preparar(sesiones,tipo=tipo,turno_id=tid,ciclo=ciclo,
        programada_para=now,estado='enviando' if vencida else 'programada',
        reclamada_en=now-timedelta(seconds=121) if vencida else None)
    sender = CorreoGrabado()
    dispatcher=DespacharNotificacion(sesiones,escenario.reloj,sender,configuracion())
    result=await dispatcher.ejecutar_detallado(1,identifier)
    assert result.estado == esperado
    assert len(sender.mensajes)==(esperado=='enviada')
    assert (await leer(sesiones,identifier)).reclamada_en is None


@pytest.mark.parametrize('tipo',['liberacion','cancelacion_por_personal','reprogramacion_por_personal','resumen_reserva','cancelacion_por_paciente'])
@pytest.mark.parametrize('vencida',[False,True])
async def test_avisos_hechos_consumados_sin_exigir_turno_activo(sesiones,tipo,vencida):
    identifier=await preparar(sesiones,tipo=tipo,ciclo=99,estado='enviando' if vencida else 'programada',
        reclamada_en=AHORA-timedelta(hours=3) if vencida else None)
    sender=CorreoGrabado()
    result=await DespacharNotificacion(sesiones,RelojSimulado(AHORA),sender,configuracion()).ejecutar_detallado(1,identifier)
    assert result.estado=='enviada'
    assert len(sender.mensajes)==1


@pytest.mark.parametrize('vencida',[False,True])
async def test_vigencia_e_intentos_se_resuelven_antes_del_cupo(sesiones,vencida):
    await preparar(sesiones,estado='enviada',enviada_en=AHORA)
    await preparar(sesiones,estado='enviada',enviada_en=AHORA)
    state=dict(estado='enviando',reclamada_en=AHORA-timedelta(seconds=121)) if vencida else {}
    invalid=await preparar(sesiones,tipo='recordatorio',ciclo=None,intentos=3,**state)
    exhausted=await preparar(sesiones,intentos=3,**state)
    eligible=await preparar(sesiones,intentos=1,**state)
    sender=CorreoGrabado()
    dispatcher=DespacharNotificacion(sesiones,RelojSimulado(AHORA),sender,configuracion(email_daily_limit=2,email_daily_limit_account=1))
    a=await dispatcher.ejecutar_detallado(1,invalid)
    b=await dispatcher.ejecutar_detallado(1,exhausted)
    c=await dispatcher.ejecutar_detallado(1,eligible)
    assert (a.estado,b.estado,c.motivo)==('omitida','fallida','cupo_total')
    row=await leer(sesiones,eligible)
    assert row.intentos==1
    assert row.estado==('enviando' if vencida else 'programada')
    assert sender.mensajes==[]


@pytest.mark.parametrize('turno_ajeno',[False,True])
async def test_recordatorio_sin_turno_propio_es_omitido(sesiones,url_base,turno_ajeno):
    escenario=await preparar_escenario(sesiones,url_base)
    tid=None
    if turno_ajeno:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),base_url='http://test') as client:
            response=await client.post('/api/v1/turnos',headers=escenario.headers(consultorio=2),json=escenario.payload(consultorio=2))
        assert response.status_code==201
        tid=response.json()['id']
    identifier=await preparar(sesiones,tipo='recordatorio',turno_id=tid,ciclo=1)
    sender=CorreoGrabado()
    result=await DespacharNotificacion(sesiones,escenario.reloj,sender,configuracion()).ejecutar_detallado(1,identifier)
    assert result.estado=='omitida'
    assert sender.mensajes==[]
