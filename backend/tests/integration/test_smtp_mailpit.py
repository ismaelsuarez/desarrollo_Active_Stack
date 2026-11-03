"""Recepción SMTP real; requiere Mailpit y no elimina mensajes ajenos."""

import asyncio
import os
import uuid

import httpx
import pytest

from app.core.config import Settings
from app.domain.ports.correo import EnviadorCorreo
from app.infrastructure.correo.plantillas import correo_cuenta
from app.infrastructure.correo.smtp import EnviadorSMTP

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('tipo,ruta', [
    ('verificacion_email', '/verificar-email#token='),
    ('recuperacion_password', '/restablecer-password#token='),
])
async def test_smtp_entrega_plantilla_de_cuenta_en_mailpit(tipo, ruta):
    identificador = uuid.uuid4().hex
    destinatario = f'cuenta-{identificador}@example.test'
    settings = Settings(
        database_url='postgresql+asyncpg://test@localhost/unused',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1,
        smtp_host=os.environ.get('SMTP_TEST_HOST', '127.0.0.1'),
        smtp_port=int(os.environ.get('SMTP_TEST_PORT', '11025')),
        smtp_starttls=False, smtp_user=None, smtp_password=None,
        smtp_from='Consultorio de prueba <consultorio@example.test>',
    )
    asunto, cuerpo = correo_cuenta(tipo, identificador, 'https://turnos.example.test')
    enviador: EnviadorCorreo = EnviadorSMTP(settings)
    await enviador.enviar(destinatario, asunto, cuerpo)

    api = os.environ.get('MAILPIT_API_URL', 'http://127.0.0.1:18025')
    async with httpx.AsyncClient(base_url=api, trust_env=False, timeout=5) as client:
        mensaje_id = None
        for intento in range(30):
            listado = await client.get('/api/v1/messages', params={'limit': 1000})
            listado.raise_for_status()
            encontrado = next((mensaje for mensaje in listado.json()['messages']
                               if any(para['Address'] == destinatario for para in mensaje['To'])), None)
            if encontrado:
                mensaje_id = encontrado['ID']
                break
            await asyncio.sleep(0.05)
        assert mensaje_id is not None, 'Mailpit no recibió el mensaje de esta prueba'
        respuesta = await client.get(f'/api/v1/message/{mensaje_id}')
        respuesta.raise_for_status()
        mensaje = respuesta.json()
    assert mensaje['Subject'] == asunto
    assert mensaje['From']['Address'] == 'consultorio@example.test'
    assert mensaje['To'][0]['Address'] == destinatario
    assert f'https://turnos.example.test{ruta}{identificador}' in mensaje['Text']
    assert mensaje['HTML'] == ''
    assert 'DNI' not in mensaje['Text']
