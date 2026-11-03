from urllib.parse import parse_qs, urlsplit
from unittest.mock import AsyncMock

import pytest

from app.infrastructure.correo.plantillas import correo_cuenta


def test_verificacion_contiene_enlace_privado_sin_datos_personales():
    asunto, cuerpo = correo_cuenta('verificacion_email', 'verificar-token', 'https://turnos.example.test')
    assert asunto == 'Verificá tu correo'
    enlace = next(line for line in cuerpo.splitlines() if line.startswith('https://'))
    url = urlsplit(enlace)
    assert url.path == '/verificar-email'
    assert url.query == ''
    assert parse_qs(url.fragment) == {'token': ['verificar-token']}
    assert 'DNI' not in cuerpo
    assert 'contraseña:' not in cuerpo


def test_recuperacion_usa_su_ruta_y_escapa_el_token_en_fragmento():
    asunto, cuerpo = correo_cuenta('recuperacion_password', 'token+con&signos', 'https://turnos.example.test/')
    assert asunto == 'Restablecé tu contraseña'
    enlace = next(line for line in cuerpo.splitlines() if line.startswith('https://'))
    url = urlsplit(enlace)
    assert url.path == '/restablecer-password'
    assert url.query == ''
    assert parse_qs(url.fragment) == {'token': ['token+con&signos']}
    assert 'DNI' not in cuerpo


def test_plantilla_rechaza_tipos_fuera_del_alcance_de_cuenta():
    with pytest.raises(ValueError, match='Tipo de correo de cuenta no soportado'):
        correo_cuenta('recordatorio', 'token', 'https://turnos.example.test')


async def test_smtp_usa_starttls_en587_y_mensaje_de_texto(monkeypatch):
    from app.core.config import Settings
    from app.infrastructure.correo.smtp import EnviadorSMTP

    settings = Settings(
        database_url='postgresql+asyncpg://test@localhost/test',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1,
        smtp_host='smtp.example.test', smtp_port=587, smtp_starttls=True,
        smtp_user='sender@example.test', smtp_password='private-password',
        smtp_from='Consultorio <sender@example.test>',
    )
    enviar = AsyncMock(return_value=({}, 'accepted'))
    monkeypatch.setattr('aiosmtplib.send', enviar)
    await EnviadorSMTP(settings).enviar('paciente@example.test', 'Verificá tu correo', 'Texto de prueba')
    mensaje = enviar.call_args.args[0]
    assert mensaje['From'] == 'Consultorio <sender@example.test>'
    assert mensaje['To'] == 'paciente@example.test'
    assert mensaje['Subject'] == 'Verificá tu correo'
    assert mensaje.get_content_type() == 'text/plain'
    assert mensaje.get_content().strip() == 'Texto de prueba'
    assert enviar.call_args.kwargs == {
        'hostname': 'smtp.example.test', 'port': 587,
        'username': 'sender@example.test', 'password': 'private-password',
        'start_tls': True, 'use_tls': False, 'timeout': 30,
    }


async def test_smtp_local_sin_tls_ni_autenticacion(monkeypatch):
    from app.core.config import Settings
    from app.infrastructure.correo.smtp import EnviadorSMTP

    settings = Settings(
        database_url='postgresql+asyncpg://test@localhost/test',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1,
        smtp_host='mailpit', smtp_port=1025, smtp_starttls=False,
        smtp_user=None, smtp_password=None,
    )
    enviar = AsyncMock(return_value=({}, 'accepted'))
    monkeypatch.setattr('aiosmtplib.send', enviar)
    await EnviadorSMTP(settings).enviar('test@example.test', 'Recuperación', 'Contenido')
    assert enviar.call_args.kwargs['port'] == 1025
    assert enviar.call_args.kwargs['start_tls'] is False
    assert enviar.call_args.kwargs['use_tls'] is False
    assert enviar.call_args.kwargs['username'] is None
    assert enviar.call_args.kwargs['password'] is None


@pytest.mark.parametrize('clase_error', ['smtp', 'conexion'])
async def test_error_smtp_no_expone_destinatario_ni_credenciales(monkeypatch, clase_error):
    import aiosmtplib
    from app.core.config import Settings
    from app.domain.ports.correo import ErrorEnvioCorreo
    from app.infrastructure.correo.smtp import EnviadorSMTP

    settings = Settings(
        database_url='postgresql+asyncpg://test@localhost/test',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1,
    )
    excepcion = aiosmtplib.SMTPException if clase_error == 'smtp' else OSError
    monkeypatch.setattr('aiosmtplib.send', AsyncMock(side_effect=excepcion(
        'recipient@example.test private-password')))
    with pytest.raises(ErrorEnvioCorreo) as error:
        await EnviadorSMTP(settings).enviar('recipient@example.test', 'Asunto', 'Cuerpo')
    assert str(error.value) == 'No se pudo enviar el correo'
    assert 'recipient@example.test' not in repr(error.value)
    assert 'private-password' not in repr(error.value)


async def test_timeout_acota_el_envio_completo(monkeypatch):
    import asyncio
    from app.core.config import Settings
    from app.domain.ports.correo import ErrorEnvioCorreo
    from app.infrastructure.correo.smtp import EnviadorSMTP

    settings = Settings(
        database_url='postgresql+asyncpg://test@localhost/test',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1, smtp_timeout_seconds=0.01,
    )

    async def envio_colgado(*args, **kwargs):
        await asyncio.Event().wait()

    monkeypatch.setattr('aiosmtplib.send', envio_colgado)
    with pytest.raises(ErrorEnvioCorreo, match='No se pudo enviar el correo'):
        await asyncio.wait_for(
            EnviadorSMTP(settings).enviar('test@example.test', 'Asunto', 'Cuerpo'),
            timeout=0.2,
        )
