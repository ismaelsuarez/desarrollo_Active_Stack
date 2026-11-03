from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import PrestacionModel
from app.infrastructure.db.models import TurnoModel
from app.main import create_app
from tests.integration.test_core_models import crear_consultorio_ejemplo
from tests.integration.fabricas import crear_profesional, crear_turno, hora

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def prestaciones_app(sesiones, url_base):
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
    app.state.token_service = AuthTokenService(RelojSimulado(AHORA), "j" * 32)
    return app


def authorization(prestaciones_app, rol=RolUsuario.ADMINISTRADOR, consultorio_id=1):
    token = AuthTokenService(RelojSimulado(AHORA), "j" * 32).emitir_access_token(
        Principal(usuario_id=10, consultorio_id=consultorio_id, rol=rol)
    )
    return {"Authorization": f"Bearer {token}"}


async def test_catalogo_crear_listar_editar_y_desactivar_preserva_turno_existente(
    prestaciones_app,
    sesiones,
):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        headers = authorization(prestaciones_app)
        creada = await cliente.post(
            "/api/v1/prestaciones",
            headers=headers,
            json={"nombre": "Evaluación nueva", "duracion_min": 35},
        )
        assert creada.status_code == 201
        assert creada.json() == {
            "id": creada.json()["id"],
            "nombre": "Evaluación nueva",
            "duracion_min": 35,
            "activa": True,
            "sugerida": False,
        }
        id_prestacion = creada.json()["id"]

        listado = await cliente.get("/api/v1/prestaciones", headers=headers)
        assert listado.status_code == 200
        assert [fila["nombre"] for fila in listado.json()] == ["Evaluación nueva"]

        actualizada = await cliente.patch(
            f"/api/v1/prestaciones/{id_prestacion}",
            headers=headers,
            json={"duracion_min": 50},
        )
        assert actualizada.status_code == 200
        assert actualizada.json()["duracion_min"] == 50
        desactivada = await cliente.patch(
            f"/api/v1/prestaciones/{id_prestacion}",
            headers=headers,
            json={"activa": False},
        )
        assert desactivada.status_code == 200
        assert desactivada.json()["activa"] is False

    async with sesiones() as sesion:
        persistida = await sesion.scalar(
            select(PrestacionModel).where(PrestacionModel.id == id_prestacion)
        )
        assert persistida is not None
        assert persistida.duracion_min == 50
        assert persistida.activa is False


async def test_catalogo_rechaza_duracion_invalida_nombre_duplicado_y_campos_extra(
    prestaciones_app,
):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        headers = authorization(prestaciones_app)
        datos = {"nombre": "Consulta", "duracion_min": 30}
        assert (await cliente.post("/api/v1/prestaciones", headers=headers, json=datos)).status_code == 201
        duplicada = await cliente.post("/api/v1/prestaciones", headers=headers, json=datos)
        assert duplicada.status_code == 409
        invalida = await cliente.post(
            "/api/v1/prestaciones", headers=headers,
            json={"nombre": "Duración cero", "duracion_min": 0},
        )
        assert invalida.status_code == 422
        extra = await cliente.post(
            "/api/v1/prestaciones", headers=headers,
            json={**datos, "consultorio_id": 2},
        )
        assert extra.status_code == 422


@pytest.mark.parametrize("duracion", [0, -1])
async def test_catalogo_rechaza_toda_duracion_no_positiva(prestaciones_app, duracion):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        respuesta = await cliente.post(
            "/api/v1/prestaciones",
            headers=authorization(prestaciones_app),
            json={"nombre": "Duración inválida", "duracion_min": duracion},
        )
    assert respuesta.status_code == 422


async def test_editar_duracion_no_cambia_un_turno_ya_guardado(prestaciones_app, sesiones, engine):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        respuesta = await cliente.post(
            "/api/v1/prestaciones",
            headers=authorization(prestaciones_app),
            json={"nombre": "Duración histórica", "duracion_min": 35},
        )
        id_prestacion = respuesta.json()["id"]
        profesional_id = await crear_profesional(engine)
        turno_id = await crear_turno(
            engine,
            profesional_id=profesional_id,
            prestacion_id=id_prestacion,
            inicio=hora(10),
            duracion_min=35,
        )
        actualizada = await cliente.patch(
            f"/api/v1/prestaciones/{id_prestacion}",
            headers=authorization(prestaciones_app),
            json={"duracion_min": 60},
        )
        assert actualizada.status_code == 200

    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, turno_id)
        assert turno is not None
        assert turno.fin == hora(10, 35)


async def test_catalogo_restringe_escrituras_y_a_isla_por_principal(prestaciones_app, sesiones):
    async with sesiones() as sesion:
        ajena = PrestacionModel(
            consultorio_id=2, nombre="De otro consultorio", duracion_min=25,
            activa=True, sugerida=False,
        )
        sesion.add(ajena)
        await sesion.flush()
        id_ajena = ajena.id
        await sesion.commit()

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        recepcion = authorization(prestaciones_app, RolUsuario.RECEPCION)
        prohibida = await cliente.post(
            "/api/v1/prestaciones", headers=recepcion,
            json={"nombre": "No autorizado", "duracion_min": 20},
        )
        assert prohibida.status_code == 403

        admin = authorization(prestaciones_app)
        ajena = await cliente.patch(
            f"/api/v1/prestaciones/{id_ajena}", headers=admin,
            json={"duracion_min": 55},
        )
        assert ajena.status_code == 404
        listado = await cliente.get("/api/v1/prestaciones", headers=admin)
        assert listado.status_code == 200
        assert listado.json() == []


async def test_openapi_publica_contratos_cerrados_y_errores_del_catalogo(prestaciones_app):
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=prestaciones_app), base_url="http://test"
    ) as cliente:
        esquema = (await cliente.get("/openapi.json")).json()

    rutas = esquema["paths"]
    assert set(rutas["/api/v1/prestaciones"]) == {"get", "post"}
    assert set(rutas["/api/v1/prestaciones/{prestacion_id}"]) == {"patch", "delete"}
    assert "409" in rutas["/api/v1/prestaciones"]["post"]["responses"]
    assert "404" in rutas["/api/v1/prestaciones/{prestacion_id}"]["patch"]["responses"]
    assert (
        esquema["components"]["schemas"]["PrestacionEntrada"]["additionalProperties"]
        is False
    )
