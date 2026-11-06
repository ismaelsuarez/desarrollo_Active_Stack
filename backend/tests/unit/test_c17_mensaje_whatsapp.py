from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest

from app.domain.services.mensaje_whatsapp import construir_mensaje_whatsapp


def test_mensaje_codifica_nombres_y_no_necesita_datos_clinicos():
    mensaje, enlace = construir_mensaje_whatsapp(
        telefono='5491123456789', paciente='Ana & José',
        fecha_hora=datetime(2026, 11, 9, 10, 30), profesional='Dra. Sol',
        consultorio='Clínica Sur', accion='confirmar',
    )
    assert 'Ana & José' in mensaje
    assert '09/11/2026' in mensaje and '10:30' in mensaje
    assert 'Dra. Sol' in mensaje and 'Clínica Sur' in mensaje
    assert urlsplit(enlace).path == '/5491123456789'
    assert parse_qs(urlsplit(enlace).query)['text'] == [mensaje]


def test_mensaje_recordatorio_con_accion_permitida():
    mensaje, enlace = construir_mensaje_whatsapp(
        telefono='12125551234', paciente='María',
        fecha_hora=datetime(2026, 1, 4, 8, 5), profesional='Dr. Paz',
        consultorio='Consultorio Norte', accion='recordar',
    )
    assert '04/01/2026' in mensaje and '08:05' in mensaje
    assert parse_qs(urlsplit(enlace).query)['text'] == [mensaje]


def test_no_acepta_accion_arbitraria_que_inyecte_datos_clinicos():
    with pytest.raises(ValueError):
        construir_mensaje_whatsapp(
            telefono='12125551234', paciente='María',
            fecha_hora=datetime(2026, 1, 4, 8, 5), profesional='Dr. Paz',
            consultorio='Consultorio Norte', accion='tratamiento sensible',
        )


@pytest.mark.parametrize(('accion', 'fragmento'), [
    ('liberacion', 'liberado'),
    ('cancelacion_por_personal', 'cancelado'),
    ('reprogramacion_por_personal', 'reprogramado'),
])
def test_mensaje_de_hecho_no_presenta_el_turno_como_vigente(accion, fragmento):
    mensaje, _ = construir_mensaje_whatsapp(
        telefono='+54 9 11 2345-6789', paciente='José',
        fecha_hora=datetime(2026, 11, 9, 13, 30, tzinfo=UTC),
        profesional='Dra. Sol', consultorio='Centro', accion=accion,
        zona_horaria='America/Argentina/Buenos_Aires',
    )
    assert fragmento in mensaje
    assert '09/11/2026' in mensaje and '10:30' in mensaje


def test_recordatorio_no_promete_liberacion_sin_condiciones():
    mensaje, _ = construir_mensaje_whatsapp(
        telefono='5491123456789', paciente='José',
        fecha_hora=datetime(2026, 11, 9, 10, 30), profesional='Sol',
        consultorio='Centro', accion='recordar', liberacion_automatica=False,
    )
    assert 'liberar' not in mensaje and 'liberado' not in mensaje


def test_recordatorio_advierte_liberacion_cuando_corresponde():
    mensaje, _ = construir_mensaje_whatsapp(
        telefono='5491123456789', paciente='José',
        fecha_hora=datetime(2026, 11, 9, 10, 30), profesional='Sol',
        consultorio='Centro', accion='recordar', liberacion_automatica=True,
    )
    assert 'liberado' in mensaje


def test_no_genera_enlace_para_telefono_invalido():
    with pytest.raises(ValueError):
        construir_mensaje_whatsapp(
            telefono='123', paciente='José', fecha_hora=datetime(2026, 11, 9),
            profesional='Sol', consultorio='Centro', accion='confirmar',
        )
