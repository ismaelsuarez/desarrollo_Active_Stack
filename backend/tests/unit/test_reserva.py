from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.policies.reserva import duracion_turno, estado_inicial, validar_intervalo
from app.domain.value_objects.estado_turno import EstadoTurno

ZONA = "America/Argentina/Buenos_Aires"


def hora(horas: int, minutos: int = 0, segundos: int = 0) -> datetime:
    return datetime(2026, 11, 9, horas, minutos, segundos, tzinfo=ZoneInfo(ZONA))


def test_intervalo_completo_en_extremo_del_bloque_es_valido():
    validar_intervalo(hora(9), hora(9, 30), [(time(9), time(12))], [], 15, ZONA)


def test_inicio_fuera_de_grilla_no_es_reservable():
    with pytest.raises(ValueError):
        validar_intervalo(hora(9, 7), hora(9, 37), [(time(9), time(12))], [], 15, ZONA)


@pytest.mark.parametrize("inicio,fin", [
    (hora(11, 30), hora(12)),
    (hora(13, 10), hora(13, 40)),
    (hora(9).astimezone(timezone.utc), hora(9, 30).astimezone(timezone.utc)),
])
def test_bordes_zona_equivalente_y_grilla_anclada_a_cada_bloque(inicio, fin):
    validar_intervalo(inicio, fin, [(time(9), time(12)), (time(13, 10), time(17))], [], 15, ZONA)


@pytest.mark.parametrize("inicio,fin", [
    (hora(11, 45), hora(12, 15)),
    (hora(11, 45), hora(13, 15)),
    (hora(8, 45), hora(9, 15)),
    (hora(9), hora(9)),
    (hora(9, 30), hora(9)),
    (hora(9, 0, 1), hora(9, 30)),
    (hora(9).replace(microsecond=1), hora(9, 30)),
    (hora(9).replace(tzinfo=None), hora(9, 30)),
    (hora(9), hora(9, 30).replace(tzinfo=None)),
    (hora(23, 45), hora(0, 15) + timedelta(days=1)),
])
def test_rechaza_intervalos_fuera_de_un_bloque_o_sin_zona(inicio, fin):
    with pytest.raises(ValueError):
        validar_intervalo(inicio, fin, [(time(9), time(12)), (time(13), time(17))], [], 15, ZONA)


@pytest.mark.parametrize("bloqueos", [
    [(hora(9, 15), hora(9, 45))],
    [(hora(8), hora(10))],
    [(hora(9), hora(9, 30))],
    [(hora(8, 45).astimezone(timezone.utc), hora(9, 15).astimezone(timezone.utc))],
])
def test_rechaza_bloqueo_parcial_total_global_o_propio(bloqueos):
    with pytest.raises(ValueError):
        validar_intervalo(hora(9), hora(9, 30), [(time(9), time(12))], bloqueos, 15, ZONA)


@pytest.mark.parametrize("bloqueos", [
    [(hora(8, 30), hora(9))],
    [(hora(9, 30), hora(10))],
])
def test_bloqueos_contiguos_no_intersectan_el_intervalo(bloqueos):
    validar_intervalo(hora(9), hora(9, 30), [(time(9), time(12))], bloqueos, 15, ZONA)


def test_sin_bloques_no_hay_horario_valido():
    with pytest.raises(ValueError):
        validar_intervalo(hora(9), hora(9, 30), [], [], 15, ZONA)


def test_duracion_de_catalogo_se_conserva():
    assert duracion_turno(30, None, 15) == 30


@pytest.mark.parametrize("catalogo,ajustada,esperada", [
    (60, None, 60), (20, None, 20), (30, 45, 45), (60, 15, 15),
])
def test_duracion_ajustada_o_catalogo_sin_redondeo(catalogo, ajustada, esperada):
    assert duracion_turno(catalogo, ajustada, 15) == esperada


@pytest.mark.parametrize("ajustada", [20, 0, -15])
def test_ajuste_exige_duracion_positiva_en_multiplos_de_grilla(ajustada):
    with pytest.raises(ValueError):
        duracion_turno(30, ajustada, 15)


def test_anticipo_exactamente_en_umbral_nace_pendiente():
    assert estado_inicial(hora(9) + timedelta(hours=48), hora(9), 48) == EstadoTurno.PENDIENTE


@pytest.mark.parametrize("minutos,manual,esperado", [
    (2879, False, EstadoTurno.CONFIRMADO),
    (2881, False, EstadoTurno.PENDIENTE),
    (2880, True, EstadoTurno.CONFIRMADO),
    (4000, True, EstadoTurno.CONFIRMADO),
])
def test_estado_inicial_distingue_umbral_estricto_y_confirmacion_manual(minutos, manual, esperado):
    assert estado_inicial(hora(9) + timedelta(minutes=minutos), hora(9), 48, manual) == esperado
