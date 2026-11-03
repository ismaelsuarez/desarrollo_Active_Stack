import asyncio
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, update

from app.core.config import Settings
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel
from tests.integration.test_core_models import crear_consultorio_ejemplo

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


class CorreoGrabado:
    def __init__(self):
        self.mensajes = []

    async def enviar(self, destinatario, asunto, cuerpo):
        self.mensajes.append((destinatario, asunto, cuerpo))


def configuracion(**overrides):
    return Settings(database_url='postgresql+asyncpg://postgres@localhost/test',
                    jwt_secret_key='j' * 32, origin_hash_secret='o' * 32,
                    app_env='test', consultorio_activo_id=1, **overrides)


async def preparar(sesiones, **overrides):
    async with sesiones() as session:
        clinic = await session.get(ConsultorioModel, 1)
        if clinic is None:
            session.add(crear_consultorio_ejemplo())
            await session.flush()
        values = dict(consultorio_id=1, tipo='verificacion_email', canal='email',
                      estado='programada', destinatario='cuenta@example.test',
                      mensaje='Verificá tu correo', programada_para=AHORA,
                      intentos=0)
        values.update(overrides)
        row = NotificacionModel(**values)
        session.add(row)
        await session.commit()
        return row.id


async def leer(sesiones, identifier):
    async with sesiones() as session:
        return await session.get(NotificacionModel, identifier)


async def test_despacho_confirma_reclamacion_antes_de_enviar(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones)

    class Observador(CorreoGrabado):
        async def enviar(self, destinatario, asunto, cuerpo):
            row = await leer(sesiones, identifier)
            assert row.estado == 'enviando'
            assert row.intentos == 1
            assert row.reclamada_en == AHORA
            # A separate transaction can take the row lock during transport.
            async with sesiones() as session:
                locked = await session.scalar(select(NotificacionModel).where(
                    NotificacionModel.id == identifier).with_for_update(nowait=True))
                assert locked is not None
            await super().enviar(destinatario, asunto, cuerpo)

    sender = Observador()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    assert await dispatcher.ejecutar(1, identifier) is True
    row = await leer(sesiones, identifier)
    assert row.estado == 'enviada'
    assert row.enviada_en == AHORA
    assert row.reclamada_en is None
    assert sender.mensajes[0][0] == 'cuenta@example.test'
    assert sender.mensajes[0][2] == 'Verificá tu correo'


async def test_dos_despachos_concurrentes_envian_una_sola_vez(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones)
    started, finish = asyncio.Event(), asyncio.Event()

    class Lento(CorreoGrabado):
        async def enviar(self, *args):
            started.set()
            await finish.wait()
            await super().enviar(*args)

    sender = Lento()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    first = asyncio.create_task(dispatcher.ejecutar(1, identifier))
    await asyncio.wait_for(started.wait(), 3)
    try:
        assert await dispatcher.ejecutar(1, identifier) is False
    finally:
        finish.set()
        assert await first is True
    assert len(sender.mensajes) == 1
    assert (await leer(sesiones, identifier)).intentos == 1


@pytest.mark.parametrize('previos, esperado', [(0, 'programada'), (2, 'fallida')])
async def test_fallo_de_transporte_reintenta_o_agota_sin_secretos(sesiones, previos, esperado, caplog):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, intentos=previos)

    class Fallido:
        async def enviar(self, *args):
            raise ConnectionError('password=top-secret cuenta@example.test')

    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), Fallido(), configuracion())
    assert await dispatcher.ejecutar(1, identifier) is False
    row = await leer(sesiones, identifier)
    assert row.estado == esperado
    assert row.reclamada_en is None
    assert row.intentos == previos + 1
    assert row.ultimo_error == 'ConnectionError'
    assert 'top-secret' not in caplog.text
    assert 'cuenta@example.test' not in caplog.text


@pytest.mark.parametrize('age, enviado', [(119, False), (120, False), (121, True)])
async def test_reclamacion_se_reenvia_solo_si_es_mas_vieja_que_ttl(sesiones, age, enviado):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, estado='enviando', intentos=1,
                               reclamada_en=AHORA - timedelta(seconds=age))
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    assert await dispatcher.ejecutar(1, identifier) is enviado
    row = await leer(sesiones, identifier)
    assert row.intentos == (2 if enviado else 1)
    assert len(sender.mensajes) == int(enviado)


@pytest.mark.parametrize('state', ['programada', 'enviando'])
async def test_intentos_agotados_no_vuelven_a_enviar(sesiones, state):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, estado=state, intentos=3,
                               reclamada_en=AHORA - timedelta(seconds=121) if state == 'enviando' else None)
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    assert await dispatcher.ejecutar(1, identifier) is False
    row = await leer(sesiones, identifier)
    assert row.estado == 'fallida'
    assert row.reclamada_en is None
    assert row.intentos == 3
    assert sender.mensajes == []


