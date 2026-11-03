import asyncio
from datetime import timedelta
from urllib.parse import parse_qs, urlsplit
import pytest
from sqlalchemy import select, func

from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import UsuarioModel, PacienteModel, TokenUsuarioModel
from app.infrastructure.db.models import RefreshTokenModel
from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel
from app.domain.services.auth_crypto import verificar_password, calcular_token_hash
from tests.integration.test_core_models import crear_consultorio_ejemplo, AHORA
from tests.integration.test_limites_cuenta import config

pytestmark = pytest.mark.integration


def datos(index=1):
    return dict(nombre='Ana', apellido='Paz', telefono='11223344',
                email=f'persona{index}@example.test', dni='30123456',
                nombre_usuario=f'persona{index}', password='password123',
                obra_social=None, acepta_aviso_privacidad=True,
                aviso_privacidad_version='2026-10-borrador')


async def preparar(sesiones):
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.commit()


async def test_registro_crea_ficha_cuenta_y_verificacion_atomica(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    await preparar(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        nid = await service.registrar(1, **datos())
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel))
        patient = await session.scalar(select(PacienteModel))
        token = await session.scalar(select(TokenUsuarioModel))
        mail = await session.get(NotificacionModel, nid)
        assert user.rol == 'paciente' and not user.email_verificado
        assert user.aviso_privacidad_aceptado_en == AHORA
        assert user.aviso_privacidad_version == '2026-10-borrador'
        assert verificar_password('password123', user.password_hash)
        assert patient.usuario_id == user.id and patient.dni == '30123456'
        assert mail.tipo == 'verificacion_email'
        raw = parse_qs(urlsplit(mail.mensaje.splitlines()[-1]).fragment)['token'][0]
        assert token.token_hash == calcular_token_hash(raw)
        assert raw != token.token_hash
        assert not await session.scalar(select(func.count()).select_from(SolicitudVinculacionModel))


async def test_dni_repetido_concurrente_crea_una_ficha_y_una_solicitud(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    await preparar(sesiones)
    async def register(index):
        async with sesiones() as session:
            return await ServicioCuentas(session, RelojSimulado(AHORA), config()).registrar(1, **datos(index))
    result = await asyncio.gather(register(1), register(2))
    assert all(isinstance(nid, int) for nid in result)
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(PacienteModel)) == 1
        assert await session.scalar(select(func.count()).select_from(UsuarioModel)) == 2
        assert await session.scalar(select(func.count()).select_from(SolicitudVinculacionModel)) == 1
        mails = (await session.scalars(select(NotificacionModel))).all()
        assert all(mail.tipo == 'verificacion_email' for mail in mails)
        assert all('30123456' not in mail.mensaje for mail in mails)


@pytest.mark.parametrize('values', [dict(acepta_aviso_privacidad=False),
                                  dict(aviso_privacidad_version='vieja')])
async def test_registro_rechaza_consentimiento_invalido_sin_escrituras(sesiones, values):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    await preparar(sesiones)
    data = datos() | values
    async with sesiones() as session:
        with pytest.raises(ErrorCuenta) as error:
            await ServicioCuentas(session, RelojSimulado(AHORA), config()).registrar(1, **data)
        assert error.value.status_code == 422
    async with sesiones() as session:
        for model in (UsuarioModel, PacienteModel, SolicitudVinculacionModel, NotificacionModel):
            assert await session.scalar(select(func.count()).select_from(model)) == 0


async def token_correo(sesiones, tipo='verificacion_email'):
    async with sesiones() as session:
        mail = await session.scalar(select(NotificacionModel).where(NotificacionModel.tipo==tipo).order_by(NotificacionModel.id.desc()))
        return parse_qs(urlsplit(mail.mensaje.splitlines()[-1]).fragment)['token'][0]


