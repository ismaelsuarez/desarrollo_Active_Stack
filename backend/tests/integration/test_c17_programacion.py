"""Programación transaccional de hitos WhatsApp."""
import httpx
import pytest
from datetime import timedelta
from sqlalchemy import select

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.avisos_whatsapp import RepositorioAvisosWhatsAppSQL
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from app.application.services.hitos import ProgramadorHitos
from tests.integration.c07_support import INICIO
from tests.integration.test_c16_planning import escenario, payload

pytestmark = pytest.mark.integration


async def test_reserva_sin_email_programa_hitos_whatsapp(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 201, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == respuesta.json()['id'],
            NotificacionModel.canal == 'whatsapp').order_by(NotificacionModel.programada_para))).all()
        assert [n.tipo for n in avisos] == ['solicitud_confirmacion', 'recordatorio']
        assert all(n.estado == 'programada' and n.destinatario == '5491123456789' for n in avisos)


@pytest.mark.parametrize('telefono', [None, '123'])
async def test_telefono_invalido_no_bloquea_correo(escenario, sesiones, telefono):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = telefono
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 201, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == respuesta.json()['id'],
            NotificacionModel.tipo.in_(('solicitud_confirmacion', 'recordatorio'))))).all()
        assert len(avisos) == 2 and all(n.canal == 'email' for n in avisos)


async def test_reprogramar_omite_hitos_anteriores_y_crea_nuevo_ciclo(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        assert creada.status_code == 201, creada.text
        respuesta = await cliente.patch(f"/api/v1/turnos/{creada.json()['id']}",
            headers=escenario.headers(), json={'inicio': (INICIO + timedelta(days=1)).isoformat()})
    assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo.in_(('solicitud_confirmacion', 'recordatorio')))
            .order_by(NotificacionModel.ciclo, NotificacionModel.tipo))).all()
        assert [(n.ciclo, n.estado) for n in avisos] == [(1, 'omitida'), (1, 'omitida'), (2, 'programada'), (2, 'programada')]


async def test_fallo_al_programar_whatsapp_revierte_reserva(escenario, sesiones, monkeypatch):
    async def fallar(*args, **kwargs):
        raise RuntimeError('fallo controlado')
    monkeypatch.setattr(RepositorioAvisosWhatsAppSQL, 'programar_hito', fallar)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 500
    async with sesiones() as sesion:
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


@pytest.mark.parametrize(('horas', 'esperados'), [(48, 2), (30, 1), (24, 0)])
async def test_hitos_respetan_limites_y_no_se_duplican(escenario, sesiones, horas, esperados):
    escenario.reloj.fijar(INICIO - timedelta(hours=horas))
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 201, respuesta.text
    async with UnidadDeTrabajoSQL(sesiones) as u:
        turno = await u.turnos.obtener(1, respuesta.json()['id'])
        await ProgramadorHitos().planificar(u, turno, 'crear', escenario.reloj.ahora())
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == respuesta.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo.in_(('solicitud_confirmacion', 'recordatorio'))))).all()
        assert len(avisos) == esperados
