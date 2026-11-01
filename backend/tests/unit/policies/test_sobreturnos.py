from datetime import datetime, timezone
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.sobreturno import (
    puede_autorizar_sobreturno,
    puede_responder_sobreturno,
    sobreturno_cumple_condiciones,
)


def _crear_turno(profesional_id: int = 10, es_sobreturno: bool = True) -> Turno:
    return Turno(
        id=1,
        consultorio_id=1,
        paciente_id=10,
        profesional_id=profesional_id,
        box_id=1,
        prestacion_id=1,
        inicio=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
        estado=EstadoTurno.PENDIENTE,
        es_sobreturno=es_sobreturno,
    )


def test_puede_autorizar_sobreturno():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)
    adm_fin = Principal(5, 1, RolUsuario.ADMINISTRATIVO)

    assert puede_autorizar_sobreturno(admin) is True
    assert puede_autorizar_sobreturno(recep) is True
    assert puede_autorizar_sobreturno(prof) is False
    assert puede_autorizar_sobreturno(pac) is False
    assert puede_autorizar_sobreturno(adm_fin) is False
    assert puede_autorizar_sobreturno(None) is False


def test_puede_responder_sobreturno():
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    pac = Principal(4, 1, RolUsuario.PACIENTE)

    turno_propio = _crear_turno(profesional_id=50, es_sobreturno=True)
    turno_no_sobreturno = _crear_turno(profesional_id=50, es_sobreturno=False)

    # Profesional sobre su propia agenda
    assert puede_responder_sobreturno(prof, turno_propio, profesional_id=50) is True
    # Profesional sobre agenda ajena
    assert puede_responder_sobreturno(prof, turno_propio, profesional_id=99) is False
    # No es sobreturno
    assert puede_responder_sobreturno(prof, turno_no_sobreturno, profesional_id=50) is False

    # Administrador con agenda propia (DD-24)
    assert puede_responder_sobreturno(admin, turno_propio, profesional_id=50) is True
    assert puede_responder_sobreturno(admin, turno_propio, profesional_id=99) is False

    # Otros roles
    assert puede_responder_sobreturno(recep, turno_propio, profesional_id=50) is False
    assert puede_responder_sobreturno(pac, turno_propio, profesional_id=50) is False


def test_sobreturno_cumple_condiciones():
    turno = _crear_turno(profesional_id=50, es_sobreturno=True)

    # Avisado y con autorizante registrado
    assert sobreturno_cumple_condiciones(turno, profesional_avisado=True, autorizante_id=1) is True

    # Sin avisar al profesional
    assert sobreturno_cumple_condiciones(turno, profesional_avisado=False, autorizante_id=1) is False

    # Sin autorizante registrado
    assert sobreturno_cumple_condiciones(turno, profesional_avisado=True, autorizante_id=None) is False

    # No es sobreturno
    turno_comun = _crear_turno(profesional_id=50, es_sobreturno=False)
    assert sobreturno_cumple_condiciones(turno_comun, profesional_avisado=True, autorizante_id=1) is False

    # Nulos
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    assert sobreturno_cumple_condiciones(None, profesional_avisado=True, autorizante_id=1) is False
    assert puede_responder_sobreturno(None, turno, 50) is False
    assert puede_responder_sobreturno(prof, None, 50) is False
    assert puede_responder_sobreturno(prof, turno, None) is False
