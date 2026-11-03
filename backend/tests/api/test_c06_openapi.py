from app.api.v1.schemas.agenda import BoxEntrada, HorarioEntrada, ProfesionalEntrada
from app.api.v1.schemas.consultorio import ConfiguracionConsultorioEntrada
from app.api.v1.schemas.personal import PersonalEntrada
from app.api.v1.schemas.prestacion import PrestacionEntrada
from tests.api.test_health import configured_app


def test_c06_routes_are_in_openapi_with_documented_operations_and_strict_inputs():
    schema = configured_app().openapi()
    paths = schema["paths"]
    expected = {
        "/api/v1/usuarios": {"get", "post"},
        "/api/v1/usuarios/{usuario_id}": {"patch", "delete"},
        "/api/v1/boxes": {"get", "post"},
        "/api/v1/profesionales": {"get", "post"},
        "/api/v1/profesionales/{profesional_id}": {"patch"},
        "/api/v1/profesionales/{profesional_id}/horario-semanal": {"get", "put"},
        "/api/v1/profesionales/{profesional_id}/bloqueos": {"get", "post"},
        "/api/v1/bloqueos": {"get", "post"},
        "/api/v1/bloqueos/{bloqueo_id}": {"delete"},
        "/api/v1/prestaciones": {"get", "post"},
        "/api/v1/prestaciones/{prestacion_id}": {"patch", "delete"},
        "/api/v1/consultorio": {"get", "patch"},
    }
    for path, methods in expected.items():
        assert methods <= paths[path].keys()
        for method in methods:
            assert paths[path][method].get("security"), f"Missing auth contract for {method.upper()} {path}"
    for model in (BoxEntrada, HorarioEntrada, ProfesionalEntrada, ConfiguracionConsultorioEntrada, PersonalEntrada, PrestacionEntrada):
        assert model.model_json_schema().get("additionalProperties") is False


def test_c06_openapi_documents_success_and_expected_error_statuses():
    paths = configured_app().openapi()["paths"]
    assert "201" in paths["/api/v1/usuarios"]["post"]["responses"]
    assert {"403", "422"} <= paths["/api/v1/profesionales"]["post"]["responses"].keys()
    assert {"201", "409"} <= paths["/api/v1/prestaciones"]["post"]["responses"].keys()
    assert {"200", "422"} <= paths["/api/v1/consultorio"]["patch"]["responses"].keys()
    assert {"201", "409"} <= paths["/api/v1/bloqueos"]["post"]["responses"].keys()
