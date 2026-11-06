"""Avisos WhatsApp de hechos conservados en la transacción de origen."""
import httpx
import pytest
from datetime import timedelta
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.avisos_whatsapp import RepositorioAvisosWhatsAppSQL
from tests.integration.c07_support import INICIO
from tests.integration.test_c16_planning import escenario, payload

pytestmark = pytest.mark.integration


async def test_cancelacion_personal_programa_aviso_sin_email(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        respuesta = await cliente.post(f"/api/v1/turnos/{creada.json()['id']}/cancelar", headers=escenario.headers(), json={})
    assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        aviso = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'cancelacion_por_personal'))).one()
        assert aviso.estado == 'programada' and aviso.ciclo == 1
        assert 'cancelado' in aviso.mensaje and aviso.destinatario == '5491123456789'


async def test_reprogramacion_guarda_snapshot_del_nuevo_horario(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        turno_id = creada.json()['id']
        respuesta = await cliente.patch(f'/api/v1/turnos/{turno_id}', headers=escenario.headers(),
            json={'inicio': (INICIO + timedelta(days=1)).isoformat()})
        assert respuesta.status_code == 200, respuesta.text
        respuesta = await cliente.patch(f'/api/v1/turnos/{turno_id}', headers=escenario.headers(),
            json={'inicio': (INICIO + timedelta(days=2)).isoformat()})
        assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'reprogramacion_por_personal').order_by(NotificacionModel.ciclo))).all()
        assert [aviso.ciclo for aviso in avisos] == [2, 3]
        assert '10/11/2026' in avisos[0].mensaje and '11/11/2026' in avisos[1].mensaje


async def test_error_al_programar_aviso_revierte_cancelacion(escenario, sesiones, monkeypatch):
    async def fallar(*args, **kwargs):
        raise RuntimeError('fallo controlado')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        turno_id = creada.json()['id']
        monkeypatch.setattr(RepositorioAvisosWhatsAppSQL, 'programar_hecho', fallar)
        respuesta = await cliente.post(f'/api/v1/turnos/{turno_id}/cancelar', headers=escenario.headers(), json={})
        assert respuesta.status_code == 500
        consulta = await cliente.get(f'/api/v1/turnos/{turno_id}', headers=escenario.headers())
        assert consulta.status_code == 200
        assert consulta.json()['estado'] != 'cancelado'
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id,
            NotificacionModel.tipo == 'cancelacion_por_personal'))).all()
        assert avisos == []


@pytest.mark.parametrize('telefono', [None, '123'])
async def test_cancelacion_sin_telefono_conserva_aviso_email(escenario, sesiones, telefono):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = telefono
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        respuesta = await cliente.post(f"/api/v1/turnos/{creada.json()['id']}/cancelar", headers=escenario.headers(), json={})
        assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'],
            NotificacionModel.tipo == 'cancelacion_por_personal'))).all()
        assert len(avisos) == 1 and avisos[0].canal == 'email'


async def test_liberacion_programa_aviso_whatsapp_sin_email(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        respuesta = await cliente.post(f"/api/v1/turnos/{creada.json()['id']}/liberar", headers=escenario.headers(), json={})
        assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        aviso = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'liberacion'))).one()
        assert aviso.estado == 'programada' and aviso.ciclo == 1 and 'liberado' in aviso.mensaje
