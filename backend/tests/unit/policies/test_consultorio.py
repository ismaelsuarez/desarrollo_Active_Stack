from dataclasses import dataclass
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.policies.consultorio import mismo_consultorio


@dataclass(frozen=True, slots=True)
class RecursoPrueba:
    id: int
    consultorio_id: int


def test_mismo_consultorio_permite_cuando_coincide():
    user = Principal(usuario_id=1, consultorio_id=10, rol=RolUsuario.PROFESIONAL)
    recurso = RecursoPrueba(id=100, consultorio_id=10)

    assert mismo_consultorio(user, recurso) is True


def test_mismo_consultorio_deniega_cuando_difiere():
    user = Principal(usuario_id=1, consultorio_id=10, rol=RolUsuario.PROFESIONAL)
    recurso_ajeno = RecursoPrueba(id=100, consultorio_id=20)

    assert mismo_consultorio(user, recurso_ajeno) is False


def test_mismo_consultorio_deniega_casos_borde():
    user = Principal(usuario_id=1, consultorio_id=10, rol=RolUsuario.PROFESIONAL)

    assert mismo_consultorio(user, None) is False
    assert mismo_consultorio(None, RecursoPrueba(id=1, consultorio_id=10)) is False
    assert mismo_consultorio(user, object()) is False
    assert mismo_consultorio(user, RecursoPrueba(id=1, consultorio_id=None)) is False
