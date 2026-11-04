import pytest
from sqlalchemy import select, update

from app.application.services.cuentas import ErrorCuenta, ServicioCuentas, actualizar_contacto_transaccional
from app.domain.entities.auth import Principal, RolUsuario
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.cuentas import RepositorioCuentas
from app.infrastructure.db.models import PacienteModel, RefreshTokenModel, TokenUsuarioModel, UsuarioModel
from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration


async def contacto_preparado(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    uid = escenario.usuarios[1, "paciente"]
    pid = escenario.pacientes[1]
    async with sesiones() as sesion:
        await sesion.execute(update(UsuarioModel).where(UsuarioModel.id == uid).values(
            email_verificado=True, email_verificado_en=AHORA,
        ))
        await sesion.execute(update(PacienteModel).where(PacienteModel.id == pid).values(
            usuario_id=uid, email="paciente1@example.test", telefono="1100000000",
        ))
        sesion.add(TokenUsuarioModel(
            consultorio_id=1, usuario_id=uid, tipo="verificar_email", token_hash="a" * 64,
            expira_en=AHORA.replace(year=2027), creado_en=AHORA,
        ))
        sesion.add(RefreshTokenModel(
            consultorio_id=1, usuario_id=uid, token_hash="c" * 64,
            expira_en=AHORA.replace(year=2027), creado_en=AHORA,
        ))
        await sesion.commit()
    return escenario, Principal(uid, 1, RolUsuario.PACIENTE), pid


async def test_contacto_propio_comparte_transaccion_y_reverifica_correo(sesiones, url_base):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    async with sesiones() as sesion:
        nid = await actualizar_contacto_transaccional(
            RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
            principal, telefono="1199999999", email=" NUEVO@EXAMPLE.TEST ",
            paciente_id_esperado=pid,
        )
        async with sesiones() as otra:
            assert await otra.scalar(select(UsuarioModel.email).where(
                UsuarioModel.id == principal.usuario_id)) == "paciente1@example.test"
        await sesion.commit()
    async with sesiones() as sesion:
        usuario = await sesion.get(UsuarioModel, principal.usuario_id)
        ficha = await sesion.get(PacienteModel, pid)
        notificacion = await sesion.get(NotificacionModel, nid)
        anterior = await sesion.scalar(select(TokenUsuarioModel).where(TokenUsuarioModel.token_hash == "a" * 64))
        assert usuario.email == ficha.email == "nuevo@example.test"
        assert usuario.email_verificado is False
        assert usuario.email_verificado_en is None
        assert ficha.telefono == "1199999999"
        assert anterior.usado_en == AHORA
        assert notificacion.tipo == "verificacion_email"
        assert notificacion.estado == "programada"
        assert notificacion.usuario_id == principal.usuario_id


@pytest.mark.parametrize("vinculada,esperado", [(True, -1), (False, None)])
async def test_contacto_rechaza_ficha_que_ya_no_es_la_vigente(sesiones, url_base, vinculada, esperado):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    if not vinculada:
        async with sesiones() as sesion:
            await sesion.execute(update(PacienteModel).where(PacienteModel.id == pid).values(usuario_id=None))
            await sesion.commit()
    async with sesiones() as sesion:
        with pytest.raises(ErrorCuenta) as rechazo:
            await actualizar_contacto_transaccional(
                RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
                principal, None, "otro@example.test", paciente_id_esperado=esperado or pid,
            )
        assert rechazo.value.status_code == 404
        await sesion.rollback()
    async with sesiones() as sesion:
        assert await sesion.scalar(select(UsuarioModel.email).where(
            UsuarioModel.id == principal.usuario_id)) == "paciente1@example.test"
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


async def test_contacto_de_cuenta_sin_ficha_conserva_contrato_c05(sesiones, url_base):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    async with sesiones() as sesion:
        await sesion.execute(update(PacienteModel).where(PacienteModel.id == pid).values(usuario_id=None))
        await sesion.commit()
        nid = await actualizar_contacto_transaccional(
            RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
            principal, None, "sin-ficha@example.test",
        )
        await sesion.commit()
    async with sesiones() as sesion:
        assert await sesion.scalar(select(UsuarioModel.email).where(
            UsuarioModel.id == principal.usuario_id)) == "sin-ficha@example.test"
        assert (await sesion.get(PacienteModel, pid)).email == "paciente1@example.test"
        assert await sesion.get(NotificacionModel, nid) is not None


@pytest.mark.parametrize("telefono,email", [("1188888888", None), (None, " PACIENTE1@EXAMPLE.TEST ")])
async def test_contacto_sin_cambiar_correo_no_reverifica(sesiones, url_base, telefono, email):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    async with sesiones() as sesion:
        nid = await actualizar_contacto_transaccional(
            RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
            principal, telefono, email, paciente_id_esperado=pid,
        )
        await sesion.commit()
    assert nid is None
    async with sesiones() as sesion:
        assert (await sesion.get(UsuarioModel, principal.usuario_id)).email_verificado is True
        assert (await sesion.get(PacienteModel, pid)).telefono == (telefono or "1100000000")
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
        assert (await sesion.scalar(select(TokenUsuarioModel).where(
            TokenUsuarioModel.token_hash == "a" * 64))).usado_en is None


async def test_email_de_cuenta_ocupado_es_conflicto_sin_efectos(sesiones, url_base):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    async with sesiones() as sesion:
        with pytest.raises(ErrorCuenta) as rechazo:
            await actualizar_contacto_transaccional(
                RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
                principal, "1199999999", "recepcion1@example.test", paciente_id_esperado=pid,
            )
        assert rechazo.value.status_code == 409
        await sesion.rollback()
    async with sesiones() as sesion:
        usuario = await sesion.get(UsuarioModel, principal.usuario_id)
        ficha = await sesion.get(PacienteModel, pid)
        assert usuario.email == ficha.email == "paciente1@example.test"
        assert usuario.email_verificado is True
        assert ficha.telefono == "1100000000"
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
        refresh = await sesion.scalar(select(RefreshTokenModel).where(
            RefreshTokenModel.token_hash == "c" * 64))
        assert refresh.revocado_en is None
        assert refresh.reemplazado_por_id is None


async def test_wrapper_c05_revierte_y_deja_la_sesion_utilizable_al_conflicto(sesiones, url_base):
    escenario, principal, _ = await contacto_preparado(sesiones, url_base)
    async with sesiones() as sesion:
        with pytest.raises(ErrorCuenta) as rechazo:
            await ServicioCuentas(sesion, escenario.reloj, escenario.app.state.settings).actualizar_cuenta(
                principal, None, "recepcion1@example.test",
            )
        assert rechazo.value.status_code == 409
        assert await sesion.scalar(select(UsuarioModel.email).where(
            UsuarioModel.id == principal.usuario_id)) == "paciente1@example.test"


async def test_fallo_del_caller_revierte_contacto_y_verificacion(sesiones, url_base):
    escenario, principal, pid = await contacto_preparado(sesiones, url_base)
    with pytest.raises(RuntimeError, match="cuerpo controlado"):
        async with sesiones() as sesion, sesion.begin():
            await actualizar_contacto_transaccional(
                RepositorioCuentas(sesion), escenario.reloj, escenario.app.state.settings,
                principal, None, "rollback@example.test", paciente_id_esperado=pid,
            )
            raise RuntimeError("cuerpo controlado")
    async with sesiones() as sesion:
        assert await sesion.scalar(select(UsuarioModel.email).where(
            UsuarioModel.id == principal.usuario_id)) == "paciente1@example.test"
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
