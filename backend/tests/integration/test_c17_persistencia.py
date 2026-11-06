"""Persistencia aislada por canal y snapshot de avisos WhatsApp."""
import httpx
import pytest
import asyncio
from sqlalchemy import select

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.test_c16_planning import escenario, payload

pytestmark = pytest.mark.integration


async def test_aviso_whatsapp_es_durable_sin_correo_y_no_se_duplica(escenario, sesiones):
    from app.infrastructure.db.avisos_whatsapp import RepositorioAvisosWhatsAppSQL

    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 201, respuesta.text
    turno_id = respuesta.json()['id']
    async with UnidadDeTrabajoSQL(sesiones) as u:
        turno = await u.turnos.obtener(1, turno_id)
        repo = RepositorioAvisosWhatsAppSQL(u._sesion)
        primero = await repo.programar_hecho(turno, 'liberacion', escenario.reloj.ahora())
        duplicado = await repo.programar_hecho(turno, 'liberacion', escenario.reloj.ahora())
        assert primero is not None and duplicado is None
    async with sesiones() as sesion:
        aviso = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'liberacion'))).one()
        assert aviso.estado == 'programada'
        assert aviso.destinatario == '5491123456789'
        assert '09/11/2026' in aviso.mensaje and 'liberado' in aviso.mensaje
        assert aviso.enlace_whatsapp.startswith('https://wa.me/5491123456789?')


async def test_snapshot_y_canal_email_se_conservan_y_rollback_descarta_aviso(escenario, sesiones):
    from app.infrastructure.db.avisos_whatsapp import RepositorioAvisosWhatsAppSQL

    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    assert respuesta.status_code == 201, respuesta.text
    turno_id = respuesta.json()['id']
    async with UnidadDeTrabajoSQL(sesiones) as u:
        turno = await u.turnos.obtener(1, turno_id)
        repo = RepositorioAvisosWhatsAppSQL(u._sesion)
        await repo.programar_hecho(turno, 'cancelacion_por_personal', escenario.reloj.ahora())
    with pytest.raises(RuntimeError):
        async with UnidadDeTrabajoSQL(sesiones) as u:
            turno = await u.turnos.obtener(1, turno_id)
            await RepositorioAvisosWhatsAppSQL(u._sesion).programar_hecho(
                turno, 'liberacion', escenario.reloj.ahora())
            raise RuntimeError('rollback')
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 9876-5432'
        await sesion.commit()
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id))).all()
        whatsapp = [n for n in avisos if n.canal == 'whatsapp' and n.tipo in ('cancelacion_por_personal', 'liberacion')]
        assert len(whatsapp) == 1 and whatsapp[0].tipo == 'cancelacion_por_personal'
        assert whatsapp[0].destinatario == '5491123456789'
        assert 'cancelado' in whatsapp[0].mensaje
        assert any(n.canal == 'email' for n in avisos)


async def test_programacion_concurrente_solo_persiste_un_aviso(escenario, sesiones):
    from app.infrastructure.db.avisos_whatsapp import RepositorioAvisosWhatsAppSQL

    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '+1 212 555 1234'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    turno_id = respuesta.json()['id']
    barrera = asyncio.Barrier(2)

    async def programar():
        async with UnidadDeTrabajoSQL(sesiones) as u:
            turno = await u.turnos.obtener(1, turno_id)
            await barrera.wait()
            return await RepositorioAvisosWhatsAppSQL(u._sesion).programar_hecho(
                turno, 'liberacion', escenario.reloj.ahora())

    resultados = await asyncio.wait_for(asyncio.gather(programar(), programar()), 5)
    assert sum(resultado is not None for resultado in resultados) == 1
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'liberacion'))).all()
        assert len(avisos) == 1 and avisos[0].destinatario == '12125551234'
