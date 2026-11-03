import pytest
from pydantic import ValidationError

from app.api.v1.schemas.cuenta import RegistroRequest


@pytest.fixture
def registro():
    return {
        'nombre': ' Ana ', 'apellido': ' Paz ', 'telefono': ' 1144445555 ',
        'email': ' ANA@EXAMPLE.TEST ', 'dni': ' 12345678 ',
        'nombre_usuario': ' ANA ', 'password': 'password-seguro',
        'acepta_aviso_privacidad': True, 'aviso_privacidad_version': 'version-del-servidor',
    }


def test_registro_normaliza_identificadores_y_protege_password(registro):
    cuerpo = RegistroRequest(**registro)
    assert cuerpo.nombre == 'Ana'
    assert cuerpo.apellido == 'Paz'
    assert cuerpo.telefono == '1144445555'
    assert cuerpo.email == 'ana@example.test'
    assert cuerpo.nombre_usuario == 'ana'
    assert cuerpo.dni == '12345678'
    assert cuerpo.password.get_secret_value() == 'password-seguro'
    assert cuerpo.obra_social is None
    assert 'password-seguro' not in repr(cuerpo)


@pytest.mark.parametrize('campo,valor', [
    ('nombre', '  '), ('apellido', ''), ('telefono', ' '),
    ('nombre_usuario', '  '), ('email', 'correo-invalido'),
    ('email', 'nombre@dominio'), ('dni', '12.345.678'),
    ('dni', '12a45678'), ('password', '1234567'),
    ('acepta_aviso_privacidad', False),
    ('acepta_aviso_privacidad', 1), ('acepta_aviso_privacidad', 'true'),
])
def test_registro_rechaza_datos_invalidos(registro, campo, valor):
    with pytest.raises(ValidationError):
        RegistroRequest(**{**registro, campo: valor})


@pytest.mark.parametrize('campo', ['consultorio_id', 'rol', 'usuario_id'])
def test_registro_rechaza_identidad_y_rol_del_cliente(registro, campo):
    with pytest.raises(ValidationError) as error:
        RegistroRequest(**registro, **{campo: 'dato-ajeno'})
    assert 'password-seguro' not in str(error.value)
    assert 'dato-ajeno' not in str(error.value)


def test_registro_exige_aceptacion_y_version_sin_compararla_con_la_vigente(registro):
    with pytest.raises(ValidationError):
        RegistroRequest(**{k: v for k, v in registro.items() if k != 'acepta_aviso_privacidad'})
    with pytest.raises(ValidationError):
        RegistroRequest(**{k: v for k, v in registro.items() if k != 'aviso_privacidad_version'})
    assert RegistroRequest(**registro).aviso_privacidad_version == 'version-del-servidor'


def test_solicitud_correo_normaliza_sin_aceptar_identidad_cliente():
    from app.api.v1.schemas.cuenta import CorreoRequest

    assert CorreoRequest(email=' ANA@EXAMPLE.TEST ').email == 'ana@example.test'
    with pytest.raises(ValidationError):
        CorreoRequest(email='invalido')
    with pytest.raises(ValidationError):
        CorreoRequest(email='ana@example.test', consultorio_id=3)


def test_token_se_mantiene_secreto_y_no_admite_campos_extra():
    from app.api.v1.schemas.cuenta import TokenRequest

    cuerpo = TokenRequest(token='token-privado')
    assert cuerpo.token.get_secret_value() == 'token-privado'
    assert 'token-privado' not in repr(cuerpo)
    with pytest.raises(ValidationError) as error:
        TokenRequest(token='token-privado', consultorio_id=1)
    assert 'token-privado' not in str(error.value)
    with pytest.raises(ValidationError):
        TokenRequest(token='')


def test_restablecimiento_exige_token_y_password_nueva_de_ocho_caracteres():
    from app.api.v1.schemas.cuenta import RestablecerPasswordRequest

    cuerpo = RestablecerPasswordRequest(token='token-privado', password='12345678')
    assert cuerpo.token.get_secret_value() == 'token-privado'
    assert cuerpo.password.get_secret_value() == '12345678'
    assert '12345678' not in repr(cuerpo)
    with pytest.raises(ValidationError):
        RestablecerPasswordRequest(token='token-privado', password='1234567')
    with pytest.raises(ValidationError):
        RestablecerPasswordRequest(token='token-privado', password='12345678', consultorio_id=1)


def test_cambio_de_password_exige_actual_y_nueva_sin_exponerlas():
    from app.api.v1.schemas.cuenta import CambiarPasswordRequest

    cuerpo = CambiarPasswordRequest(password_actual='actual-privada', password_nueva='12345678')
    assert cuerpo.password_actual.get_secret_value() == 'actual-privada'
    assert cuerpo.password_nueva.get_secret_value() == '12345678'
    assert 'actual-privada' not in repr(cuerpo)
    assert '12345678' not in repr(cuerpo)
    with pytest.raises(ValidationError):
        CambiarPasswordRequest(password_actual='actual-privada', password_nueva='1234567')
    with pytest.raises(ValidationError):
        CambiarPasswordRequest(password_nueva='12345678')
    with pytest.raises(ValidationError):
        CambiarPasswordRequest(password_actual='actual-privada', password_nueva='12345678', usuario_id=2)


@pytest.mark.parametrize('datos,esperado', [
    ({'telefono': ' 1144445555 '}, {'telefono': '1144445555', 'email': None}),
    ({'email': ' ANA@EXAMPLE.TEST '}, {'telefono': None, 'email': 'ana@example.test'}),
])
def test_actualizar_cuenta_acepta_un_contacto_y_lo_normaliza(datos, esperado):
    from app.api.v1.schemas.cuenta import ActualizarCuentaRequest

    assert ActualizarCuentaRequest(**datos).model_dump() == esperado


@pytest.mark.parametrize('datos', [
    {}, {'telefono': None, 'email': None}, {'telefono': ' '},
    {'email': 'correo-invalido'}, {'telefono': '1144445555', 'dni': '12345678'},
])
def test_actualizar_cuenta_rechaza_cuerpo_vacio_invalido_o_datos_de_ficha(datos):
    from app.api.v1.schemas.cuenta import ActualizarCuentaRequest

    with pytest.raises(ValidationError):
        ActualizarCuentaRequest(**datos)


@pytest.mark.parametrize('campo,valor', [
    ('nombre', 'n' * 121), ('apellido', 'a' * 121),
    ('telefono', '1' * 41), ('email', 'a' * 250 + '@example.test'),
    ('dni', '1' * 21), ('nombre_usuario', 'u' * 256),
    ('password', 'p' * 129), ('obra_social', 'o' * 256),
    ('aviso_privacidad_version', 'v' * 65),
])
def test_registro_rechaza_campos_excesivamente_largos(registro, campo, valor):
    with pytest.raises(ValidationError):
        RegistroRequest(**{**registro, campo: valor})