@pytest.mark.parametrize('state, claim, sent, esperado', [
    ('enviando', AHORA - timedelta(seconds=120), None, False),
    ('enviando', AHORA - timedelta(seconds=121), None, True),
    ('enviada', None, AHORA - timedelta(days=1), True),
    ('enviada', None, AHORA, False),
])
async def test_cupo_cuenta_cuenta_solo_envios_del_dia_y_reclamaciones_vigentes(
        sesiones, state, claim, sent, esperado):
    from app.application.services.notificaciones import DespacharNotificacion
    await preparar(sesiones, estado=state, reclamada_en=claim, enviada_en=sent)
    identifier = await preparar(sesiones)
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion(email_daily_limit=5, email_daily_limit_account=1))
    assert await dispatcher.ejecutar(1, identifier) is esperado
    assert (await leer(sesiones, identifier)).intentos == int(esperado)


async def test_cupo_usa_dia_del_consultorio_y_se_reabre_a_medianoche(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    # 02:00 UTC still belongs to the previous Buenos Aires calendar day.
    ahora = datetime(2026, 11, 3, 2, tzinfo=timezone.utc)
    await preparar(sesiones, estado='enviada', enviada_en=ahora - timedelta(hours=4))
    identifier = await preparar(sesiones, programada_para=ahora)
    reloj, sender = RelojSimulado(ahora), CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, reloj, sender,
                                      configuracion(email_daily_limit=2, email_daily_limit_account=1))
    assert await dispatcher.ejecutar(1, identifier) is False
    reloj.avanzar(timedelta(hours=1))
    assert await dispatcher.ejecutar(1, identifier) is True


@pytest.mark.parametrize('anteriores, alerta', [(2, False), (3, True)])
async def test_alerta_al_alcanzar_ochenta_por_ciento(sesiones, caplog, anteriores, alerta):
    from app.application.services.notificaciones import DespacharNotificacion
    for _ in range(anteriores):
        await preparar(sesiones, tipo='resumen_reserva', estado='enviada', enviada_en=AHORA)
    identifier = await preparar(sesiones, tipo='resumen_reserva')
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion(email_daily_limit=5, email_daily_limit_account=2))
    assert await dispatcher.ejecutar(1, identifier)
    assert ('cupo_correo_alerta' in caplog.text) is alerta
    assert 'cuenta@example.test' not in caplog.text


@pytest.mark.parametrize('tipo, esperado', [('verificacion_email', 'fallida'),
                                         ('vinculacion_rechazada', 'omitida')])
async def test_resolucion_sin_envio_no_se_frena_por_tope_total(sesiones, tipo, esperado):
    from app.application.services.notificaciones import DespacharNotificacion
    for _ in range(2):
        await preparar(sesiones, tipo='resumen_reserva', estado='enviada', enviada_en=AHORA)
    identifier = await preparar(sesiones, tipo=tipo, estado='enviando', intentos=3,
                               reclamada_en=AHORA - timedelta(seconds=121))
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion(email_daily_limit=2, email_daily_limit_account=1))
    assert await dispatcher.ejecutar(1, identifier) is False
    row = await leer(sesiones, identifier)
    assert row.estado == esperado
    assert row.reclamada_en is None
    assert row.intentos == 3
    assert sender.mensajes == []


async def test_cupo_cuenta_reserva_capacidad_para_turnos(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion
    for _ in range(2):
        await preparar(sesiones, estado='enviada', enviada_en=AHORA, intentos=1)
    account = await preparar(sesiones)
    appointment = await preparar(sesiones, tipo='resumen_reserva')
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion(email_daily_limit=5, email_daily_limit_account=2))
    assert await dispatcher.ejecutar(1, account) is False
    assert await dispatcher.ejecutar(1, appointment) is True
    row = await leer(sesiones, account)
    assert row.estado == 'programada'
    assert row.intentos == 0
    assert row.reclamada_en is None
    assert len(sender.mensajes) == 1


@pytest.mark.parametrize('state', ['programada', 'enviando'])
async def test_tope_total_no_reclama_nuevos_ni_vencidos(sesiones, state):
    from app.application.services.notificaciones import DespacharNotificacion
    for _ in range(2):
        await preparar(sesiones, estado='enviada', enviada_en=AHORA, tipo='resumen_reserva')
    old_claim = AHORA - timedelta(seconds=121) if state == 'enviando' else None
    identifier = await preparar(sesiones, estado=state, reclamada_en=old_claim, intentos=1)
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion(email_daily_limit=2, email_daily_limit_account=1))
    assert await dispatcher.ejecutar(1, identifier) is False
    row = await leer(sesiones, identifier)
    assert row.estado == state
    assert row.intentos == 1
    assert row.reclamada_en == old_claim
    assert sender.mensajes == []


