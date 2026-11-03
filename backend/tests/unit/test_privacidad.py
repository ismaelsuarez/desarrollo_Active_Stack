from pathlib import Path
import pytest

from app.application.privacidad import VERSION_AVISO, TEXTO_AVISO, renderizar_aviso


def test_aviso_copia_texto_y_version_de_la_fuente_del_proyecto():
    fuente = (Path(__file__).resolve().parents[3] / 'knowledge-base' /
              '13_aviso_de_privacidad_borrador.md').read_text(encoding='utf-8')
    texto = fuente.split('## Texto que ve el paciente\n', 1)[1].split(
        '## Leyenda del campo de notas', 1)[0].strip()
    assert TEXTO_AVISO == texto
    assert VERSION_AVISO == '2026-10-borrador'
    aviso = renderizar_aviso('Consultorio Centro', 'Av. Corrientes 123', '1144445555')
    assert aviso['version'] == '2026-10-borrador'
    assert 'Consultorio Centro, con domicilio en Av. Corrientes 123' in aviso['texto']
    assert 'escribiendo a 1144445555' in aviso['texto']


@pytest.mark.parametrize('direccion,telefono,marcador', [
    (None, '1144445555', '[DOMICILIO]'),
    ('Calle 1', None, '[CONTACTO]'),
])
def test_aviso_incompleto_conserva_marcador_y_no_esta_listo_para_produccion(direccion, telefono, marcador):
    from app.application.privacidad import aviso_completo

    aviso = renderizar_aviso('Consultorio Centro', direccion, telefono)
    assert marcador in aviso['texto']
    assert not aviso_completo(aviso['texto'])


def test_aviso_completo_no_contiene_marcadores():
    from app.application.privacidad import aviso_completo

    aviso = renderizar_aviso('Consultorio Centro', 'Calle 1', '1144445555')
    assert aviso_completo(aviso['texto'])
    assert '[' not in aviso['texto']
