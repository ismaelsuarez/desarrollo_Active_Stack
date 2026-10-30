from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.auth_service import (
    AuthService,
    CredencialesInvalidasError,
    EmailNoVerificadoError,
    SesionInvalidaError,
)
from app.application.services.rate_limiter import LoginRateLimiter
from app.application.services.token_service import AuthTokenService
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.domain.services.auth_crypto import hashear_password, calcular_token_hash
from app.infrastructure.db.models import ConsultorioModel, RefreshTokenModel, UsuarioModel

pytestmark = pytest.mark.integration

SECRET = "origin-hash-secret-for-auth-service-12345"
JWT_SECRET = "jwt-secret-key-32-bytes-minimum-auth-service"
AHORA = datetime(2026, 10, 30, 17, 0, 0, tzinfo=timezone.utc)


def crear_consultorio(id: int = 1) -> ConsultorioModel:
    return ConsultorioModel(
        id=id,
        nombre="Consultorio Auth",
        telefono="1122334455",
        direccion="Av. Callao 123",
        zona_horaria="America/Argentina/Buenos_Aires",
        modo_liberacion="automatico",
        horas_confirmacion=48,
        horas_recordatorio=24,
        horas_liberacion=12,
        horas_limite_paciente=24,
        minutos_granularidad=15,
        dias_anticipacion_maxima=60,
        max_turnos_activos_paciente=2,
        activo=True,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )


