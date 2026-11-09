from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from app.api.deps import get_reloj
from app.core.config import Settings
from app.domain.ports.reloj import RelojSimulado
from app.domain.entities.auth import Principal, RolUsuario
from app.application.services.token_service import AuthTokenService
from app.main import create_app
from app.infrastructure.db.models import ConsultorioModel
from sqlalchemy import update
from sqlalchemy import func, select
from app.infrastructure.db.models import PacienteModel, UsuarioModel
from app.infrastructure.db.account_models import IntentoRegistroModel, NotificacionModel, SolicitudVinculacionModel
from tests.integration.test_core_models import crear_consultorio_ejemplo

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def cuenta_app(sesiones, url_base):
    async with sesiones() as sesion:
        sesion.add(crear_consultorio_ejemplo())
        await sesion.commit()
    settings = Settings(
        database_url=url_base, jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
        app_env='test', consultorio_activo_id=1, cookie_secure=False,
    )
    app = create_app(settings)
    app.state.session_factory = sesiones
    app.dependency_overrides[get_reloj] = lambda: RelojSimulado(AHORA)
    return app


async def test_aviso_publico_devuelve_version_y_datos_del_consultorio(cuenta_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.get('/api/v1/publico/aviso-privacidad')
    assert respuesta.status_code == 200
    aviso = respuesta.json()
    assert aviso['version'] == '2026-10-borrador'
    assert 'Consultorio Centro' in aviso['texto']
    assert 'Av. Corrientes 1234' in aviso['texto']
    assert '1122334455' in aviso['texto']


@pytest.mark.parametrize('ambiente,direccion,estado', [
    ('production', None, 503),
    ('production', 'Calle completa 123', 200),
    ('development', None, 200),
])
async def test_aviso_incompleto_no_se_publica_en_produccion(cuenta_app, sesiones, ambiente, direccion, estado):
    cuenta_app.state.settings.app_env = ambiente
    async with sesiones() as sesion:
        await sesion.execute(update(ConsultorioModel).where(ConsultorioModel.id == 1).values(direccion=direccion))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.get('/api/v1/publico/aviso-privacidad')
    assert respuesta.status_code == estado
    if ambiente == 'development':
        assert '[DOMICILIO]' in respuesta.json()['texto']
    elif estado == 200:
        assert '[' not in respuesta.json()['texto']


async def test_validacion422_no_devuelve_password_ni_input_crudo(cuenta_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/auth/login', json={'password': 'password-privada', 'dni': '12345678'})
    assert respuesta.status_code == 422
    assert 'password-privada' not in respuesta.text
    assert '12345678' not in respuesta.text
    assert respuesta.json()['detail']
    assert all(set(error) == {'loc', 'msg', 'type'} for error in respuesta.json()['detail'])


def datos_registro(**cambios):
    return {
        'nombre': 'Ana', 'apellido': 'Paz', 'telefono': '1144445555',
        'email': 'ana@example.test', 'dni': '12345678', 'nombre_usuario': 'ana',
        'password': 'password-privada', 'acepta_aviso_privacidad': True,
        'aviso_privacidad_version': '2026-10-borrador', **cambios,
    }


@pytest.mark.parametrize('ruta,cuerpo', [
    ('/api/v1/auth/login', {'nombre_usuario': 'ana', 'password': 'clave', '12345678': 'x'}),
    ('/api/v1/auth/registro', datos_registro(**{'12345678': 'x'})),
])
async def test_validacion_no_refleja_nombre_de_campo_extra(cuenta_app, ruta, cuerpo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.post(ruta, json=cuerpo)
    assert respuesta.status_code == 422
    assert '12345678' not in respuesta.text
    assert any(error['type'] == 'extra_forbidden' for error in respuesta.json()['detail'])


class CorreoCapturado:
    def __init__(self):
        self.mensajes = []

    async def enviar(self, destinatario, asunto, cuerpo):
        self.mensajes.append((destinatario, asunto, cuerpo))


@pytest.mark.parametrize('ruta,nombre', [
    ('/api/v1/auth/reenviar-verificacion', 'reenviar_verificacion'),
    ('/api/v1/auth/recuperar-password', 'recuperar_password'),
])
async def test_solicitudes_correo_limitadas_por_origen_sin_enumeracion(cuenta_app, ruta, nombre):
    from app.api.v1.routers.cuentas import get_servicio_cuentas

    ejecutar = AsyncMock(return_value=None)
    cuenta_app.dependency_overrides[get_servicio_cuentas] = lambda: SimpleNamespace(**{nombre: ejecutar})
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        for numero in range(10):
            respuesta = await cliente.post(ruta, json={'email': f'paciente{numero}@example.test'})
            assert respuesta.status_code == 200
            assert respuesta.json() == {'mensaje': 'Si corresponde, recibirás un correo'}
        rechazadas = [await cliente.post(ruta, json={'email': direccion})
                      for direccion in ('existente@example.test', 'inexistente@example.test')]
    assert all(respuesta.status_code == 429 for respuesta in rechazadas)
    assert rechazadas[0].json() == rechazadas[1].json()
    assert all(int(respuesta.headers['retry-after']) > 0 for respuesta in rechazadas)
    assert ejecutar.await_count == 10


async def test_solicitudes_correo_comparten_cuota_sin_afectar_registro(cuenta_app):
    from app.api.v1.routers.cuentas import get_servicio_cuentas

    cuenta_app.state.settings.account_request_limit_per_origin = 1
    cuenta_app.dependency_overrides[get_servicio_cuentas] = lambda: SimpleNamespace(
        reenviar_verificacion=AsyncMock(return_value=None), recuperar_password=AsyncMock(return_value=None))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        primera = await cliente.post('/api/v1/auth/reenviar-verificacion', json={'email': 'a@example.test'})
        segunda = await cliente.post('/api/v1/auth/recuperar-password', json={'email': 'b@example.test'})
        registro = await cliente.post('/api/v1/auth/registro', json=datos_registro(acepta_aviso_privacidad=False))
    assert primera.status_code == 200
    assert segunda.status_code == 429
    assert registro.status_code == 422


async def test_registro_http_crea_cuenta_y_despacha_despues_del_commit(cuenta_app, sesiones):
    from app.api.v1.routers.cuentas import get_enviador_correo

    enviador = CorreoCapturado()
    cuenta_app.dependency_overrides[get_enviador_correo] = lambda: enviador
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/auth/registro', json=datos_registro())
    assert respuesta.status_code == 201
    assert respuesta.json() == {'mensaje': 'Revisá tu correo para verificar la cuenta'}
    assert len(enviador.mensajes) == 1
    assert enviador.mensajes[0][0] == 'ana@example.test'
    assert '#token=' in enviador.mensajes[0][2]
    assert 'password-privada' not in respuesta.text
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(UsuarioModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(PacienteModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(IntentoRegistroModel)) == 1
        correo = await sesion.scalar(select(NotificacionModel))
        assert correo.estado == 'enviada'
        assert correo.reclamada_en is None


@pytest.mark.parametrize('cambios', [
    {'acepta_aviso_privacidad': False}, {'aviso_privacidad_version': 'vieja'},
    {'password': 'secreto'}, {'consultorio_id': 9},
])
async def test_registro_invalido_conserva_intento_sin_crear_datos(cuenta_app, sesiones, cambios):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/auth/registro', json=datos_registro(**cambios))
    assert respuesta.status_code == 422
    assert 'password-privada' not in respuesta.text
    assert '12345678' not in respuesta.text
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(IntentoRegistroModel)) == 1
        for modelo in (UsuarioModel, PacienteModel, SolicitudVinculacionModel, NotificacionModel):
            assert await sesion.scalar(select(func.count()).select_from(modelo)) == 0


async def test_registro_limite429_no_agrega_otro_intento(cuenta_app, sesiones):
    cuenta_app.state.settings.registration_limit_per_origin = 1
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        primera = await cliente.post('/api/v1/auth/registro', json=datos_registro(acepta_aviso_privacidad=False))
        segunda = await cliente.post('/api/v1/auth/registro', json=datos_registro())
    assert primera.status_code == 422
    assert segunda.status_code == 429
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(IntentoRegistroModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(UsuarioModel)) == 0


async def test_registro_json_malformado_cuenta_antes_de_parsear_y_respeta_limite(cuenta_app, sesiones):
    cuenta_app.state.settings.registration_limit_per_origin = 1
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        primera = await cliente.post('/api/v1/auth/registro', content=b'{json-invalido',
                                     headers={'Content-Type': 'application/json'})
        assert primera.status_code == 422
        async with sesiones() as sesion:
            assert await sesion.scalar(select(func.count()).select_from(IntentoRegistroModel)) == 1
        segunda = await cliente.post('/api/v1/auth/registro', content=b'{json-invalido',
                                     headers={'Content-Type': 'application/json'})
        assert segunda.status_code == 429
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(IntentoRegistroModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(UsuarioModel)) == 0


async def test_registro_dni_existente_misma_respuesta_y_una_solicitud(cuenta_app, sesiones):
    from app.api.v1.routers.cuentas import get_enviador_correo

    enviador = CorreoCapturado()
    cuenta_app.dependency_overrides[get_enviador_correo] = lambda: enviador
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        primera = await cliente.post('/api/v1/auth/registro', json=datos_registro())
        segunda = await cliente.post('/api/v1/auth/registro', json=datos_registro(
            nombre_usuario='otra', email='otra@example.test'))
    assert primera.status_code == segunda.status_code == 201
    assert primera.json() == segunda.json()
    assert len(enviador.mensajes) == 2
    assert enviador.mensajes[0][1] == enviador.mensajes[1][1]
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(PacienteModel)) == 1
        assert await sesion.scalar(select(func.count()).select_from(SolicitudVinculacionModel)) == 1


def token_de_prueba(cuenta_app, rol=RolUsuario.PACIENTE):
    principal = Principal(usuario_id=7, consultorio_id=1, rol=rol)
    return AuthTokenService(RelojSimulado(AHORA), 'j' * 32).emitir_access_token(principal)


@pytest.mark.parametrize('metodo,ruta,payload,nombre,args,autenticado', [
    ('POST', '/verificar-email', {'token': 'token-privado'}, 'verificar_email', ('token-privado',), False),
    ('POST', '/reenviar-verificacion', {'email': ' ANA@EXAMPLE.TEST '}, 'reenviar_verificacion', (1, 'ana@example.test'), False),
    ('POST', '/recuperar-password', {'email': ' ANA@EXAMPLE.TEST '}, 'recuperar_password', (1, 'ana@example.test'), False),
    ('POST', '/restablecer-password', {'token': 'token-privado', 'password': 'password-nueva'}, 'restablecer_password', ('token-privado', 'password-nueva'), False),
    ('PATCH', '/cambiar-password', {'password_actual': 'password-actual', 'password_nueva': 'password-nueva'}, 'cambiar_password', ('password-actual', 'password-nueva'), True),
    ('PATCH', '/actualizar-cuenta', {'email': ' NUEVO@EXAMPLE.TEST '}, 'actualizar_cuenta', (), True),
])
async def test_endpoints_delegan_al_caso_de_uso_sin_identidad_del_cliente(
        cuenta_app, metodo, ruta, payload, nombre, args, autenticado):
    from app.api.v1.routers.cuentas import get_servicio_cuentas

    ejecutar = AsyncMock(return_value=None)
    servicio = SimpleNamespace(**{nombre: ejecutar})
    cuenta_app.dependency_overrides[get_servicio_cuentas] = lambda: servicio
    headers = {'Authorization': f'Bearer {token_de_prueba(cuenta_app)}'} if autenticado else {}
    if ruta in ('/verificar-email', '/restablecer-password'):
        # These flows must use the token's row, not the configured clinic.
        cuenta_app.state.settings.consultorio_activo_id = 99
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.request(metodo, '/api/v1/auth' + ruta, json=payload, headers=headers)
    assert respuesta.status_code == 200
    assert set(respuesta.json()) == {'mensaje'}
    assert 'token-privado' not in respuesta.text
    assert 'password-' not in respuesta.text
    if ruta == '/actualizar-cuenta':
        principal = ejecutar.call_args.args[0]
        assert principal.usuario_id == 7
        assert principal.consultorio_id == 1
        assert ejecutar.call_args.kwargs == {'telefono': None, 'email': 'nuevo@example.test'}
    elif autenticado:
        principal, *argumentos = ejecutar.call_args.args
        assert principal.usuario_id == 7
        assert tuple(argumentos) == args
    else:
        ejecutar.assert_awaited_once_with(*args)


@pytest.mark.parametrize('metodo,ruta,payload', [
    ('POST', '/registro', datos_registro()),
    ('POST', '/verificar-email', {'token': 'token-privado'}),
    ('POST', '/reenviar-verificacion', {'email': 'ana@example.test'}),
    ('POST', '/recuperar-password', {'email': 'ana@example.test'}),
    ('POST', '/restablecer-password', {'token': 'token-privado', 'password': 'password-nueva'}),
    ('PATCH', '/cambiar-password', {'password_actual': 'password-actual', 'password_nueva': 'password-nueva'}),
    ('PATCH', '/actualizar-cuenta', {'telefono': '1144445555'}),
])
async def test_todos_los_cuerpos_rechazan_consultorio_cliente_sin_eco_de_secretos(cuenta_app, metodo, ruta, payload):
    headers = {'Authorization': f'Bearer {token_de_prueba(cuenta_app)}'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.request(metodo, '/api/v1/auth' + ruta,
                                          json={**payload, 'consultorio_id': 99}, headers=headers)
    assert respuesta.status_code == 422
    assert 'token-privado' not in respuesta.text
    assert 'password-nueva' not in respuesta.text
    assert 'password-actual' not in respuesta.text
    assert '12345678' not in respuesta.text


@pytest.mark.parametrize('metodo,ruta,payload,nombre', [
    ('POST', '/verificar-email', {'token': 'token-privado'}, 'verificar_email'),
    ('POST', '/restablecer-password', {'token': 'token-privado', 'password': 'password-nueva'}, 'restablecer_password'),
    ('PATCH', '/cambiar-password', {'password_actual': 'password-actual', 'password_nueva': 'password-nueva'}, 'cambiar_password'),
    ('PATCH', '/actualizar-cuenta', {'telefono': '1144445555'}, 'actualizar_cuenta'),
])
async def test_errores_de_cuenta_preservan_codigo_y_mensaje_seguro(cuenta_app, metodo, ruta, payload, nombre):
    from app.api.v1.routers.cuentas import get_servicio_cuentas
    from app.application.services.cuentas import ErrorCuenta

    servicio = SimpleNamespace(**{nombre: AsyncMock(side_effect=ErrorCuenta(409, 'La cuenta cambió; intentá nuevamente'))})
    cuenta_app.dependency_overrides[get_servicio_cuentas] = lambda: servicio
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.request(metodo, '/api/v1/auth' + ruta, json=payload,
            headers={'Authorization': f'Bearer {token_de_prueba(cuenta_app)}'})
    assert respuesta.status_code == 409
    assert respuesta.json() == {'detail': 'La cuenta cambió; intentá nuevamente'}


@pytest.mark.parametrize('ruta,payload', [
    ('/cambiar-password', {'password_actual': 'password-actual', 'password_nueva': 'password-nueva'}),
    ('/actualizar-cuenta', {'telefono': '1144445555'}),
])
async def test_autoservicio_exige_jwt(cuenta_app, ruta, payload):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.patch('/api/v1/auth' + ruta, json=payload)
    assert respuesta.status_code == 401


@pytest.mark.parametrize('rol', [RolUsuario.ADMINISTRADOR, RolUsuario.PROFESIONAL, RolUsuario.RECEPCION, RolUsuario.ADMINISTRATIVO])
async def test_actualizar_contacto_es_solo_para_paciente(cuenta_app, rol):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.patch('/api/v1/auth/actualizar-cuenta', json={'telefono': '1144445555'},
            headers={'Authorization': f'Bearer {token_de_prueba(cuenta_app, rol)}'})
    assert respuesta.status_code == 403


async def test_fallo_smtp_no_revierte_registro_y_queda_reintentable(cuenta_app, sesiones):
    from app.api.v1.routers.cuentas import get_enviador_correo

    class CorreoFallido:
        async def enviar(self, destinatario, asunto, cuerpo):
            raise ConnectionError('recipient@example.test password-privada')

    cuenta_app.dependency_overrides[get_enviador_correo] = CorreoFallido
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.post('/api/v1/auth/registro', json=datos_registro())
    assert respuesta.status_code == 201
    async with sesiones() as sesion:
        assert await sesion.scalar(select(func.count()).select_from(UsuarioModel)) == 1
        correo = await sesion.scalar(select(NotificacionModel))
        assert correo.estado == 'programada'
        assert correo.intentos == 1
        assert correo.ultimo_error == 'ConnectionError'
        assert correo.reclamada_en is None


def token_del_correo(mensaje):
    enlace = next(line for line in mensaje[2].splitlines() if line.startswith('http'))
    return parse_qs(urlsplit(enlace).fragment)['token'][0]


async def test_flujo_http_registro_verificacion_recuperacion_y_autoservicio(cuenta_app):
    from app.api.v1.routers.cuentas import get_enviador_correo

    enviador = CorreoCapturado()
    cuenta_app.dependency_overrides[get_enviador_correo] = lambda: enviador
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        registro = await cliente.post('/api/v1/auth/registro', json=datos_registro())
        assert registro.status_code == 201
        bloqueado = await cliente.post('/api/v1/auth/login', json={
            'identificador': 'ana', 'password': 'password-privada'})
        assert bloqueado.status_code == 403
        reenviado = await cliente.post('/api/v1/auth/reenviar-verificacion', json={'email': 'ana@example.test'})
        assert reenviado.status_code == 200
        verificacion = token_del_correo(enviador.mensajes[-1])
        cuenta_app.state.settings.consultorio_activo_id = 99
        verificado = await cliente.post('/api/v1/auth/verificar-email', json={'token': verificacion})
        assert verificado.status_code == 200
        repetido = await cliente.post('/api/v1/auth/verificar-email', json={'token': verificacion})
        assert repetido.status_code == 400
        cuenta_app.state.settings.consultorio_activo_id = 1
        login = await cliente.post('/api/v1/auth/login', json={
            'identificador': 'ana', 'password': 'password-privada'})
        assert login.status_code == 200
        assert 'refresh_token' in cliente.cookies
        recuperacion = await cliente.post('/api/v1/auth/recuperar-password', json={'email': 'ana@example.test'})
        assert recuperacion.status_code == 200
        reset_token = token_del_correo(enviador.mensajes[-1])
        cuenta_app.state.settings.consultorio_activo_id = 99
        restablecido = await cliente.post('/api/v1/auth/restablecer-password', json={
            'token': reset_token, 'password': 'password-recuperada'})
        assert restablecido.status_code == 200
        refresh = await cliente.post('/api/v1/auth/refresh')
        assert refresh.status_code == 401
        cuenta_app.state.settings.consultorio_activo_id = 1
        nuevo_login = await cliente.post('/api/v1/auth/login', json={
            'identificador': 'ana', 'password': 'password-recuperada'})
        assert nuevo_login.status_code == 200
        cabeceras = {'Authorization': 'Bearer ' + nuevo_login.json()['access_token']}
        cambio = await cliente.patch('/api/v1/auth/cambiar-password', headers=cabeceras, json={
            'password_actual': 'password-recuperada', 'password_nueva': 'password-final'})
        assert cambio.status_code == 200
        contacto = await cliente.patch('/api/v1/auth/actualizar-cuenta', headers=cabeceras, json={
            'telefono': '1199998888', 'email': 'nuevo@example.test'})
        assert contacto.status_code == 200
        bloqueado_nuevo = await cliente.post('/api/v1/auth/login', json={
            'identificador': 'ana', 'password': 'password-final'})
        assert bloqueado_nuevo.status_code == 403
        nueva_verificacion = await cliente.post('/api/v1/auth/verificar-email', json={
            'token': token_del_correo(enviador.mensajes[-1])})
        assert nueva_verificacion.status_code == 200
        login_final = await cliente.post('/api/v1/auth/login', json={
            'identificador': 'nuevo@example.test', 'password': 'password-final'})
        assert login_final.status_code == 200


@pytest.mark.parametrize('ruta', ['/reenviar-verificacion', '/recuperar-password'])
async def test_solicitud_correo_responde_igual_exista_o_no(cuenta_app, ruta):
    from app.api.v1.routers.cuentas import get_enviador_correo

    enviador = CorreoCapturado()
    cuenta_app.dependency_overrides[get_enviador_correo] = lambda: enviador
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        assert (await cliente.post('/api/v1/auth/registro', json=datos_registro())).status_code == 201
        existente = await cliente.post('/api/v1/auth' + ruta, json={'email': 'ana@example.test'})
        inexistente = await cliente.post('/api/v1/auth' + ruta, json={'email': 'ausente@example.test'})
    assert existente.status_code == inexistente.status_code == 200
    assert existente.json() == inexistente.json() == {'mensaje': 'Si corresponde, recibirás un correo'}


async def test_openapi_expone_los_ocho_endpoints_y_entradas_cerradas(cuenta_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=cuenta_app), base_url='http://test') as cliente:
        respuesta = await cliente.get('/openapi.json')
    assert respuesta.status_code == 200
    esquema = respuesta.json()
    esperados = {
        '/api/v1/publico/aviso-privacidad': 'get',
        '/api/v1/auth/registro': 'post',
        '/api/v1/auth/verificar-email': 'post',
        '/api/v1/auth/reenviar-verificacion': 'post',
        '/api/v1/auth/recuperar-password': 'post',
        '/api/v1/auth/restablecer-password': 'post',
        '/api/v1/auth/cambiar-password': 'patch',
        '/api/v1/auth/actualizar-cuenta': 'patch',
    }
    for ruta, metodo in esperados.items():
        assert metodo in esquema['paths'][ruta]
    registro_schema = esquema['paths']['/api/v1/auth/registro']['post']['requestBody']['content']['application/json']['schema']
    assert registro_schema['additionalProperties'] is False
    assert 'acepta_aviso_privacidad' in registro_schema['required']
    assert registro_schema['properties']['password']['writeOnly'] is True
    for nombre in ('CorreoRequest', 'TokenRequest',
                   'RestablecerPasswordRequest', 'CambiarPasswordRequest', 'ActualizarCuentaRequest'):
        assert esquema['components']['schemas'][nombre]['additionalProperties'] is False
