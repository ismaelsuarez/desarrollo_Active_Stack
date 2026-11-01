from datetime import datetime, timezone
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.turno import es_dueno_de_agenda, es_titular_del_turno


def _crear_turno(paciente_id: int = 10, profesional_id: int = 20) -> Turno:
    return Turno(
        id=1,
        consultorio_id=1,
        paciente_id=paciente_id,
        profesional_id=profesional_id,
        box_id=1,
        prestacion_id=1,
        inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
        estado=EstadoTurno.PENDIENTE,
        es_sobreturno=False,
    )


def test_es_dueno_de_agenda_profesional():
    prof = Principal(usuario_id=5, consultorio_id=1, rol=RolUsuario.PROFESIONAL)
    turno = _crear_turno(profesional_id=50)

    # profesional_id coincide
    assert es_dueno_de_agenda(prof, turno, profesional_id=50) is True
    # profesional_id no coincide
    assert es_dueno_de_agenda(prof, turno, profesional_id=99) is False
    # sin profesional_id vinculado
    assert es_dueno_de_agenda(prof, turno, profesional_id=None) is False


def test_es_dueno_de_agenda_administrador_con_agenda():
    # DD-24: el administrador puede tener agenda si atiende
    admin = Principal(usuario_id=2, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)
    turno = _crear_turno(profesional_id=50)

    assert es_dueno_de_agenda(admin, turno, profesional_id=50) is True
    assert es_dueno_de_agenda(admin, turno, profesional_id=99) is False


def test_es_dueno_de_agenda_roles_sin_agenda():
    recep = Principal(usuario_id=3, consultorio_id=1, rol=RolUsuario.RECEPCION)
    paciente = Principal(usuario_id=4, consultorio_id=1, rol=RolUsuario.PACIENTE)
    turno = _crear_turno(profesional_id=50)

    assert es_dueno_de_agenda(recep, turno, profesional_id=50) is False
    assert es_dueno_de_agenda(paciente, turno, profesional_id=50) is False


def test_es_titular_del_turno_paciente():
    pac = Principal(usuario_id=100, consultorio_id=1, rol=RolUsuario.PACIENTE)
    turno = _crear_turno(paciente_id=10)

    # Coincide con ficha_vigente_id
    assert es_titular_del_turno(pac, turno, ficha_vigente_id=10) is True
    # Ficha no coincide
    assert es_titular_del_turno(pac, turno, ficha_vigente_id=20) is False
    # Cuenta sin ficha vinculada (None)
    assert es_titular_del_turno(pac, turno, ficha_vigente_id=None) is False


def test_es_titular_del_turno_solo_rol_paciente():
    prof = Principal(usuario_id=10, consultorio_id=1, rol=RolUsuario.PROFESIONAL)
    turno = _crear_turno(paciente_id=10)

    # Un profesional o admin no es "titular del turno" bajo la política de paciente
    assert es_titular_del_turno(prof, turno, ficha_vigente_id=10) is False


def test_titularidad_casos_borde_nulos():
    pac = Principal(usuario_id=100, consultorio_id=1, rol=RolUsuario.PACIENTE)
    prof = Principal(usuario_id=5, consultorio_id=1, rol=RolUsuario.PROFESIONAL)
    admin_rol = Principal(usuario_id=6, consultorio_id=1, rol=RolUsuario.ADMINISTRATIVO)
    turno = _crear_turno(paciente_id=10, profesional_id=50)

    assert es_titular_del_turno(None, turno, 10) is False
    assert es_titular_del_turno(pac, None, 10) is False
    assert es_titular_del_turno(admin_rol, turno, 10) is False

    assert es_dueno_de_agenda(None, turno, 50) is False
    assert es_dueno_de_agenda(prof, None, 50) is False
    assert es_dueno_de_agenda(admin_rol, turno, 50) is False
