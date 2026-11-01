from datetime import datetime, timezone
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.turno import turno_es_modificable, transicion_permitida


def _crear_turno_con_estado(estado: EstadoTurno) -> Turno:
    return Turno(
        id=1,
        consultorio_id=1,
        paciente_id=10,
        profesional_id=20,
        box_id=1,
        prestacion_id=1,
        inicio=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        fin=datetime(2026, 11, 1, 11, 0, tzinfo=timezone.utc),
        estado=estado,
        es_sobreturno=False,
    )


def test_turno_es_modificable():
    # Estados modificables
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.PENDIENTE)) is True
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.CONFIRMADO)) is True

    # Estados no modificables
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.ATENDIDO)) is False
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.AUSENTE)) is False
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.CANCELADO)) is False
    assert turno_es_modificable(_crear_turno_con_estado(EstadoTurno.LIBERADO)) is False


def test_transiciones_desde_pendiente():
    t = _crear_turno_con_estado(EstadoTurno.PENDIENTE)
    assert transicion_permitida(t, EstadoTurno.CONFIRMADO) is True
    assert transicion_permitida(t, EstadoTurno.ATENDIDO) is True
    assert transicion_permitida(t, EstadoTurno.AUSENTE) is True
    assert transicion_permitida(t, EstadoTurno.CANCELADO) is True
    assert transicion_permitida(t, EstadoTurno.LIBERADO) is True
    assert transicion_permitida(t, EstadoTurno.PENDIENTE) is False  # no transición reflexiva


def test_transiciones_desde_confirmado():
    t = _crear_turno_con_estado(EstadoTurno.CONFIRMADO)
    assert transicion_permitida(t, EstadoTurno.ATENDIDO) is True
    assert transicion_permitida(t, EstadoTurno.AUSENTE) is True
    assert transicion_permitida(t, EstadoTurno.CANCELADO) is True

    assert transicion_permitida(t, EstadoTurno.PENDIENTE) is False
    assert transicion_permitida(t, EstadoTurno.LIBERADO) is False


def test_transiciones_desde_ausente():
    t = _crear_turno_con_estado(EstadoTurno.AUSENTE)
    # Solo admite corregir a atendido
    assert transicion_permitida(t, EstadoTurno.ATENDIDO) is True

    assert transicion_permitida(t, EstadoTurno.CANCELADO) is False
    assert transicion_permitida(t, EstadoTurno.CONFIRMADO) is False
    assert transicion_permitida(t, EstadoTurno.PENDIENTE) is False
    assert transicion_permitida(t, EstadoTurno.LIBERADO) is False


def test_estados_terminales_no_admiten_transicion():
    for estado in (EstadoTurno.ATENDIDO, EstadoTurno.CANCELADO, EstadoTurno.LIBERADO):
        t = _crear_turno_con_estado(estado)
        for destino in EstadoTurno:
            assert transicion_permitida(t, destino) is False


def test_transiciones_casos_borde_nulos():
    t = _crear_turno_con_estado(EstadoTurno.PENDIENTE)
    assert turno_es_modificable(None) is False
    assert transicion_permitida(None, EstadoTurno.CONFIRMADO) is False
    assert transicion_permitida(t, None) is False