@pytest.mark.parametrize('falla_primero', [False, True])
async def test_resultado_tardio_no_pisa_segunda_reclamacion(sesiones, caplog, falla_primero):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones)
    reloj = RelojSimulado(AHORA)
    started, finish = asyncio.Event(), asyncio.Event()

    class PrimeroLento(CorreoGrabado):
        def __init__(self):
            super().__init__()
            self.calls = 0

        async def enviar(self, *args):
            self.calls += 1
            if self.calls == 1:
                started.set()
                await finish.wait()
                if falla_primero:
                    raise ConnectionError('secreto no registrable')
            await super().enviar(*args)

    sender = PrimeroLento()
    dispatcher = DespacharNotificacion(sesiones, reloj, sender, configuracion())
    first = asyncio.create_task(dispatcher.ejecutar(1, identifier))
    await asyncio.wait_for(started.wait(), 3)
    try:
        reloj.avanzar(timedelta(seconds=121))
        assert await dispatcher.ejecutar(1, identifier) is True
    finally:
        finish.set()
        assert await first is False
    row = await leer(sesiones, identifier)
    assert row.estado == 'enviada'
    assert row.intentos == 2
    assert row.enviada_en == reloj.ahora()
    assert row.reclamada_en is None
    assert 'reclamacion_perdida' in caplog.text


async def test_caida_tras_envio_conserva_reclamacion_y_permite_duplicado(sesiones):
    from app.application.services.notificaciones import DespacharNotificacion

    class Caida(BaseException):
        pass

    class EnviadoAntesDeCaer(CorreoGrabado):
        async def enviar(self, *args):
            await super().enviar(*args)
            raise Caida()

    identifier = await preparar(sesiones)
    reloj, sender = RelojSimulado(AHORA), EnviadoAntesDeCaer()
    with pytest.raises(Caida):
        await DespacharNotificacion(sesiones, reloj, sender, configuracion()).ejecutar(1, identifier)
    row = await leer(sesiones, identifier)
    assert row.estado == 'enviando'
    assert row.reclamada_en == AHORA
    reloj.avanzar(timedelta(seconds=121))
    retry = CorreoGrabado()
    assert await DespacharNotificacion(sesiones, reloj, retry, configuracion()).ejecutar(1, identifier)
    assert len(sender.mensajes) + len(retry.mensajes) == 2
    assert (await leer(sesiones, identifier)).intentos == 2


@pytest.mark.parametrize('state', ['programada', 'enviando'])
async def test_rechazo_no_verificado_se_omite_antes_de_intentos(sesiones, state):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, tipo='vinculacion_rechazada', estado=state,
                               intentos=3, reclamada_en=AHORA - timedelta(seconds=121)
                               if state == 'enviando' else None)
    sender = CorreoGrabado()
    assert await DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion()).ejecutar(1, identifier) is False
    row = await leer(sesiones, identifier)
    assert row.estado == 'omitida'
    assert row.reclamada_en is None
    assert row.intentos == 3
    assert sender.mensajes == []


@pytest.mark.parametrize('verified', [False, True])
async def test_rechazo_requiere_verificacion_de_cuenta_del_consultorio(sesiones, verified):
    from app.application.services.notificaciones import DespacharNotificacion
    await preparar(sesiones, estado='enviada', enviada_en=AHORA)
    async with sesiones() as session:
        usuario = UsuarioModel(consultorio_id=1, nombre_usuario='cuenta',
                               email='cuenta@example.test', password_hash='hash',
                               rol='paciente', email_verificado=verified,
                               aviso_privacidad_aceptado_en=AHORA,
                               aviso_privacidad_version='2026-10-borrador',
                               creado_en=AHORA, actualizado_en=AHORA)
        session.add(usuario)
        await session.commit()
        uid = usuario.id
    identifier = await preparar(sesiones, tipo='vinculacion_rechazada', usuario_id=uid)
    sender = CorreoGrabado()
    dispatcher = DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender, configuracion())
    assert await dispatcher.ejecutar(1, identifier) is verified
    assert (await leer(sesiones, identifier)).estado == ('enviada' if verified else 'omitida')


@pytest.mark.parametrize('tipo', ['verificacion_email', 'recuperacion_password'])
async def test_correos_cuenta_son_vigentes_sin_turno_ni_usuario(sesiones, tipo):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, tipo=tipo)
    sender = CorreoGrabado()
    assert await DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion()).ejecutar(1, identifier)
    assert len(sender.mensajes) == 1


@pytest.mark.parametrize('overrides, cid', [
    ({'programada_para': AHORA + timedelta(seconds=1)}, 1),
    ({'canal': 'whatsapp', 'estado': 'preparada'}, 1),
    ({}, 2),
])
async def test_no_despacha_futuro_whatsapp_ni_otro_consultorio(sesiones, overrides, cid):
    from app.application.services.notificaciones import DespacharNotificacion
    identifier = await preparar(sesiones, **overrides)
    sender = CorreoGrabado()
    assert await DespacharNotificacion(sesiones, RelojSimulado(AHORA), sender,
                                      configuracion()).ejecutar(cid, identifier) is False
    assert (await leer(sesiones, identifier)).intentos == 0
    assert sender.mensajes == []