async def registrar_cuenta(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    await preparar(sesiones)
    async with sesiones() as session:
        await ServicioCuentas(session, RelojSimulado(AHORA), config()).registrar(1, **datos())
    return await token_correo(sesiones)


async def test_verificacion_consume_token_y_rechaza_reuso(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    token = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.verificar_email(token)
        with pytest.raises(ErrorCuenta):
            await service.verificar_email(token)
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel))
        saved = await session.scalar(select(TokenUsuarioModel))
        assert user.email_verificado
        assert user.email_verificado_en == AHORA
        assert saved.usado_en == AHORA


@pytest.mark.parametrize('kind', ['inexistente', 'vencido', 'otro_proposito'])
async def test_verificar_rechaza_tokens_invalidos_sin_cambiar_cuenta(sesiones, kind):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    token = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        row = await session.scalar(select(TokenUsuarioModel))
        if kind == 'vencido':
            row.expira_en = AHORA
        elif kind == 'otro_proposito':
            row.tipo = 'recuperar_password'
        await session.commit()
        with pytest.raises(ErrorCuenta):
            await ServicioCuentas(session, RelojSimulado(AHORA), config()).verificar_email('desconocido' if kind == 'inexistente' else token)
    async with sesiones() as session:
        assert not await session.scalar(select(UsuarioModel.email_verificado))


async def test_verificacion_concurrente_usa_consultorio_del_token(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    token = await registrar_cuenta(sesiones)
    async def verify():
        async with sesiones() as session:
            try:
                await ServicioCuentas(session, RelojSimulado(AHORA), config().model_copy(update={'consultorio_activo_id':999})).verificar_email(token)
                return True
            except ErrorCuenta:
                return False
    assert sorted(await asyncio.gather(verify(), verify())) == [False, True]


async def test_recuperar_password_solo_cuenta_verificada_y_limite_durable(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    token = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config(account_email_limit=1))
        assert await service.recuperar_password(1, 'persona1@example.test') is None
        assert await service.recuperar_password(1, 'inexistente@example.test') is None
        await service.verificar_email(token)
        assert await service.recuperar_password(1, ' PERSONA1@EXAMPLE.TEST ') is not None
        assert await service.recuperar_password(1, 'persona1@example.test') is None
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(NotificacionModel).where(NotificacionModel.tipo=='recuperacion_password')) == 1


async def test_reenvio_generico_y_limites_por_tipo(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    token = await registrar_cuenta(sesiones)
    reloj = RelojSimulado(AHORA)
    async with sesiones() as session:
        service = ServicioCuentas(session, reloj, config(account_email_limit=2))
        assert await service.reenviar_verificacion(1, 'desconocido@example.test') is None
        assert await service.reenviar_verificacion(2, 'persona1@example.test') is None
        assert await service.reenviar_verificacion(1, 'persona1@example.test') is not None
        assert await service.reenviar_verificacion(1, 'persona1@example.test') is None
        reloj.avanzar(timedelta(minutes=16))
        assert await service.reenviar_verificacion(1, 'persona1@example.test') is not None
        await service.verificar_email(token)
        assert await service.reenviar_verificacion(1, 'persona1@example.test') is None


async def test_restablecimiento_cambia_hash_consume_y_revoca_refresh(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    token = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.verificar_email(token)
        await service.recuperar_password(1, 'persona1@example.test')
        user = await session.scalar(select(UsuarioModel))
        session.add(RefreshTokenModel(consultorio_id=1, usuario_id=user.id,
            token_hash='refresh_hash', expira_en=AHORA+timedelta(days=1), creado_en=AHORA))
        await session.commit()
    raw = await token_correo(sesiones, 'recuperacion_password')
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config().model_copy(update={'consultorio_activo_id':999}))
        await service.restablecer_password(raw, 'password_nueva')
        with pytest.raises(ErrorCuenta):
            await service.restablecer_password(raw, 'tercera_clave')
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel))
        assert verificar_password('password_nueva', user.password_hash)
        assert await session.scalar(select(RefreshTokenModel.revocado_en)) == AHORA


