import pytest

from app.domain.errors import ErrorDeDominio
from app.domain.value_objects.dni import Dni


def test_dni_valido_se_instancia_correctamente():
    dni = Dni("12345678")
    assert dni.valor == "12345678"
    assert str(dni) == "12345678"


def test_dni_normaliza_espacios_en_los_extremos():
    dni = Dni("  45678901  ")
    assert dni.valor == "45678901"


@pytest.mark.parametrize("invalido", ["", "12.345.678", "12345A", "abc", "12 345 678", "-1234567"])
def test_dni_rechaza_caracteres_no_numericos_o_formato_invalido(invalido):
    with pytest.raises(ErrorDeDominio, match="DNI"):
        Dni(invalido)


def test_dni_son_inmutables_y_comparables_por_valor():
    d1 = Dni("12345678")
    d2 = Dni("12345678")
    d3 = Dni("87654321")
    assert d1 == d2
    assert d1 != d3
    assert hash(d1) == hash(d2)
