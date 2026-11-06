"""Ciclo de preparación y registro manual sobre PostgreSQL real."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.application.services.notificaciones import DespacharNotificacion
from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from tests.integration.c07_support import INICIO
from tests.integration.test_c16_planning import escenario, payload
from tests.integration.test_notificaciones import CorreoGrabado, configuracion

pytestmark = pytest.mark.integration


async def test_ciclo_prepara_consulta_marca_y_reprograma_sin_email(escenario, sesiones):
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.email = None
        paciente.telefono = '011 15 2345-6789'
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        creada = await cliente.post('/api/v1/turnos', headers=escenario.headers(), json=payload(escenario))
        assert creada.status_code == 201
        turno_id = creada.json()['id']
        escenario.reloj.fijar(INICIO - timedelta(hours=48))
        settings, correo = configuracion(), CorreoGrabado()
        barrido = EjecutarBarrido(sesiones, escenario.reloj,
            DespacharNotificacion(sesiones, escenario.reloj, correo, settings), settings)
        await barrido.ejecutar(1)
        bandeja = await cliente.get('/api/v1/notificaciones?canal=whatsapp&estado=preparada', headers=escenario.headers())
        assert bandeja.status_code == 200 and len(bandeja.json()) == 1
        identificador = bandeja.json()[0]['id']
        detalle = await cliente.get(f'/api/v1/notificaciones/{identificador}/whatsapp', headers=escenario.headers())
        assert detalle.status_code == 200 and detalle.json()['enlace_whatsapp'].startswith('https://wa.me/5491123456789?')
        marca = await cliente.post(f'/api/v1/notificaciones/{identificador}/marcar-enviada', headers=escenario.headers())
        assert marca.status_code == 200 and marca.json()['estado'] == 'enviada_manual'
        cambio = await cliente.patch(f'/api/v1/turnos/{turno_id}', headers=escenario.headers(),
            json={'inicio': (INICIO + timedelta(days=1)).isoformat()})
        assert cambio.status_code == 200, cambio.text
    async with sesiones() as sesion:
        avisos = (await sesion.scalars(select(NotificacionModel).where(
            NotificacionModel.turno_id == turno_id, NotificacionModel.canal == 'whatsapp'))).all()
        assert any(n.id == identificador and n.estado == 'enviada_manual' for n in avisos)
        assert any(n.ciclo == 1 and n.tipo == 'recordatorio' and n.estado == 'omitida' for n in avisos)
        assert any(n.ciclo == 2 and n.tipo == 'reprogramacion_por_personal' for n in avisos)
        assert any(n.ciclo == 2 and n.tipo == 'solicitud_confirmacion' for n in avisos)
    assert correo.mensajes == []
