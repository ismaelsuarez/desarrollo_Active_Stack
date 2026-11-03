"""RN-05: password checks and session issuance serialize with reset."""
import asyncio

import pytest
from sqlalchemy import select

from app.application.services.auth_service import CredencialesInvalidasError
from app.application.services.cuentas import ServicioCuentas
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import RefreshTokenModel, UsuarioModel
from tests.integration.test_refresh_reset_race import AHORA, RESET, auth, preparar
from tests.integration.test_limites_cuenta import config

pytestmark = pytest.mark.integration


async def ingresar(servicio):
    return await servicio.login(consultorio_id=1, identificador='cuenta-race',
                                 password='password123', client_host='127.0.0.1',
                                 x_forwarded_for=None)


async def test_login_ya_validado_espera_reset_y_su_sesion_no_sobrevive(sesiones):
    await preparar(sesiones)
    limpiado, continuar = asyncio.Event(), asyncio.Event()
    async with sesiones() as login_session, sesiones() as reset_session:
        servicio = auth(login_session)
        limpiar = servicio.rate_limiter.limpiar_intentos_exitosos

        async def limpiar_y_pausar(*args, **kwargs):
            await limpiar(*args, **kwargs)
            limpiado.set()
            await continuar.wait()

        servicio.rate_limiter.limpiar_intentos_exitosos = limpiar_y_pausar
        login_task = asyncio.create_task(ingresar(servicio))
        await asyncio.wait_for(limpiado.wait(), 3)
        reset_task = asyncio.create_task(ServicioCuentas(reset_session,
            RelojSimulado(AHORA), config()).restablecer_password(RESET, 'password_nueva'))
        try:
            # Login retains the account lock even after deleting login attempts.
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(reset_task), 0.2)
        finally:
            continuar.set()
            await login_task
            await reset_task

    async with sesiones() as session:
        rows = (await session.scalars(select(RefreshTokenModel))).all()
        assert len(rows) == 2
        assert all(row.revocado_en == AHORA for row in rows)


async def test_reset_en_curso_hace_que_login_relea_y_rechace_password_anterior(sesiones):
    await preparar(sesiones)
    reset_listo, continuar_reset = asyncio.Event(), asyncio.Event()
    login_leyendo_usuario = asyncio.Event()
    async with sesiones() as reset_session, sesiones() as login_session:
        commit = reset_session.commit
        scalar = login_session.scalar

        async def confirmar_despues_de_login():
            reset_listo.set()
            await continuar_reset.wait()
            await commit()

        async def avisar_lectura(statement, *args, **kwargs):
            if any(column.get('entity') is UsuarioModel
                   for column in statement.column_descriptions):
                login_leyendo_usuario.set()
            return await scalar(statement, *args, **kwargs)

        reset_session.commit = confirmar_despues_de_login
        login_session.scalar = avisar_lectura
        reset_task = asyncio.create_task(ServicioCuentas(reset_session,
            RelojSimulado(AHORA), config()).restablecer_password(RESET, 'password_nueva'))
        await asyncio.wait_for(reset_listo.wait(), 3)
        login_task = asyncio.create_task(ingresar(auth(login_session)))
        try:
            await asyncio.wait_for(login_leyendo_usuario.wait(), 3)
        finally:
            continuar_reset.set()
            await reset_task
        with pytest.raises(CredencialesInvalidasError):
            await login_task

    async with sesiones() as session:
        rows = (await session.scalars(select(RefreshTokenModel))).all()
        assert len(rows) == 1
        assert rows[0].revocado_en == AHORA
