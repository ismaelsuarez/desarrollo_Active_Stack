import pytest

from app.domain.value_objects.telefono import normalizar_telefono


def test_normaliza_telefono_internacional_explicito():
    assert normalizar_telefono('+54 9 11 2345-6789') == '5491123456789'


@pytest.mark.parametrize(('valor', 'esperado'), [
    ('011 2345-6789', '541123456789'),
    ('011 15 2345-6789', '5491123456789'),
    ('0341 15 234-5678', '5493412345678'),
    ('02964 15 123456', '5492964123456'),
    ('0341 234-5678', '543412345678'),
    ('+1 (212) 555-1234', '12125551234'),
    ('0044 20 7946 0958', '442079460958'),
    (None, None), ('', None), ('12345', None), ('011 abc 2345-6789', None),
    ('+000123456789', None), ('+5411', None), ('011 2345 6789 ext 4', None),
    ('012 15 1515-6789', None), ('１１３３３３３３３３', None),
])
def test_normaliza_formatos_y_rechaza_ambiguos(valor, esperado):
    assert normalizar_telefono(valor) == esperado
