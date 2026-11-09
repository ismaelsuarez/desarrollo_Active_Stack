from datetime import datetime, timedelta, timezone
import pytest
import jwt

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.application.services.token_service import AuthTokenService, TokenError

SECRET = "jwt-secret-key-for-testing-purposes-123456"
AHORA = datetime(2026, 10, 30, 15, 0, 0, tzinfo=timezone.utc)


def test_emitir_token_con_claims_minimos_y_validados():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET, ttl_segundos=900)
    principal = Principal(usuario_id=42, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)

    token = servicio.emitir_access_token(principal)
    assert isinstance(token, str)

    # Decodificar inspeccionando claims exactos
    payload = jwt.decode(token, SECRET, algorithms=["HS256"], options={"verify_exp": False})
    assert payload["sub"] == "42"
    assert payload["consultorio_id"] == 1
    assert payload["rol"] == "administrador"
    assert "jti" in payload
    assert payload["iat"] == int(reloj.ahora().timestamp())
    assert payload["exp"] == int(reloj.ahora().timestamp()) + 900
    # Minimización de datos (RN-06): no claims personales
    assert not {"email", "nombre", "dni", "paciente_id"} & set(payload.keys())


def test_decodificar_token_valido_construye_principal():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET, ttl_segundos=900)
    principal = Principal(usuario_id=42, consultorio_id=1, rol=RolUsuario.PROFESIONAL)

    token = servicio.emitir_access_token(principal)
    resultado = servicio.decodificar_access_token(token)

    assert resultado == principal


def test_decodificar_token_expirado_segun_reloj_inyectado():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET, ttl_segundos=900)
    principal = Principal(usuario_id=42, consultorio_id=1, rol=RolUsuario.PACIENTE)

    token = servicio.emitir_access_token(principal)

    # Avanzar el reloj inyectado 16 minutos (960s > 900s)
    reloj.avanzar(timedelta(seconds=960))

    with pytest.raises(TokenError) as error:
        servicio.decodificar_access_token(token)
    assert "expirado" in str(error.value).lower()


def test_rechazo_token_firma_invalida():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET)
    servicio_otro = AuthTokenService(reloj=reloj, secret_key="otro-secreto-totalmente-distinto-32b")
    principal = Principal(usuario_id=42, consultorio_id=1, rol=RolUsuario.ADMINISTRATIVO)

    token = servicio_otro.emitir_access_token(principal)

    with pytest.raises(TokenError):
        servicio.decodificar_access_token(token)


def test_token_vence_en_el_segundo_exacto_de_expiracion():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET, ttl_segundos=900)
    principal = Principal(usuario_id=42, consultorio_id=1, rol=RolUsuario.PACIENTE)
    token = servicio.emitir_access_token(principal)

    reloj.avanzar(timedelta(seconds=899))
    assert servicio.decodificar_access_token(token) == principal
    reloj.avanzar(timedelta(seconds=1))
    with pytest.raises(TokenError):
        servicio.decodificar_access_token(token)


def test_rechazo_token_con_claims_faltantes_o_invalidos():
    reloj = RelojSimulado(AHORA)
    servicio = AuthTokenService(reloj=reloj, secret_key=SECRET)

    # Token con rol no válido
    bad_payload = {
        "sub": "42",
        "consultorio_id": 1,
        "rol": "rol_inexistente",
        "jti": "uuid-123",
        "iat": int(AHORA.timestamp()),
        "exp": int(AHORA.timestamp()) + 900,
    }
    bad_token = jwt.encode(bad_payload, SECRET, algorithm="HS256")

    with pytest.raises(TokenError):
        servicio.decodificar_access_token(bad_token)
