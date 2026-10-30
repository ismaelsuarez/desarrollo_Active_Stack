from dataclasses import FrozenInstanceError
import pytest

from app.domain.entities.auth import Principal, RolUsuario


def test_rol_usuario_values():
    assert RolUsuario.ADMINISTRADOR == "administrador"
    assert RolUsuario.RECEPCION == "recepcion"
    assert RolUsuario.PROFESIONAL == "profesional"
    assert RolUsuario.PACIENTE == "paciente"
    assert RolUsuario.ADMINISTRATIVO == "administrativo"
    assert len(RolUsuario) == 5


def test_principal_instantiation_and_attributes():
    principal = Principal(usuario_id=10, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)
    assert principal.usuario_id == 10
    assert principal.consultorio_id == 1
    assert principal.rol == RolUsuario.ADMINISTRADOR


def test_principal_is_frozen_immutable():
    principal = Principal(usuario_id=10, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)
    with pytest.raises(FrozenInstanceError):
        principal.rol = RolUsuario.PROFESIONAL  # type: ignore[misc]
