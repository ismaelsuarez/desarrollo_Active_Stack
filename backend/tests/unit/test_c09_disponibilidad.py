from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.domain.entities.turno import Turno
from app.domain.services.disponibilidad import calcular_disponibilidad
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.value_objects.intervalo import Intervalo

ZONA = "America/Argentina/Buenos_Aires"
DIA = date(2026, 11, 9)


def hora(h: int, m: int = 0, *, dia: date = DIA) -> datetime:
    return datetime.combine(dia, time(h, m), tzinfo=ZoneInfo(ZONA))


def consultar(**cambios):
    argumentos = dict(
        fecha=DIA, bloques=[(time(9), time(10))], bloqueos=[], turnos=[],
        duracion_min=30, granularidad=15, zona=ZONA,
        ahora=hora(8), dias_anticipacion_maxima=60,
    )
    argumentos.update(cambios)
    return calcular_disponibilidad(**argumentos)


def test_ofrece_turnos_completos_hasta_el_extremo_del_bloque():
    assert consultar() == [
        Intervalo(hora(9), hora(9, 30)),
        Intervalo(hora(9, 15), hora(9, 45)),
        Intervalo(hora(9, 30), hora(10)),
    ]


def test_prestacion_larga_no_se_parte_entre_bloques_ni_cruza_la_pausa():
    assert consultar(
        bloques=[(time(9), time(10)), (time(10, 30), time(11))],
        duracion_min=60,
    ) == [Intervalo(hora(9), hora(10))]


@pytest.mark.parametrize("bloqueo,esperados", [
    ((hora(9, 30), hora(10)), [(hora(9), hora(9, 30))]),
    ((hora(9, 45), hora(10, 15)), [(hora(9), hora(9, 30)), (hora(9, 15), hora(9, 45))]),
])
def test_excluye_excepciones_totales_o_parciales_pero_admite_contiguidad(bloqueo, esperados):
    assert consultar(bloqueos=[bloqueo]) == [Intervalo(*puntas) for puntas in esperados]


def turno(inicio, fin, estado=EstadoTurno.PENDIENTE, es_sobreturno=False):
    return Turno(
        id=1, consultorio_id=1, paciente_id=1, profesional_id=1,
        box_id=1, prestacion_id=1, inicio=inicio, fin=fin,
        estado=estado, es_sobreturno=es_sobreturno,
    )


@pytest.mark.parametrize("estado", [
    EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO,
    EstadoTurno.ATENDIDO, EstadoTurno.AUSENTE,
])
@pytest.mark.parametrize("es_sobreturno", [False, True])
def test_turnos_ocupantes_incluyen_sobreturnos_y_permiten_extremos_contiguos(estado, es_sobreturno):
    assert consultar(turnos=[turno(hora(9, 30), hora(10), estado, es_sobreturno)]) == [
        Intervalo(hora(9), hora(9, 30)),
    ]


@pytest.mark.parametrize("estado", [EstadoTurno.CANCELADO, EstadoTurno.LIBERADO])
def test_turnos_cancelados_y_liberados_no_ocupan(estado):
    assert consultar(turnos=[turno(hora(9), hora(10), estado)]) == [
        Intervalo(hora(9), hora(9, 30)),
        Intervalo(hora(9, 15), hora(9, 45)),
        Intervalo(hora(9, 30), hora(10)),
    ]


@pytest.mark.parametrize("inicio,fin,esperados", [
    (hora(8, 45), hora(9, 15), [(hora(9, 15), hora(9, 45)), (hora(9, 30), hora(10))]),
    (hora(9), hora(9, 30), [(hora(9, 30), hora(10))]),
    (hora(9), hora(10), []),
])
def test_ocupacion_parcial_exacta_o_total(inicio, fin, esperados):
    assert consultar(turnos=[turno(inicio, fin)]) == [Intervalo(*puntas) for puntas in esperados]


