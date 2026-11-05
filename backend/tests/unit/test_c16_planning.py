"""RN-25/RN-26/RN-29: decisiones temporales con instantes conocidos."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.policies.hitos import programacion_hitos
from app.domain.value_objects.estado_turno import EstadoTurno

ZONA = ZoneInfo("America/Argentina/Buenos_Aires")


def test_pending_booking_schedules_confirmation_and_reminder_from_start():
    assert programacion_hitos(
        datetime(2026, 11, 9, 10, tzinfo=ZONA), EstadoTurno.PENDIENTE,
        datetime(2026, 11, 6, 8, tzinfo=ZONA),
        horas_confirmacion=48, horas_recordatorio=24,
    ) == (
        ("solicitud_confirmacion", datetime(2026, 11, 7, 10, tzinfo=ZONA)),
        ("recordatorio", datetime(2026, 11, 8, 10, tzinfo=ZONA)),
    )


@pytest.mark.parametrize("horas,estado,tipos", [
    (48, EstadoTurno.PENDIENTE, ("solicitud_confirmacion", "recordatorio")),
    (30, EstadoTurno.CONFIRMADO, ("recordatorio",)),
    (24, EstadoTurno.CONFIRMADO, ()),
    (10, EstadoTurno.CONFIRMADO, ()),
    (72, EstadoTurno.CONFIRMADO, ("recordatorio",)),
    (72, EstadoTurno.CANCELADO, ()),
])
def test_initial_confirmation_and_elapsed_milestones(horas, estado, tipos):
    inicio = datetime(2026, 11, 9, 10, tzinfo=ZONA)
    assert tuple(tipo for tipo, _ in programacion_hitos(
        inicio, estado, inicio - timedelta(hours=horas),
        horas_confirmacion=48, horas_recordatorio=24,
    )) == tipos


def test_custom_configuration_uses_exact_instants_without_rounding():
    assert programacion_hitos(
        datetime(2026, 11, 9, 10, tzinfo=ZONA), EstadoTurno.PENDIENTE,
        datetime(2026, 11, 6, 8, tzinfo=ZONA),
        horas_confirmacion=60, horas_recordatorio=36,
    ) == (
        ("solicitud_confirmacion", datetime(2026, 11, 6, 22, tzinfo=ZONA)),
        ("recordatorio", datetime(2026, 11, 7, 22, tzinfo=ZONA)),
    )
