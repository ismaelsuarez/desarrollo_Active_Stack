import pytest
from pydantic import ValidationError

from app.api.v1.schemas.auth import (
    LoginRequest,
    MensajeResponse,
    TokenResponse,
    UsuarioPerfilResponse,
)


def test_login_request_valido():
    req = LoginRequest(identificador="admin", password="password123")
    assert req.identificador == "admin"
    assert req.password == "password123"


def test_login_request_rechaza_campos_extra():
    with pytest.raises(ValidationError):
        LoginRequest(identificador="admin", password="password123", extra="no-permitido")  # type: ignore[call-arg]


def test_login_request_rechaza_strings_vacios():
    with pytest.raises(ValidationError):
        LoginRequest(identificador="", password="password123")
    with pytest.raises(ValidationError):
        LoginRequest(identificador="admin", password="")


def test_token_response():
    resp = TokenResponse(access_token="jwt.token.string")
    assert resp.access_token == "jwt.token.string"
    assert resp.token_type == "bearer"


def test_token_response_rechaza_campos_extra():
    with pytest.raises(ValidationError):
        TokenResponse(access_token="jwt.token.string", refresh_token="no-debe-estar-en-body")  # type: ignore[call-arg]


def test_usuario_perfil_response():
    perfil = UsuarioPerfilResponse(
        id=1,
        consultorio_id=1,
        nombre_usuario="admin",
        email="admin@consultorio.com",
        rol="administrador",
        email_verificado=True,
    )
    assert perfil.id == 1
    assert perfil.nombre_usuario == "admin"
    assert perfil.rol == "administrador"
    # No expone campos personales ni médicos ni claves
    assert not hasattr(perfil, "password_hash")
    assert not hasattr(perfil, "dni")


def test_usuario_perfil_response_rechaza_campos_extra():
    with pytest.raises(ValidationError):
        UsuarioPerfilResponse(
            id=1,
            consultorio_id=1,
            nombre_usuario="admin",
            email="admin@consultorio.com",
            rol="administrador",
            email_verificado=True,
            dni="12345678",  # type: ignore[call-arg]
        )


def test_mensaje_response():
    msg = MensajeResponse(mensaje="Operación exitosa")
    assert msg.mensaje == "Operación exitosa"
