"""Preparación durable de mensajes WhatsApp mediante el barrido."""
from datetime import timedelta
import asyncio

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.notificaciones import DespacharNotificacion
from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from tests.integration.c07_support import INICIO
from tests.integration.test_c16_planning import escenario, payload
from tests.integration.test_notificaciones import CorreoGrabado, configuracion

pytestmark = pytest.mark.integration


async def test_barrido_prepara_solicitud_sin_correo_y_es_idempotente(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        assert creada.status_code == 201, creada.text
    escenario.reloj.fijar(INICIO - timedelta(hours=48))
    settings = configuracion()
    barrido = EjecutarBarrido(sesiones, escenario.reloj,
        DespacharNotificacion(sesiones, escenario.reloj, CorreoGrabado(), settings), settings)
    await barrido.ejecutar(1)
    await barrido.ejecutar(1)
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'solicitud_confirmacion'))).all()
        assert len(avisos) == 1 and avisos[0].estado == 'preparada'
        assert avisos[0].enlace_whatsapp.startswith('https://wa.me/5491123456789?')


@pytest.mark.parametrize(('horas', 'esperado'), [(48, 'preparada'), (24, 'omitida')])
async def test_limite_y_dos_barridos_concurrentes(escenario, sesiones, horas, esperado):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '+1 212 555 1234'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        assert creada.status_code == 201
    escenario.reloj.fijar(INICIO - timedelta(hours=horas))
    settings = configuracion()
    barrido = EjecutarBarrido(sesiones, escenario.reloj,
        DespacharNotificacion(sesiones, escenario.reloj, CorreoGrabado(), settings), settings)
    await asyncio.wait_for(asyncio.gather(barrido.ejecutar(1), barrido.ejecutar(1)), 15)
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'solicitud_confirmacion'))).all()
        assert len(avisos) == 1 and avisos[0].estado == esperado


@pytest.mark.parametrize('enviada', [True, False])
async def test_recordatorio_solo_advierte_liberacion_con_correo_enviado(escenario, sesiones, enviada):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
    async with sesiones() as sesion:
        solicitud = await sesion.scalar(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'email',
            NotificacionModel.tipo == 'solicitud_confirmacion'))
        solicitud.estado = 'enviada' if enviada else 'fallida'
        await sesion.commit()
    escenario.reloj.fijar(INICIO - timedelta(hours=24))
    settings = configuracion()
    barrido = EjecutarBarrido(sesiones, escenario.reloj,
        DespacharNotificacion(sesiones, escenario.reloj, CorreoGrabado(), settings), settings)
    await barrido.ejecutar(1)
    async with sesiones() as sesion:
        recordatorio = await sesion.scalar(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'recordatorio'))
        assert recordatorio.estado == 'preparada'
        assert ('liberado' in recordatorio.mensaje) == enviada


async def test_barrido_prepara_snapshot_de_hecho_y_no_envia_correo(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        cancelada = await cliente.post(f"/api/v1/turnos/{creada.json()['id']}/cancelar", headers=escenario.headers(), json={})
        assert cancelada.status_code == 200
    settings = configuracion()
    correo = CorreoGrabado()
    barrido = EjecutarBarrido(sesiones, escenario.reloj,
        DespacharNotificacion(sesiones, escenario.reloj, correo, settings), settings)
    await barrido.ejecutar(1)
    async with sesiones() as sesion:
        aviso = await sesion.scalar(select(NotificacionModel).where(
            NotificacionModel.turno_id == creada.json()['id'], NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo == 'cancelacion_por_personal'))
        assert aviso.estado == 'preparada' and 'cancelado' in aviso.mensaje
        assert aviso.enlace_whatsapp.startswith('https://wa.me/')
    assert correo.mensajes == []


@pytest.mark.parametrize('accion', ['cancelar', 'liberar', 'reprogramar'])
async def test_cambio_omite_hitos_preparados_y_conserva_aviso_de_hecho(escenario, sesiones, accion):
    from sqlalchemy import text
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.telefono = '011 15 2345-6789'
        await sesion.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        turno_id = creada.json()['id']
        async with sesiones() as sesion:
            avisos = (await sesion.scalars(select(NotificacionModel).where(
                NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp'))).all()
            for aviso in avisos:
                aviso.estado = 'preparada'
            await sesion.commit()
        if accion == 'reprogramar':
            respuesta = await cliente.patch(f'/api/v1/turnos/{turno_id}', headers=escenario.headers(),
                json={'inicio': (INICIO + timedelta(days=1)).isoformat()})
        else:
            respuesta = await cliente.post(f'/api/v1/turnos/{turno_id}/{accion}', headers=escenario.headers(), json={})
        assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp'))).all()
        anteriores = [aviso for aviso in avisos if aviso.ciclo == 1 and aviso.tipo in ('solicitud_confirmacion', 'recordatorio')]
        assert len(anteriores) == 2 and all(aviso.estado == 'omitida' for aviso in anteriores)
        hechos = [aviso for aviso in avisos if aviso.tipo not in ('solicitud_confirmacion', 'recordatorio')]
        assert len(hechos) == 1 and hechos[0].estado == 'programada'


@pytest.mark.parametrize('primero', ['barrido', 'cancelacion'])
async def test_barrido_y_cancelacion_se_serializan(escenario, sesiones, monkeypatch, primero):
    from app.infrastructure.db.repositorios import RepositorioTurnosSQL
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        turno_id = creada.json()['id']
        escenario.reloj.fijar(INICIO - timedelta(hours=48))
        settings = configuracion()
        barrido = EjecutarBarrido(sesiones, escenario.reloj,
            DespacharNotificacion(sesiones, escenario.reloj, CorreoGrabado(), settings), settings)
        retenido, continuar = asyncio.Event(), asyncio.Event()
        if primero == 'barrido':
            original = AsyncSession.scalar
            async def interceptar(sesion, sentencia, *args, **kwargs):
                resultado = await original(sesion, sentencia, *args, **kwargs)
                if asyncio.current_task().get_name() == 'barrido-c17' and 'FROM turno' in str(sentencia) and 'FOR UPDATE' in str(sentencia):
                    retenido.set()
                    await continuar.wait()
                return resultado
            monkeypatch.setattr(AsyncSession, 'scalar', interceptar)
        else:
            original_actualizar = RepositorioTurnosSQL.actualizar
            async def interceptar_actualizacion(repo, *args, **kwargs):
                resultado = await original_actualizar(repo, *args, **kwargs)
                retenido.set()
                await continuar.wait()
                return resultado
            monkeypatch.setattr(RepositorioTurnosSQL, 'actualizar', interceptar_actualizacion)
        async def cancelar():
            return await cliente.post(f'/api/v1/turnos/{turno_id}/cancelar', headers=escenario.headers(), json={})
        if primero == 'barrido':
            primer = asyncio.create_task(barrido.whatsapp.ejecutar(1), name='barrido-c17')
        else:
            primer = asyncio.create_task(cancelar())
        await asyncio.wait_for(retenido.wait(), 5)
        segundo = asyncio.create_task(cancelar() if primero == 'barrido' else barrido.whatsapp.ejecutar(1), name='segundo-c17')
        try:
            await asyncio.sleep(0.1)
            assert not segundo.done()
        finally:
            continuar.set()
        resultados = await asyncio.wait_for(asyncio.gather(primer, segundo), 10)
        respuesta = resultados[1] if primero == 'barrido' else resultados[0]
        assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        hitos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp',
            NotificacionModel.tipo.in_(('solicitud_confirmacion', 'recordatorio'))))).all()
        assert len(hitos) == 2 and all(hito.estado == 'omitida' for hito in hitos)
