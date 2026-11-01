from datetime import datetime, timedelta, timezone
import pytest
from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.turno import dentro_de_ventana_paciente, hora_de_inicio_alcanzada


def _crear_turno(inicio: datetime) -> Turno:
    return Turno(
        id=1,
        consultorio_id=1,
        paciente_id=10,
        profesional_id=20,
        box_id=1,
        prestacion_id=1,
        inicio=inicio,
        fin=inicio + timedelta(hours=1),
        estado=EstadoTurno.CONFIRMADO,
        es_sobreturno=False,
    )


def test_dentro_de_ventana_paciente_limites_exactos():
    inicio = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
    turno = _crear_turno(inicio)
    limite_24h = inicio - timedelta(hours=24)

    # Exactamente en el límite de 24 horas: permitido
    assert dentro_de_ventana_paciente(turno, ahora=limite_24h, horas_limite=24) is True

    # 1 segundo antes del límite (con más de 24h de anticipación): permitido
    assert dentro_de_ventana_paciente(turno, ahora=limite_24h - timedelta(seconds=1), horas_limite=24) is True

    # 1 segundo después del límite (con menos de 24h de anticipación): denegado
    assert dentro_de_ventana_paciente(turno, ahora=limite_24h + timedelta(seconds=1), horas_limite=24) is False


def test_hora_de_inicio_alcanzada_limites_exactos():
    inicio = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
    turno = _crear_turno(inicio)

    # Exactamente al inicio: permitido
    assert hora_de_inicio_alcanzada(turno, ahora=inicio) is True

    # 1 segundo después del inicio: permitido
    assert hora_de_inicio_alcanzada(turno, ahora=inicio + timedelta(seconds=1)) is True

    # 1 segundo antes del inicio: denegado
    assert hora_de_inicio_alcanzada(turno, ahora=inicio - timedelta(seconds=1)) is False


def test_ventanas_exigen_zona_horaria():
    inicio = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
    turno = _crear_turno(inicio)
    ahora_naive = datetime(2026, 11, 1, 10, 0, 0)

    with pytest.raises(ValueError, match="zona horaria"):
        dentro_de_ventana_paciente(turno, ahora=ahora_naive)

    with pytest.raises(ValueError, match="zona horaria"):
        hora_de_inicio_alcanzada(turno, ahora=ahora_naive)


def test_ventanas_triangulacion_horas_configurables_y_nulos():
    inicio = datetime(2026, 11, 2, 10, 0, 0, tzinfo=timezone.utc)
    turno = _crear_turno(inicio)
    ahora_40h = inicio - timedelta(hours=40)

    # Con 48h de límite, 40h de anticipación está vencido
    assert dentro_de_ventana_paciente(turno, ahora=ahora_40h, horas_limite=48) is False
    # Con 24h de límite, 40h de anticipación está dentro de la ventana
    assert dentro_de_ventana_paciente(turno, ahora=ahora_40h, horas_limite=24) is True

    # Nulos
    assert dentro_de_ventana_paciente(None, ahora=ahora_40h) is False
    assert dentro_de_ventana_paciente(turno, ahora=None) is False
    assert hora_de_inicio_alcanzada(None, ahora=ahora_40h) is False
    assert hora_de_inicio_alcanzada(turno, ahora=None) is False
