from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.ports.reloj import Reloj, RelojSimulado, RelojSistema

ZONA_BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def test_reloj_sistema_devuelve_instante_con_zona_horaria_de_buenos_aires():
    reloj: Reloj = RelojSistema()
    ahora = reloj.ahora()
    assert isinstance(ahora, datetime)
    assert ahora.tzinfo is not None
    assert ahora.tzname() == "ART" or ahora.tzinfo == ZONA_BUENOS_AIRES


def test_reloj_simulado_reproduce_instante_exacto():
    fijo = datetime(2026, 10, 15, 10, 30, tzinfo=ZONA_BUENOS_AIRES)
    reloj: Reloj = RelojSimulado(fijo)
    assert reloj.ahora() == fijo


def test_reloj_simulado_convierte_a_zona_buenos_aires_si_recibe_utc():
    utc_dt = datetime(2026, 10, 15, 13, 30, tzinfo=ZoneInfo("UTC"))
    reloj = RelojSimulado(utc_dt)
    assert reloj.ahora().tzinfo == ZONA_BUENOS_AIRES
    assert reloj.ahora().hour == 10
    assert reloj.ahora().minute == 30


def test_reloj_simulado_rechaza_datetime_naive():
    naive_dt = datetime(2026, 10, 15, 10, 30)
    with pytest.raises(ValueError, match="naive"):
        RelojSimulado(naive_dt)


def test_reloj_simulado_permite_avanzar_tiempo():
    inicio = datetime(2026, 10, 15, 10, 0, tzinfo=ZONA_BUENOS_AIRES)
    reloj = RelojSimulado(inicio)
    reloj.avanzar(timedelta(minutes=45))
    assert reloj.ahora() == datetime(2026, 10, 15, 10, 45, tzinfo=ZONA_BUENOS_AIRES)