async def test_login_exitoso_con_usuario_y_con_email(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=30)
        sesion.add(consultorio)
        await sesion.flush()

        usuario = UsuarioModel(
            consultorio_id=30,
            nombre_usuario="recepcionista",
            email="recepcion@consultorio.com",
            password_hash=hashear_password("PasswordSegura123!"),
            rol=RolUsuario.RECEPCION.value,
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(
            sesion=sesion,
            reloj=reloj,
            token_service=token_service,
            rate_limiter=rate_limiter,
        )

        # Login con nombre_usuario
        access_tok, refresh_tok, principal = await auth_service.login(
            consultorio_id=30,
            identificador="recepcionista",
            password="PasswordSegura123!",
            client_host="192.168.1.10",
            x_forwarded_for=None,
        )
        assert access_tok is not None
        assert refresh_tok is not None
        assert principal.rol == RolUsuario.RECEPCION
        assert principal.usuario_id == usuario.id

        # Login con email en mayúsculas y espacios
        access_tok2, refresh_tok2, principal2 = await auth_service.login(
            consultorio_id=30,
            identificador="  RECEPCION@CONSULTORIO.COM  ",
            password="PasswordSegura123!",
            client_host="192.168.1.10",
            x_forwarded_for=None,
        )
        assert access_tok2 is not None
        assert principal2.usuario_id == usuario.id


async def test_login_password_incorrecta_lanza_credenciales_invalidas(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=31)
        sesion.add(consultorio)
        await sesion.flush()

        usuario = UsuarioModel(
            consultorio_id=31,
            nombre_usuario="odontologo",
            email="odontologo@consultorio.com",
            password_hash=hashear_password("ClaveCorrecta123!"),
            rol=RolUsuario.PROFESIONAL.value,
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        with pytest.raises(CredencialesInvalidasError):
            await auth_service.login(
                consultorio_id=31,
                identificador="odontologo",
                password="ClaveErronea123!",
                client_host="192.168.1.10",
                x_forwarded_for=None,
            )


async def test_login_usuario_inexistente_lanza_credenciales_invalidas(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=32)
        sesion.add(consultorio)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        with pytest.raises(CredencialesInvalidasError):
            await auth_service.login(
                consultorio_id=32,
                identificador="usuario_fantasma",
                password="CualquierPassword123!",
                client_host="192.168.1.10",
                x_forwarded_for=None,
            )


async def test_login_paciente_sin_verificar_tras_password_correcta(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=33)
        sesion.add(consultorio)
        await sesion.flush()

        paciente = UsuarioModel(
            consultorio_id=33,
            nombre_usuario="paciente_nuevo",
            email="paciente@test.com",
            password_hash=hashear_password("ClavePaciente123!"),
            rol=RolUsuario.PACIENTE.value,
            email_verificado=False,
            aviso_privacidad_aceptado_en=AHORA,
            aviso_privacidad_version="1.0",
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(paciente)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        # 1. Contraseña correcta pero no verificado -> EmailNoVerificadoError (403)
        with pytest.raises(EmailNoVerificadoError):
            await auth_service.login(
                consultorio_id=33,
                identificador="paciente_nuevo",
                password="ClavePaciente123!",
                client_host="192.168.1.10",
                x_forwarded_for=None,
            )

        # 2. Contraseña incorrecta para el mismo paciente sin verificar -> CredencialesInvalidasError (no revela rol ni estado)
        with pytest.raises(CredencialesInvalidasError):
            await auth_service.login(
                consultorio_id=33,
                identificador="paciente_nuevo",
                password="ClaveIncorrecta!",
                client_host="192.168.1.10",
                x_forwarded_for=None,
            )


async def test_refresh_rotacion_exitosa(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=34)
        sesion.add(consultorio)
        await sesion.flush()

        usuario = UsuarioModel(
            consultorio_id=34,
            nombre_usuario="admin34",
            email="admin34@consultorio.com",
            password_hash=hashear_password("PasswordSegura123!"),
            rol=RolUsuario.ADMINISTRADOR.value,
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        _, raw_refresh, _ = await auth_service.login(
            consultorio_id=34,
            identificador="admin34",
            password="PasswordSegura123!",
            client_host="192.168.1.10",
            x_forwarded_for=None,
        )

        # Rotar
        nuevo_access, nuevo_refresh, principal = await auth_service.refresh(raw_refresh)
        assert nuevo_access is not None
        assert nuevo_refresh is not None
        assert nuevo_refresh != raw_refresh
        assert principal.usuario_id == usuario.id

        # El token viejo quedó marcado con reemplazado_por_id y revocado_en
        viejo_hash = calcular_token_hash(raw_refresh)
        viejo_db = await sesion.scalar(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == viejo_hash))
        assert viejo_db.reemplazado_por_id is not None
        assert viejo_db.revocado_en is not None


async def test_refresh_reuso_de_token_revoca_todas_las_sesiones(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=35)
        sesion.add(consultorio)
        await sesion.flush()

        usuario = UsuarioModel(
            consultorio_id=35,
            nombre_usuario="admin35",
            email="admin35@consultorio.com",
            password_hash=hashear_password("PasswordSegura123!"),
            rol=RolUsuario.ADMINISTRADOR.value,
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        _, token_original, _ = await auth_service.login(
            consultorio_id=35,
            identificador="admin35",
            password="PasswordSegura123!",
            client_host="192.168.1.10",
            x_forwarded_for=None,
        )

        # Primera rotación válida
        _, token_rotado, _ = await auth_service.refresh(token_original)

        # Intento de reusar el token original (ataque de repetición)
        with pytest.raises(SesionInvalidaError):
            await auth_service.refresh(token_original)

        # Todas las sesiones del usuario deben haber quedado revocadas, incluido el token_rotado
        rotado_hash = calcular_token_hash(token_rotado)
        rotado_db = await sesion.scalar(select(RefreshTokenModel).where(RefreshTokenModel.token_hash == rotado_hash))
        assert rotado_db.revocado_en is not None


async def test_logout_revoca_refresh_token(sesiones: async_sessionmaker[AsyncSession]):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        consultorio = crear_consultorio(id=36)
        sesion.add(consultorio)
        await sesion.flush()

        usuario = UsuarioModel(
            consultorio_id=36,
            nombre_usuario="admin36",
            email="admin36@consultorio.com",
            password_hash=hashear_password("PasswordSegura123!"),
            rol=RolUsuario.ADMINISTRADOR.value,
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()

        rate_limiter = LoginRateLimiter(sesion=sesion, reloj=reloj, origin_hash_secret=SECRET)
        token_service = AuthTokenService(reloj=reloj, secret_key=JWT_SECRET)
        auth_service = AuthService(sesion=sesion, reloj=reloj, token_service=token_service, rate_limiter=rate_limiter)

        _, raw_refresh, _ = await auth_service.login(
            consultorio_id=36,
            identificador="admin36",
            password="PasswordSegura123!",
            client_host="192.168.1.10",
            x_forwarded_for=None,
        )

        await auth_service.logout(raw_refresh)

        # Intentar refrescar con el token deslogueado debe fallar
        with pytest.raises(SesionInvalidaError):
            await auth_service.refresh(raw_refresh)
