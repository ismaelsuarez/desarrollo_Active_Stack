from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_reloj
from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import ConsultorioModel
from app.main import create_app
from tests.integration.test_core_models import crear_consultorio_ejemplo

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def consultorio_app(sesiones, url_base):
    async with sesiones() as sesion:
        sesion.add_all((crear_consultorio_ejemplo(1), crear_consultorio_ejemplo(2)))
        await sesion.commit()
    settings = Settings(
        database_url=url_base,
        jwt_secret_key="j" * 32,
        origin_hash_secret="o" * 32,
        app_env="test",
        consultorio_activo_id=1,
        cookie_secure=False,
    )
    app = create_app(settings)
    app.state.session_factory = sesiones
    app.dependency_overrides[get_reloj] = lambda: RelojSimulado(AHORA)
    return app


def authorization(rol=RolUsuario.ADMINISTRADOR, consultorio_id=1):
    token = AuthTokenService(RelojSimulado(AHORA), "j" * 32).emitir_access_token(
        Principal(usuario_id=10, consultorio_id=consultorio_id, rol=rol)
    )
    return {"Authorization": f"Bearer {token}"}


async def test_administrador_consulta_y_actualiza_configuracion_del_consultorio(
    consultorio_app,
    sesiones,
):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=consultorio_app), base_url="http://test"
    ) as cliente:
        headers = authorization()
        inicial = await cliente.get("/api/v1/consultorio", headers=headers)
        assert inicial.status_code == 200
        assert inicial.json()["minutos_granularidad"] == 15

        payload = {
            "modo_liberacion": "manual",
            "horas_confirmacion": 72,
            "horas_recordatorio": 48,
            "horas_liberacion": 24,
            "horas_limite_paciente": 30,
            "telefono": "1144556677",
            "minutos_granularidad": 30,
            "dias_anticipacion_maxima": 90,
            "max_turnos_activos_paciente": 3,
        }
        actualizada = await cliente.patch(
            "/api/v1/consultorio", headers=headers, json=payload
        )
        assert actualizada.status_code == 200
        assert {k: actualizada.json()[k] for k in payload} == payload
        consultorio_ajeno = await cliente.get(
            "/api/v1/consultorio", headers=authorization(consultorio_id=2)
        )
        assert consultorio_ajeno.status_code == 200
        assert consultorio_ajeno.json()["minutos_granularidad"] == 15

    async with sesiones() as sesion:
        consultorio = await sesion.scalar(
            select(ConsultorioModel).where(ConsultorioModel.id == 1)
        )
        assert consultorio is not None
        assert consultorio.modo_liberacion == "manual"
        assert consultorio.telefono == "1144556677"
        assert consultorio.max_turnos_activos_paciente == 3


@pytest.mark.parametrize(
    "cambios",
    [
        {"minutos_granularidad": 4},
        {"minutos_granularidad": 121},
        {"dias_anticipacion_maxima": 0},
        {"max_turnos_activos_paciente": 0},
        {"modo_liberacion": "inmediato"},
        {"horas_confirmacion": 24},
        {"horas_recordatorio": 48},
        {"horas_liberacion": 0},
        {"horas_limite_paciente": 0},
        {"telefono": " "},
        {"telefono": "1" * 41},
    ],
)
async def test_configuracion_invalida_responde_422_y_preserva_valores(
    consultorio_app,
    sesiones,
    cambios,
):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=consultorio_app), base_url="http://test"
    ) as cliente:
        respuesta = await cliente.patch(
            "/api/v1/consultorio", headers=authorization(), json=cambios
        )
        assert respuesta.status_code == 422

    async with sesiones() as sesion:
        consultorio = await sesion.scalar(
            select(ConsultorioModel).where(ConsultorioModel.id == 1)
        )
        assert consultorio is not None
        assert consultorio.horas_confirmacion == 48
        assert consultorio.horas_recordatorio == 24
        assert consultorio.horas_liberacion == 12
        assert consultorio.minutos_granularidad == 15
        assert consultorio.dias_anticipacion_maxima == 60
        assert consultorio.max_turnos_activos_paciente == 2
        assert consultorio.modo_liberacion == "automatico"


async def test_configuracion_exige_administrador_y_cuerpo_estricto(consultorio_app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=consultorio_app), base_url="http://test"
    ) as cliente:
        for rol in (RolUsuario.RECEPCION, RolUsuario.PROFESIONAL, RolUsuario.PACIENTE):
            lectura = await cliente.get("/api/v1/consultorio", headers=authorization(rol))
            escritura = await cliente.patch(
                "/api/v1/consultorio",
                headers=authorization(rol),
                json={"telefono": "1199887766"},
            )
            assert lectura.status_code == escritura.status_code == 403

        extra = await cliente.patch(
            "/api/v1/consultorio",
            headers=authorization(),
            json={"telefono": "1199887766", "consultorio_id": 2},
        )
        assert extra.status_code == 422


@pytest.mark.parametrize(
    "cambios",
    [
        {"horas_confirmacion": 24},
        {"horas_recordatorio": 48},
        {"horas_liberacion": 0},
        {"horas_limite_paciente": 0},
        {"modo_liberacion": "inmediato"},
        {"minutos_granularidad": 4},
        {"minutos_granularidad": 121},
        {"dias_anticipacion_maxima": 0},
        {"max_turnos_activos_paciente": 0},
        {"telefono": " "},
        {"telefono": "1" * 41},
    ],
)
async def test_postgresql_rechaza_directamente_parametros_que_la_api_rechaza(
    consultorio_app,
    sesiones,
    cambios,
):
    async with sesiones() as sesion:
        with pytest.raises(IntegrityError):
            await sesion.execute(
                update(ConsultorioModel)
                .where(ConsultorioModel.id == 1)
                .values(**cambios)
            )
            await sesion.commit()
        await sesion.rollback()


async def test_consultorio_permite_quitar_el_telefono(sesiones, consultorio_app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=consultorio_app), base_url="http://test"
    ) as cliente:
        respuesta = await cliente.patch(
            "/api/v1/consultorio",
            headers=authorization(),
            json={"telefono": None},
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["telefono"] is None

    async with sesiones() as sesion:
        consultorio = await sesion.scalar(
            select(ConsultorioModel).where(ConsultorioModel.id == 1)
        )
        assert consultorio is not None
        assert consultorio.telefono is None


async def test_openapi_expone_configuracion_y_schemas_estrictos(consultorio_app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=consultorio_app), base_url="http://test"
    ) as cliente:
        esquema = (await cliente.get("/openapi.json")).json()

    assert set(esquema["paths"]["/api/v1/consultorio"]) == {"get", "patch"}
    cuerpo = esquema["paths"]["/api/v1/consultorio"]["patch"]["requestBody"]
    nombre_schema = cuerpo["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
    assert esquema["components"]["schemas"][nombre_schema]["additionalProperties"] is False
