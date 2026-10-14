from app.domain.value_objects.estado_turno import ESTADOS_ACTIVOS, EstadoTurno


def test_los_estados_activos_son_los_que_ocupan_el_horario():
    assert ESTADOS_ACTIVOS == {
        EstadoTurno.PENDIENTE,
        EstadoTurno.CONFIRMADO,
        EstadoTurno.ATENDIDO,
        EstadoTurno.AUSENTE,
    }


def test_cancelado_y_liberado_no_son_estados_activos():
    assert EstadoTurno.CANCELADO not in ESTADOS_ACTIVOS
    assert EstadoTurno.LIBERADO not in ESTADOS_ACTIVOS
    assert len(EstadoTurno) == 6
