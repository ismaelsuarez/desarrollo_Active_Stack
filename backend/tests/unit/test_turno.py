from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.entities.turno import calcular_fin, exigir_zona_horaria
from app.domain.errors import InicioSinZonaHoraria

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def test_fin_es_inicio_mas_la_duracion_de_la_prestacion():
    inicio = datetime(2026, 11, 2, 10, 0, tzinfo=BUENOS_AIRES)

    fin = calcular_fin(inicio, duracion_min=30)

    assert fin == datetime(2026, 11, 2, 10, 30, tzinfo=BUENOS_AIRES)


def test_fin_con_una_prestacion_de_sesenta_minutos():
    inicio = datetime(2026, 11, 2, 15, 15, tzinfo=BUENOS_AIRES)

    fin = calcular_fin(inicio, duracion_min=60)

    assert fin == datetime(2026, 11, 2, 16, 15, tzinfo=BUENOS_AIRES)


def test_un_inicio_sin_zona_horaria_se_rechaza():
    inicio = datetime(2026, 11, 2, 10, 0)

    with pytest.raises(InicioSinZonaHoraria) as error:
        exigir_zona_horaria(inicio)

    assert str(error.value) == "el inicio debe indicar zona horaria"


def test_un_inicio_en_utc_se_acepta():
    inicio = datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc)

    exigir_zona_horaria(inicio)

    assert calcular_fin(inicio, duracion_min=30) == datetime(
        2026, 11, 2, 10, 30, tzinfo=BUENOS_AIRES
    )
