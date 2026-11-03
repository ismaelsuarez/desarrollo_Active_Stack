"""RN-05: a refresh already in flight cannot survive password reset."""
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.application.services.auth_service import AuthService, SesionInvalidaError
from app.application.services.cuentas import ServicioCuentas
from app.application.services.rate_limiter import LoginRateLimiter
from app.application.services.token_service import AuthTokenService
from app.domain.ports.reloj import RelojSimulado
from app.domain.services.auth_crypto import calcular_token_hash, hashear_password
from app.infrastructure.db.models import RefreshTokenModel, TokenUsuarioModel, UsuarioModel
from tests.integration.test_core_models import AHORA, crear_consultorio_ejemplo
from tests.integration.test_limites_cuenta import config

pytestmark = pytest.mark.integration
REFRESH = 'refresh-original-de-prueba'
RESET = 'reset-original-de-prueba'


async def preparar(sesiones):
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.flush()
        user = UsuarioModel(consultorio_id=1, nombre_usuario='cuenta-race',
                            email='cuenta-race@example.test', rol='recepcion',
                            email_verificado=True, password_hash=hashear_password('password123'),
                            creado_en=AHORA, actualizado_en=AHORA)
        session.add(user)
        await session.flush()
        session.add(RefreshTokenModel(consultorio_id=1, usuario_id=user.id,
                    token_hash=calcular_token_hash(REFRESH), expira_en=AHORA+timedelta(days=1), creado_en=AHORA))
        session.add(TokenUsuarioModel(consultorio_id=1, usuario_id=user.id,
                    tipo='recuperar_password', token_hash=calcular_token_hash(RESET),
                    expira_en=AHORA+timedelta(minutes=30), creado_en=AHORA))
        await session.commit()


def auth(session):
    settings, reloj = config(), RelojSimulado(AHORA)
    return AuthService(session, reloj,
        AuthTokenService(reloj, settings.jwt_secret_key.get_secret_value()),
        LoginRateLimiter(session, reloj, settings.origin_hash_secret.get_secret_value()))


async def restablecer(sesiones):
    async with sesiones() as session:
        await ServicioCuentas(session, RelojSimulado(AHORA), config()).restablecer_password(RESET, 'password_nueva')


async def test_reset_entre_lectura_y_rotacion_rechaza_refresh_en_vuelo(sesiones):
    await preparar(sesiones)
    leido, continuar = asyncio.Event(), asyncio.Event()
    async with sesiones() as session:
        scalar = session.scalar
        primera = True

        async def leer_y_pausar(statement, *args, **kwargs):
            nonlocal primera
            result = await scalar(statement, *args, **kwargs)
            if primera:
                primera = False
                leido.set()
                await continuar.wait()
            return result

        session.scalar = leer_y_pausar
        task = asyncio.create_task(auth(session).refresh(REFRESH))
        await asyncio.wait_for(leido.wait(), 3)
        try:
            await restablecer(sesiones)
        finally:
            continuar.set()
        with pytest.raises(SesionInvalidaError):
            await task

    async with sesiones() as session:
        rows = (await session.scalars(select(RefreshTokenModel))).all()
        assert len(rows) == 1
        assert rows[0].revocado_en == AHORA


async def test_refresh_antes_de_reset_no_deja_sesion_rotada_activa(sesiones):
    await preparar(sesiones)
    usuario_leido, continuar = asyncio.Event(), asyncio.Event()
    reset_solicitado = asyncio.Event()
    async with sesiones() as refresh_session, sesiones() as reset_session:
        refresh_scalar = refresh_session.scalar
        reset_scalar = reset_session.scalar

        async def pausar_usuario(statement, *args, **kwargs):
            result = await refresh_scalar(statement, *args, **kwargs)
            if isinstance(result, UsuarioModel):
                usuario_leido.set()
                await continuar.wait()
            return result

        async def avisar_reset(statement, *args, **kwargs):
            reset_solicitado.set()
            return await reset_scalar(statement, *args, **kwargs)

        refresh_session.scalar = pausar_usuario
        reset_session.scalar = avisar_reset
        refresh_task = asyncio.create_task(auth(refresh_session).refresh(REFRESH))
        await asyncio.wait_for(usuario_leido.wait(), 3)
        reset_task = asyncio.create_task(ServicioCuentas(
            reset_session, RelojSimulado(AHORA), config()).restablecer_password(RESET, 'password_nueva'))
        await asyncio.wait_for(reset_solicitado.wait(), 3)
        try:
            # The account lock serializes reset after the in-flight rotation.
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(reset_task), 0.2)
        finally:
            continuar.set()
            _, nuevo_refresh, _ = await refresh_task
            await reset_task

    async with sesiones() as session:
        rows = (await session.scalars(select(RefreshTokenModel))).all()
        assert len(rows) == 2
        assert all(row.revocado_en == AHORA for row in rows)
        with pytest.raises(SesionInvalidaError):
            await auth(session).refresh(nuevo_refresh)


async def test_doble_refresh_concurrente_detecta_reuso_y_revoca_descendiente(sesiones):
    await preparar(sesiones)

    async def renovar():
        async with sesiones() as session:
            try:
                return await auth(session).refresh(REFRESH)
            except SesionInvalidaError:
                return None

    results = await asyncio.gather(renovar(), renovar())
    assert len([result for result in results if result is not None]) == 1
    async with sesiones() as session:
        rows = (await session.scalars(select(RefreshTokenModel))).all()
        assert len(rows) == 2
        assert all(row.revocado_en == AHORA for row in rows)
