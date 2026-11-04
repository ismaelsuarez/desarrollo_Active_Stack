"""RN-47/RN-48: contratos de entrada de fichas, sin valores privados en errores."""
import pytest
from pydantic import ValidationError


def test_alta_normaliza_datos_y_conserva_opcionales():
    from app.api.v1.schemas.pacientes import CrearPaciente

    datos = CrearPaciente(nombre=" Ana ", apellido=" Paz ", telefono=" 1144445555 ",
                         email=" ANA@EXAMPLE.TEST ", dni=" 12345678 ")
    assert datos.model_dump() == {
        "nombre": "Ana", "apellido": "Paz", "telefono": "1144445555",
        "email": "ana@example.test", "dni": "12345678", "obra_social": None, "notas": None,
    }


@pytest.mark.parametrize("campo,valor", [
    ("nombre", " "), ("apellido", ""), ("telefono", ""), ("email", "invalido"),
    ("dni", "12.345.678"), ("dni", "12 345678"), ("dni", "1234567A"),
])
def test_alta_rechaza_datos_invalidos(campo, valor):
    from app.api.v1.schemas.pacientes import CrearPaciente

    datos = dict(nombre="Ana", apellido="Paz", telefono="1144445555",
                 email="ana@example.test", dni="12345678")
    with pytest.raises(ValidationError):
        CrearPaciente(**{**datos, campo: valor})


@pytest.mark.parametrize("campo", ["activo", "usuario_id", "consultorio_id"])
def test_alta_rechaza_control_del_cliente_sin_mostrar_valor(campo):
    from app.api.v1.schemas.pacientes import CrearPaciente

    with pytest.raises(ValidationError) as error:
        CrearPaciente(nombre="Ana", apellido="Paz", telefono="1144445555",
                      email="ana@example.test", dni="12345678", **{campo: "privado-sentinel"})
    assert "privado-sentinel" not in str(error.value)


def test_patch_conserva_omitidos_y_admite_limpiar_opcionales():
    from app.api.v1.schemas.pacientes import EditarPaciente

    datos = EditarPaciente(nombre=" Eva ", notas=None)
    assert datos.model_dump(exclude_unset=True) == {"nombre": "Eva", "notas": None}


@pytest.mark.parametrize("datos,esperado", [
    ({"apellido": " Sol "}, {"apellido": "Sol"}),
    ({"telefono": " 1155556666 "}, {"telefono": "1155556666"}),
    ({"email": " EVA@EXAMPLE.TEST "}, {"email": "eva@example.test"}),
    ({"dni": " 87654321 "}, {"dni": "87654321"}),
    ({"obra_social": None}, {"obra_social": None}),
])
def test_patch_normaliza_cada_campo_permitido(datos, esperado):
    from app.api.v1.schemas.pacientes import EditarPaciente

    assert EditarPaciente(**datos).model_dump(exclude_unset=True) == esperado


@pytest.mark.parametrize("datos", [
    {}, {"nombre": None}, {"apellido": None}, {"telefono": None}, {"email": None},
    {"dni": None}, {"activo": False}, {"usuario_id": 1}, {"consultorio_id": 2},
])
def test_patch_rechaza_vacio_obligatorios_null_y_control_de_vinculo(datos):
    from app.api.v1.schemas.pacientes import EditarPaciente

    with pytest.raises(ValidationError):
        EditarPaciente(**datos)


def test_consulta_paginada_normaliza_filtros_y_defaultea_limites():
    from app.api.v1.schemas.pacientes import ConsultaPacientes

    consulta = ConsultaPacientes(apellido=" Sol ", dni=" 12345678 ", telefono=" 1155 ")
    assert consulta.model_dump() == {"apellido": "Sol", "dni": "12345678", "telefono": "1155", "limit": 20, "offset": 0}


@pytest.mark.parametrize("datos", [{"limit": 0}, {"limit": 101}, {"offset": -1},
                                  {"apellido": " "}, {"dni": "12.345"}, {"desconocido": 1}])
def test_consulta_rechaza_limites_y_filtros_invalidos(datos):
    from app.api.v1.schemas.pacientes import ConsultaPacientes

    with pytest.raises(ValidationError):
        ConsultaPacientes(**datos)


def test_consulta_admite_bordes_de_paginacion():
    from app.api.v1.schemas.pacientes import ConsultaPacientes

    assert ConsultaPacientes(limit=1, offset=100).limit == 1
    assert ConsultaPacientes(limit=100).limit == 100


@pytest.mark.parametrize("campo", ["nombre", "apellido", "telefono", "email", "dni"])
def test_alta_exige_cada_dato_minimo(campo):
    from app.api.v1.schemas.pacientes import CrearPaciente

    datos = dict(nombre="Ana", apellido="Paz", telefono="1144445555",
                 email="ana@example.test", dni="12345678")
    datos.pop(campo)
    with pytest.raises(ValidationError) as error:
        CrearPaciente(**datos)
    assert error.value.errors(include_input=False)[0]["loc"] == (campo,)


def test_motivo_de_desvinculacion_normaliza_y_rechazo_permite_omitirlo():
    from app.api.v1.schemas.vinculacion import DesvincularRequest, RechazarRequest

    assert DesvincularRequest(motivo=" Corrección verificada ").motivo == "Corrección verificada"
    assert RechazarRequest().motivo is None
    assert RechazarRequest(motivo=" Corrección ").motivo == "Corrección"


@pytest.mark.parametrize("datos", [{}, {"motivo": None}, {"motivo": " "},
                                  {"motivo": "Corrección", "usuario_id": "privado-sentinel"}])
def test_desvinculacion_exige_motivo_y_prohibe_extras_sin_fuga(datos):
    from app.api.v1.schemas.vinculacion import DesvincularRequest

    with pytest.raises(ValidationError) as error:
        DesvincularRequest(**datos)
    assert "privado-sentinel" not in str(error.value)


@pytest.mark.parametrize("datos", [{"estado": "desvinculada"}, {"limit": 0},
                                  {"offset": -1}, {"consultorio_id": 2}])
def test_consulta_solicitudes_rechaza_estados_limites_y_campos_no_declarados(datos):
    from app.api.v1.schemas.vinculacion import ConsultaSolicitudes

    with pytest.raises(ValidationError):
        ConsultaSolicitudes(**datos)
