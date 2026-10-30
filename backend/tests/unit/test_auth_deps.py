from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from app.api.deps import (
    consultorio_sin_token,
    requiere_rol,
    usuario_actual,
)
from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import ConsultorioModel

AHORA = datetime(2026, 10, 30, 18, 0, 0, tzinfo=timezone.utc)
SECRET = "jwt-secret-key-for-auth-deps-testing-32b"


def test_usuario_actual_token_valido():
    reloj = RelojSimulado(AHORA)
    token_service = AuthTokenService(reloj=reloj, secret_key=SECRET)
    principal = Principal(usuario_id=1, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)
    token = token_service.emitir_access_token(principal)

    resultado = usuario_actual(token=token, token_service=token_service)
    assert resultado == principal


def test_usuario_actual_sin_token_lanza_401():
    reloj = RelojSimulado(AHORA)
    token_service = AuthTokenService(reloj=reloj, secret_key=SECRET)

    with pytest.raises(HTTPException) as error:
        usuario_actual(token=None, token_service=token_service)
    assert error.value.status_code == 401


def test_usuario_actual_token_invalido_lanza_401():
    reloj = RelojSimulado(AHORA)
    token_service = AuthTokenService(reloj=reloj, secret_key=SECRET)

    with pytest.raises(HTTPException) as error:
        usuario_actual(token="token-invalido", token_service=token_service)
    assert error.value.status_code == 401


def test_requiere_rol_permite_rol_autorizado():
    dependencia = requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION)
    principal = Principal(usuario_id=1, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)

    autorizado = dependencia(principal=principal)
    assert autorizado == principal


def test_requiere_rol_deniega_rol_no_autorizado_con_403():
    dependencia = requiere_rol(RolUsuario.ADMINISTRADOR)
    principal = Principal(usuario_id=1, consultorio_id=1, rol=RolUsuario.PROFESIONAL)

    with pytest.raises(HTTPException) as error:
        dependencia(principal=principal)
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_consultorio_sin_token_activo():
    settings = MagicMock(spec=Settings)
    settings.consultorio_activo_id = 1

    consultorio = ConsultorioModel(
        id=1,
        nombre="Consultorio Norte",
        telefono="123",
        direccion="Calle 1",
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

    sesion = AsyncMock()
    sesion.scalar.return_value = consultorio

    resultado = await consultorio_sin_token(settings=settings, sesion=sesion)
    assert resultado.id == 1
    assert resultado.activo is True


@pytest.mark.asyncio
async def test_consultorio_sin_token_inactivo_o_inexistente_lanza_503():
    settings = MagicMock(spec=Settings)
    settings.consultorio_activo_id = 1

    # Inexistente
    sesion = AsyncMock()
    sesion.scalar.return_value = None
    with pytest.raises(HTTPException) as error:
        await consultorio_sin_token(settings=settings, sesion=sesion)
    assert error.value.status_code == 503

    # Inactivo
    consultorio_inactivo = MagicMock(spec=ConsultorioModel)
    consultorio_inactivo.activo = False
    sesion.scalar.return_value = consultorio_inactivo
    with pytest.raises(HTTPException) as error:
        await consultorio_sin_token(settings=settings, sesion=sesion)
    assert error.value.status_code == 503