@pytest.mark.parametrize('kind', ['inexistente', 'vencido', 'verificacion'])
async def test_restablecer_no_cambia_con_token_invalido(sesiones, kind):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    verify = await registrar_cuenta(sesiones)
    raw = verify
    if kind == 'vencido':
        async with sesiones() as session:
            row = await session.scalar(select(TokenUsuarioModel))
            row.tipo = 'recuperar_password'
            row.expira_en = AHORA
            await session.commit()
    async with sesiones() as session:
        with pytest.raises(ErrorCuenta):
            await ServicioCuentas(session, RelojSimulado(AHORA), config()).restablecer_password('invalid' if kind=='inexistente' else raw, 'otra_password')
    async with sesiones() as session:
        assert verificar_password('password123', await session.scalar(select(UsuarioModel.password_hash)))


async def test_registro_conflicto_revierte_toda_escritura(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    await registrar_cuenta(sesiones)
    async with sesiones() as session:
        with pytest.raises(ErrorCuenta) as error:
            await ServicioCuentas(session, RelojSimulado(AHORA), config()).registrar(1, **datos())
        assert error.value.status_code == 409
        assert await session.scalar(select(func.count()).select_from(UsuarioModel)) == 1


async def test_cambiar_password_exige_actual_y_cambia_hash(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    from app.domain.entities.auth import Principal, RolUsuario
    await registrar_cuenta(sesiones)
    async with sesiones() as session:
        uid = await session.scalar(select(UsuarioModel.id))
        principal = Principal(uid, 1, RolUsuario.PACIENTE)
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        with pytest.raises(ErrorCuenta):
            await service.cambiar_password(principal, 'incorrecta', 'nueva_clave')
        await service.cambiar_password(principal, 'password123', 'nueva_clave')
    async with sesiones() as session:
        assert verificar_password('nueva_clave', await session.scalar(select(UsuarioModel.password_hash)))


async def test_reset_concurrente_no_revoca_sesiones_de_otra_cuenta(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    verify = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.verificar_email(verify)
        await service.registrar(1, **datos(2))
        await service.recuperar_password(1, 'persona1@example.test')
        users = (await session.scalars(select(UsuarioModel).order_by(UsuarioModel.id))).all()
        for user in users:
            session.add(RefreshTokenModel(consultorio_id=1, usuario_id=user.id,
                token_hash=f'refresh_{user.id}', expira_en=AHORA+timedelta(days=1), creado_en=AHORA))
        await session.commit()
    token = await token_correo(sesiones, 'recuperacion_password')
    async def reset(password):
        async with sesiones() as session:
            try:
                await ServicioCuentas(session, RelojSimulado(AHORA), config()).restablecer_password(token, password)
                return True
            except ErrorCuenta:
                return False
    assert sorted(await asyncio.gather(reset('nueva_clave1'), reset('nueva_clave2'))) == [False, True]
    async with sesiones() as session:
        users = (await session.scalars(select(UsuarioModel).order_by(UsuarioModel.id))).all()
        refreshes = (await session.scalars(select(RefreshTokenModel).order_by(RefreshTokenModel.usuario_id))).all()
        assert refreshes[0].revocado_en == AHORA
        assert refreshes[1].revocado_en is None
        assert verificar_password('password123', users[1].password_hash)


async def test_actualizar_contacto_reverifica_e_invalida_enlace_anterior(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    from app.domain.entities.auth import Principal, RolUsuario
    old = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        uid = await session.scalar(select(UsuarioModel.id))
        principal = Principal(uid, 1, RolUsuario.PACIENTE)
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.verificar_email(old)
        assert await service.actualizar_cuenta(principal, '5551234', None) is None
        assert await service.actualizar_cuenta(principal, None, ' PERSONA1@EXAMPLE.TEST ') is None
        nid = await service.actualizar_cuenta(principal, '5559999', 'nuevo@example.test')
        assert isinstance(nid, int)
        with pytest.raises(ErrorCuenta):
            await service.verificar_email(old)
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel))
        patient = await session.scalar(select(PacienteModel))
        assert user.email == patient.email == 'nuevo@example.test'
        assert patient.telefono == '5559999'
        assert not user.email_verificado and user.email_verificado_en is None
    new = await token_correo(sesiones)
    async with sesiones() as session:
        await ServicioCuentas(session, RelojSimulado(AHORA), config()).verificar_email(new)


async def test_actualizar_correo_duplicado_revierte_contacto_y_no_crea_mensaje(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    from app.domain.entities.auth import Principal, RolUsuario
    await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.registrar(1, **datos(2))
        first = await session.scalar(select(UsuarioModel).where(UsuarioModel.nombre_usuario=='persona1'))
        with pytest.raises(ErrorCuenta) as error:
            await service.actualizar_cuenta(Principal(first.id,1,RolUsuario.PACIENTE), 'cambiado', 'persona2@example.test')
        assert error.value.status_code == 409
    async with sesiones() as session:
        patient = await session.scalar(select(PacienteModel))
        assert patient.telefono == '11223344'
        assert patient.email == 'persona1@example.test'
        assert await session.scalar(select(func.count()).select_from(NotificacionModel)) == 2


async def test_actualizar_cuenta_sin_ficha_no_toca_ficha_ajena(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    from app.domain.entities.auth import Principal, RolUsuario
    await registrar_cuenta(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.registrar(1, **datos(2))
        uid = await session.scalar(select(UsuarioModel.id).where(UsuarioModel.nombre_usuario=='persona2'))
        assert await service.actualizar_cuenta(Principal(uid,1,RolUsuario.PACIENTE), None, 'sin-ficha@example.test') is not None
        with pytest.raises(ErrorCuenta):
            await service.actualizar_cuenta(Principal(uid,999,RolUsuario.PACIENTE), None, 'ataque@example.test')
    async with sesiones() as session:
        assert await session.scalar(select(PacienteModel.email)) == 'persona1@example.test'
        assert await session.scalar(select(UsuarioModel.email).where(UsuarioModel.id==uid)) == 'sin-ficha@example.test'


async def test_limite_correo_concurrente_no_programa_mas_del_maximo(sesiones):
    from app.application.services.cuentas import ServicioCuentas
    token = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        await ServicioCuentas(session, RelojSimulado(AHORA), config()).verificar_email(token)
    async def request():
        async with sesiones() as session:
            return await ServicioCuentas(session, RelojSimulado(AHORA), config(account_email_limit=1)).recuperar_password(1, 'persona1@example.test')
    result = await asyncio.gather(request(), request(), request())
    assert len([nid for nid in result if nid is not None]) == 1


async def test_cambio_correo_invalida_enlaces_pendientes_del_correo_anterior(sesiones):
    from app.application.services.cuentas import ServicioCuentas, ErrorCuenta
    from app.domain.entities.auth import Principal, RolUsuario
    original = await registrar_cuenta(sesiones)
    async with sesiones() as session:
        await ServicioCuentas(session, RelojSimulado(AHORA), config()).reenviar_verificacion(1, 'persona1@example.test')
    second = await token_correo(sesiones)
    async with sesiones() as session:
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.verificar_email(second)
        await service.recuperar_password(1, 'persona1@example.test')
    recovery = await token_correo(sesiones, 'recuperacion_password')
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel))
        service = ServicioCuentas(session, RelojSimulado(AHORA), config())
        await service.actualizar_cuenta(Principal(user.id,1,RolUsuario.PACIENTE), None, 'nuevo@example.test')
        with pytest.raises(ErrorCuenta):
            await service.verificar_email(original)
        with pytest.raises(ErrorCuenta):
            await service.restablecer_password(recovery, 'password_ajena')
