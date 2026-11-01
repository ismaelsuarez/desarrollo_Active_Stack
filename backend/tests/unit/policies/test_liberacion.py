from datetime import datetime, timezone
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.turno import puede_liberar_turno


def _crear_turno(estado: EstadoTurno = EstadoTurno.PENDIENTE) -> Turno:
    return Turno(
        id=1,
        consultorio_id=1,
        paciente_id=10,
        profesional_id=20,
        box_id=1,
        prestacion_id=1,
        inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
        estado=estado,
        es_sobreturno=False,
    )


def test_liberar_turno_modo_manual():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    turno = _crear_turno(EstadoTurno.PENDIENTE)

    # En modo manual, se autoriza aunque no tenga la marca de sin confirmar
    assert puede_liberar_turno(admin, turno, modo_manual=True, sin_confirmar=False) is True
    assert puede_liberar_turno(recep, turno, modo_manual=True, sin_confirmar=False) is True


def test_liberar_turno_modo_automatico_con_marca():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    turno = _crear_turno(EstadoTurno.PENDIENTE)

    # En modo automático, se autoriza SI tiene la marca de sin confirmar
    assert puede_liberar_turno(admin, turno, modo_manual=False, sin_confirmar=True) is True
    assert puede_liberar_turno(recep, turno, modo_manual=False, sin_confirmar=True) is True


def test_liberar_turno_modo_automatico_sin_marca_denegado():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    turno = _crear_turno(EstadoTurno.PENDIENTE)

    # En modo automático sin marca: denegado
    assert puede_liberar_turno(admin, turno, modo_manual=False, sin_confirmar=False) is False
    assert puede_liberar_turno(recep, turno, modo_manual=False, sin_confirmar=False) is False


def test_liberar_turno_roles_no_autorizados():
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)
    fin = Principal(5, 1, RolUsuario.ADMINISTRATIVO)
    turno = _crear_turno(EstadoTurno.PENDIENTE)

    for rol in (prof, pac, fin):
        assert puede_liberar_turno(rol, turno, modo_manual=True, sin_confirmar=True) is False


def test_liberar_turno_estado_no_pendiente_denegado():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    for estado in (EstadoTurno.CONFIRMADO, EstadoTurno.ATENDIDO, EstadoTurno.AUSENTE, EstadoTurno.CANCELADO, EstadoTurno.LIBERADO):
        turno = _crear_turno(estado)
        assert puede_liberar_turno(admin, turno, modo_manual=True, sin_confirmar=True) is False


def test_liberar_turno_casos_borde_nulos():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    turno = _crear_turno(EstadoTurno.PENDIENTE)

    assert puede_liberar_turno(None, turno, modo_manual=True, sin_confirmar=True) is False
    assert puede_liberar_turno(admin, None, modo_manual=True, sin_confirmar=True) is False
