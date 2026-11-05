"""Recorridos de producto por HTTP, PostgreSQL, reloj y SMTP reales."""
import os
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select,update

from app.application.services.notificaciones import DespacharNotificacion
from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
from app.infrastructure.correo.smtp import EnviadorSMTP
from app.infrastructure.db.models import PacienteModel,TurnoModel
from app.infrastructure.db.account_models import NotificacionModel
from tests.integration.c07_support import preparar_escenario,INICIO
from tests.integration.test_notificaciones import configuracion

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('camino',['confirmar','liberar','fallo_solicitud'])
async def test_reserva_hitos_y_resolucion_con_mailpit(sesiones,url_base,camino):
    caso=await preparar_escenario(sesiones,url_base)
    async with sesiones() as session,session.begin():
        await session.execute(update(PacienteModel).where(PacienteModel.id==caso.pacientes[1]).values(email='paciente@example.test'))
    settings=configuracion(smtp_host=os.environ['SMTP_TEST_HOST'],smtp_port=int(os.environ['SMTP_TEST_PORT']),smtp_starttls=False)
    if camino=='fallo_solicitud':
        settings.smtp_port=1
    barrido=EjecutarBarrido(sesiones,caso.reloj,DespacharNotificacion(sesiones,caso.reloj,EnviadorSMTP(settings),settings),settings)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app),base_url='http://test') as client, httpx.AsyncClient(base_url=os.environ['MAILPIT_API_URL'],trust_env=False) as mailbox:
        await mailbox.delete('/api/v1/messages')
        reserva=await client.post('/api/v1/turnos',headers=caso.headers(),json=caso.payload())
        assert reserva.status_code==201
        tid=reserva.json()['id']
        caso.reloj.fijar(INICIO-timedelta(hours=48))
        await barrido.ejecutar(1)
        if camino=='confirmar':
            mensajes=(await mailbox.get('/api/v1/messages')).json()['messages']
            cuerpos=[(await mailbox.get('/api/v1/message/'+item['ID'])).json()['Text'] for item in mensajes]
            solicitud=next(cuerpo for cuerpo in cuerpos if '#token=' in cuerpo)
            raw=solicitud.split('#token=')[1].strip()
            resultado=await client.post('/api/v1/turnos/confirmar-por-enlace',json={'token':raw})
            assert resultado.status_code==200 and resultado.json()=={'turno_id':tid,'estado':'confirmado'}
            assert (await client.post('/api/v1/turnos/confirmar-por-enlace',json={'token':raw})).status_code==400
        settings.smtp_port=int(os.environ['SMTP_TEST_PORT'])
        caso.reloj.fijar(INICIO-timedelta(hours=24))
        await barrido.ejecutar(1)
        mensajes=(await mailbox.get('/api/v1/messages')).json()['messages']
        cuerpos=[(await mailbox.get('/api/v1/message/'+item['ID'])).json()['Text'] for item in mensajes]
        recordatorio=next(cuerpo for cuerpo in cuerpos if 'Recordatorio' in cuerpo)
        assert ('liberado' in recordatorio)==(camino=='liberar')
        assert ('Confirmá' in recordatorio)==(camino!='confirmar')
        caso.reloj.fijar(INICIO-timedelta(hours=12))
        await barrido.ejecutar(1)
        async with sesiones() as session:
            turno=await session.get(TurnoModel,tid)
            esperado={'confirmar':'confirmado','liberar':'liberado','fallo_solicitud':'pendiente'}[camino]
            assert turno.estado==esperado
            assert (turno.marcado_sin_confirmar_en is not None)==(camino=='fallo_solicitud')
        if camino=='liberar':
            # The same slot is bookable again: the exclusion no longer includes the released row.
            nueva=await client.post('/api/v1/turnos',headers=caso.headers(),json=caso.payload())
            assert nueva.status_code==201
        if camino=='fallo_solicitud':
            lista=await client.get('/api/v1/turnos?sin_confirmar=true',headers=caso.headers())
            assert [item['id'] for item in lista.json()]==[tid]
            assert (await client.post(f'/api/v1/turnos/{tid}/confirmar',headers=caso.headers())).status_code==200
            assert (await client.get('/api/v1/turnos?sin_confirmar=true',headers=caso.headers())).json()==[]
