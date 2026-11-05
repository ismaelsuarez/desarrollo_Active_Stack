from datetime import datetime, timedelta, timezone

from app.application.services.limite_publico import LimitePublico


def test_origin_exhaustion_and_exact_window_renewal():
    ahora = datetime(2026, 11, 5, tzinfo=timezone.utc)
    limite = LimitePublico(cuota=2)
    assert limite.consumir('origen', ahora) == 0
    assert limite.consumir('origen', ahora) == 0
    assert limite.consumir('origen', ahora + timedelta(seconds=1)) == 59
    assert limite.consumir('otro', ahora) == 0
    assert limite.consumir('origen', ahora + timedelta(seconds=60)) == 0


def test_capacity_preserves_existing_quota_and_prunes_expired_origins():
    ahora = datetime(2026, 11, 5, tzinfo=timezone.utc)
    limite = LimitePublico(cuota=2, capacidad=2)
    assert limite.consumir('a', ahora) == 0
    assert limite.consumir('b', ahora) == 0
    assert limite.consumir('c', ahora) == 60
    assert limite.consumir('a', ahora) == 0
    assert limite.consumir('a', ahora) == 60
    assert limite.consumir('c', ahora + timedelta(seconds=60)) == 0


def test_invalid_settings_and_backward_clock_do_not_allow_extra_reads():
    import pytest

    for opciones in ({'cuota': 0}, {'ventana_segundos': 0}, {'capacidad': 0}):
        with pytest.raises(ValueError):
            LimitePublico(**opciones)
    ahora = datetime(2026, 11, 5, tzinfo=timezone.utc)
    limite = LimitePublico(cuota=1)
    assert limite.consumir('a', ahora) == 0
    assert limite.consumir('a', ahora - timedelta(seconds=1)) == 61