@pytest.mark.parametrize("granularidad,esperados", [
    (15, [(hora(9, 10), hora(9, 30)), (hora(9, 25), hora(9, 45)), (hora(9, 40), hora(10))]),
    (20, [(hora(9, 10), hora(9, 30)), (hora(9, 30), hora(9, 50)), (hora(9, 50), hora(10, 10))]),
])
def test_grilla_anclada_y_duracion_no_multiplo_sin_redondeo(granularidad, esperados):
    assert consultar(
        bloques=[(time(9, 10), time(10, 10))], duracion_min=20, granularidad=granularidad,
    ) == [Intervalo(*puntas) for puntas in esperados]


@pytest.mark.parametrize("ahora,esperados", [
    (hora(9), [(hora(9, 15), hora(9, 45)), (hora(9, 30), hora(10))]),
    (hora(9, 15), [(hora(9, 30), hora(10))]),
    (hora(9, 30), []),
])
def test_hoy_ofrece_solo_inicios_estrictamente_futuros(ahora, esperados):
    assert consultar(ahora=ahora) == [Intervalo(*puntas) for puntas in esperados]


@pytest.mark.parametrize("dias,hay_huecos", [(60, True), (61, False)])
def test_horizonte_incluye_el_ultimo_dia_local(dias, hay_huecos):
    dia = DIA + timedelta(days=dias)
    resultado = consultar(fecha=dia)
    esperado = [
        Intervalo(hora(9, dia=dia), hora(9, 30, dia=dia)),
        Intervalo(hora(9, 15, dia=dia), hora(9, 45, dia=dia)),
        Intervalo(hora(9, 30, dia=dia), hora(10, dia=dia)),
    ] if hay_huecos else []
    assert resultado == esperado


def test_fecha_horizonte_se_calcula_en_zona_local_cerca_de_medianoche_utc():
    # 10/11 01:00 UTC todavía es 09/11 22:00 en el consultorio.
    ahora = datetime(2026, 11, 10, 1, tzinfo=timezone.utc)
    assert consultar(ahora=ahora, fecha=date(2026, 11, 11), dias_anticipacion_maxima=1) == []
    dia_permitido = date(2026, 11, 10)
    assert consultar(ahora=ahora, fecha=dia_permitido, dias_anticipacion_maxima=1) == [
        Intervalo(hora(9, dia=dia_permitido), hora(9, 30, dia=dia_permitido)),
        Intervalo(hora(9, 15, dia=dia_permitido), hora(9, 45, dia=dia_permitido)),
        Intervalo(hora(9, 30, dia=dia_permitido), hora(10, dia=dia_permitido)),
    ]


def test_dia_sin_bloques_no_ofrece_horarios():
    assert consultar(bloques=[]) == []


def test_resultado_ordenado_determinista_sin_mutar_bloques_ni_turnos():
    bloques = [(time(10), time(10, 30)), (time(9), time(9, 30))]
    bloqueos = [(hora(8), hora(8, 30))]
    turnos = [turno(hora(9), hora(9, 30), EstadoTurno.CANCELADO)]
    original = (bloques.copy(), bloqueos.copy(), turnos.copy())
    esperado = [Intervalo(hora(9), hora(9, 30)), Intervalo(hora(10), hora(10, 30))]
    assert consultar(bloques=bloques, bloqueos=bloqueos, turnos=turnos) == esperado
    assert consultar(bloques=bloques, bloqueos=bloqueos, turnos=turnos) == esperado
    assert (bloques, bloqueos, turnos) == original


def test_bloque_global_y_ocupacion_propia_se_combinan_sin_ocultar_huecos_contiguos():
    assert consultar(
        bloques=[(time(9), time(12))],
        bloqueos=[(hora(10), hora(10, 30))],
        turnos=[turno(hora(11), hora(11, 30))],
    ) == [
        Intervalo(hora(9), hora(9, 30)),
        Intervalo(hora(9, 15), hora(9, 45)),
        Intervalo(hora(9, 30), hora(10)),
        Intervalo(hora(10, 30), hora(11)),
        Intervalo(hora(11, 30), hora(12)),
    ]


def test_dia_pasado_no_ofrece_turnos_aunque_la_agenda_este_libre():
    assert consultar(fecha=DIA - timedelta(days=1)) == []
