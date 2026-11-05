"""Rebanada pública y autogestión con correo de verificación SMTP/Mailpit real."""
import asyncio
import os
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


async def test_public_to_verified_booking_and_self_service_with_real_mailpit(sesiones, url_base, caplog):
    escenario = await preparar_escenario(sesiones, url_base)
    settings = escenario.app.state.settings
    settings.smtp_host = os.environ.get('SMTP_TEST_HOST', '127.0.0.1')
    settings.smtp_port = int(os.environ.get('SMTP_TEST_PORT', '11025'))
    settings.smtp_starttls = False
    settings.smtp_user = None
    settings.smtp_password = None
    settings.smtp_from = 'Consultorio <consultorio@example.test>'
    nombre = f'cuenta{uuid4().hex[:16]}'
    email, password, dni = f'{nombre}@example.test', 'Password-sintetica-123', '88776655'
    api = os.environ.get('MAILPIT_API_URL', 'http://127.0.0.1:18025')
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as cliente:
        catalogo = await cliente.get('/api/v1/publico/prestaciones')
        assert catalogo.status_code == 200
        prestaciones = catalogo.json()
        assert prestaciones[0]['duracion_min'] == 30
        consulta = {'profesional_id': escenario.profesionales[1], 'prestacion_id': escenario.prestaciones[1],
                    'fecha': INICIO.date().isoformat()}
        disponible = await cliente.get('/api/v1/publico/disponibilidad', params=consulta)
        assert disponible.status_code == 200
        assert any(i['inicio'] == INICIO.isoformat() for i in disponible.json())
        aviso = await cliente.get('/api/v1/publico/aviso-privacidad')
        assert aviso.status_code == 200
        registro = await cliente.post('/api/v1/auth/registro', json={
            'nombre': 'Paciente', 'apellido': 'Sintético', 'dni': dni,
            'telefono': '1155554444', 'email': email, 'nombre_usuario': nombre,
            'password': password, 'acepta_aviso_privacidad': True,
            'aviso_privacidad_version': aviso.json()['version'],
        })
        assert registro.status_code == 201, registro.text
        async with httpx.AsyncClient(base_url=api, trust_env=False) as correo:
            mensaje_id = None
            for _ in range(30):
                respuesta = await correo.get('/api/v1/messages', params={'limit': 1000})
                respuesta.raise_for_status()
                mensaje = next((m for m in respuesta.json()['messages'] if any(p['Address'] == email for p in m['To'])), None)
                if mensaje:
                    mensaje_id = mensaje['ID']
                    break
                await asyncio.sleep(0.05)
            assert mensaje_id is not None, 'Falta correo SMTP real de verificación'
            cuerpo = (await correo.get(f'/api/v1/message/{mensaje_id}')).json()['Text']
        token = parse_qs(urlsplit(cuerpo.splitlines()[-1]).fragment)['token'][0]
        assert dni not in cuerpo and password not in cuerpo
        ingreso = await cliente.post('/api/v1/auth/login', json={'identificador': nombre, 'password': password})
        assert ingreso.status_code == 403
        verificado = await cliente.post('/api/v1/auth/verificar-email', json={'token': token})
        assert verificado.status_code == 200
        ingreso = await cliente.post('/api/v1/auth/login', json={'identificador': nombre, 'password': password})
        assert ingreso.status_code == 200, ingreso.text
        headers = {'Authorization': f'Bearer {ingreso.json()["access_token"]}'}
        payload = {'profesional_id': escenario.profesionales[1], 'prestacion_id': escenario.prestaciones[1], 'inicio': INICIO.isoformat()}
        anonimo = await cliente.post('/api/v1/turnos', json=payload)
        assert anonimo.status_code == 401
        creado = await cliente.post('/api/v1/turnos', headers=headers, json=payload)
        assert creado.status_code == 201, creado.text
        turno_id = creado.json()['id']
        listado = await cliente.get('/api/v1/turnos', headers=headers)
        assert listado.status_code == 200
        assert [t['id'] for t in listado.json()] == [turno_id]
        assert (await cliente.get(f'/api/v1/turnos/{turno_id}', headers=escenario.headers('paciente'))).status_code == 404
        confirmado = await cliente.post(f'/api/v1/turnos/{turno_id}/confirmar', headers=headers, json={})
        assert confirmado.status_code == 200, confirmado.text
        assert confirmado.json()['estado'] == 'confirmado'
        nuevo_inicio = INICIO + timedelta(hours=1)
        movido = await cliente.patch(f'/api/v1/turnos/{turno_id}', headers=headers, json={'inicio': nuevo_inicio.isoformat()})
        assert movido.status_code == 200, movido.text
        assert datetime.fromisoformat(movido.json()['inicio']) == nuevo_inicio
        assert movido.json()['ciclo_confirmacion'] == 2
        cancelado = await cliente.post(f'/api/v1/turnos/{turno_id}/cancelar', headers=headers, json={})
        assert cancelado.status_code == 200, cancelado.text
        assert cancelado.json()['estado'] == 'cancelado'
        libre = await cliente.get('/api/v1/publico/disponibilidad', params=consulta)
        assert any(i['inicio'] == nuevo_inicio.isoformat() for i in libre.json())
    async with sesiones() as sesion:
        assert await sesion.scalar(text('SELECT count(*) FROM turno')) == 1
        assert (await sesion.execute(text('SELECT accion FROM turno_historial ORDER BY id'))).scalars().all() == ['crear', 'confirmar', 'reprogramar', 'cancelar']
        # C16 preserves facts and omits both generations of obsolete milestones.
        comunicaciones=(await sesion.execute(text("SELECT tipo,ciclo,estado FROM notificacion WHERE tipo <> 'verificacion_email' ORDER BY tipo,ciclo"))).all()
        assert comunicaciones == [
            ('cancelacion_por_paciente',2,'programada'),
            ('recordatorio',1,'omitida'), ('recordatorio',2,'omitida'),
            ('resumen_reserva',1,'programada'),
            ('solicitud_confirmacion',1,'omitida'), ('solicitud_confirmacion',2,'omitida'),
        ]
        assert await sesion.scalar(text("SELECT count(*) FROM notificacion WHERE estado='enviada'")) == 1
    assert all(privado not in caplog.text for privado in [email, password, dni, token])
