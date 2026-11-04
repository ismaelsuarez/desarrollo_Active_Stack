import httpx
import pytest

from app.application.errors_pacientes import RechazoPaciente
from app.core.config import Settings
from app.main import create_app


@pytest.mark.parametrize("codigo,mensaje", [(409, "La ficha cambió"), (404, "Ficha no encontrada")])
async def test_rechazo_de_paciente_respeta_codigo_y_mensaje_publico(codigo, mensaje):
    app = create_app(Settings(
        database_url="postgresql+asyncpg://postgres@localhost/prueba",
        jwt_secret_key="j" * 32, origin_hash_secret="o" * 32,
        app_env="test", consultorio_activo_id=1,
    ))

    @app.get("/prueba-rechazo")
    async def rechazar():
        raise RechazoPaciente(codigo, mensaje)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/prueba-rechazo")
    assert respuesta.status_code == codigo
    assert respuesta.json() == {"detail": mensaje}


def test_solo_unicidad_de_dni_o_cuenta_es_conflicto_de_paciente():
    from sqlalchemy.exc import IntegrityError
    from app.application.errors_pacientes import conflicto_paciente

    class FalloPostgres(Exception):
        sqlstate = "23505"
        constraint_name = "uq_paciente_consultorio_dni"

    error = IntegrityError("INSERT", {}, FalloPostgres("detalle privado"))
    assert conflicto_paciente(error) is True


@pytest.mark.parametrize("estado,constraint,esperado", [
    ("23505", "uq_paciente_usuario_id", True),
    ("23505", "uq_usuario_consultorio_email", False),
    ("23503", "fk_solicitud_paciente", False),
    ("40P01", None, True),
    ("40001", None, True),
    (None, None, False),
])
def test_conflictos_selectivos_no_ocultan_otras_restricciones(estado, constraint, esperado):
    from sqlalchemy.exc import DBAPIError
    from app.application.errors_pacientes import conflicto_paciente

    original = RuntimeError("detalle privado")
    original.sqlstate = estado
    original.constraint_name = constraint
    assert conflicto_paciente(DBAPIError("UPDATE", {}, original)) is esperado


def test_constraint_del_driver_asyncpg_se_recupera_de_la_causa():
    from sqlalchemy.exc import IntegrityError
    from app.application.errors_pacientes import conflicto_paciente

    driver = RuntimeError("detalle privado")
    driver.sqlstate = "23505"
    driver.constraint_name = "uq_paciente_usuario_id"
    adaptado = RuntimeError("adaptador")
    adaptado.sqlstate = "23505"
    adaptado.__cause__ = driver
    assert conflicto_paciente(IntegrityError("UPDATE", {}, adaptado)) is True
