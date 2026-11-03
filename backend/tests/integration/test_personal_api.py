from datetime import datetime, timezone

import httpx
import pytest
from sqlalchemy import select

from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import UsuarioModel
from app.main import create_app

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def personal_app(sesiones, url_base):
    from tests.integration.test_core_models import crear_consultorio_ejemplo

    async with sesiones() as session:
        session.add_all((crear_consultorio_ejemplo(1), crear_consultorio_ejemplo(2)))
        await session.commit()
    settings = Settings(
        database_url=url_base,
        jwt_secret_key="j" * 32,
        origin_hash_secret="o" * 32,
        app_env="test",
        consultorio_activo_id=1,
        cookie_secure=False,
    )
    app = create_app(settings)
    from app.api.v1.routers.personal import router
    if not any(getattr(route, "path", "").startswith("/api/v1/usuarios") for route in app.routes):
        app.include_router(router)
    app.state.session_factory = sesiones
    app.state.token_service = AuthTokenService(RelojSimulado(AHORA), "j" * 32)
    return app


def auth_header(rol=RolUsuario.ADMINISTRADOR, consultorio_id=1, usuario_id=900):
    token = AuthTokenService(RelojSimulado(AHORA), "j" * 32).emitir_access_token(
        Principal(usuario_id=usuario_id, consultorio_id=consultorio_id, rol=rol)
    )
    return {"Authorization": f"Bearer {token}"}


async def test_administrador_crea_cuenta_de_personal_en_su_consultorio(personal_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=personal_app), base_url="http://test") as client:
        response = await client.post("/api/v1/usuarios", headers=auth_header(), json={
            "nombre_usuario": "  recep  ", "email": " RECEP@example.test ",
            "password": "Clave-123456789", "rol": "recepcion",
        })
    assert response.status_code == 201
    assert response.json()["rol"] == "recepcion"
    assert response.json()["nombre_usuario"] == "recep"
    assert "password" not in response.json()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=personal_app), base_url="http://test") as client:
        listing = await client.get("/api/v1/usuarios", headers=auth_header())
    assert listing.status_code == 200
    assert [user["nombre_usuario"] for user in listing.json()] == ["recep"]


async def test_alta_rechaza_paciente_roles_multiples_y_consultorio_del_cliente(personal_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=personal_app), base_url="http://test") as client:
        for payload in (
            {"nombre_usuario": "pac", "email": "p@example.test", "password": "Clave-123456789", "rol": "paciente"},
            {"nombre_usuario": "multi", "email": "m@example.test", "password": "Clave-123456789", "rol": ["recepcion", "profesional"]},
            {"nombre_usuario": "tenant", "email": "t@example.test", "password": "Clave-123456789", "rol": "recepcion", "consultorio_id": 2},
        ):
            response = await client.post("/api/v1/usuarios", headers=auth_header(), json=payload)
            assert response.status_code == 422


async def test_otro_rol_no_puede_escribir_personal(personal_app):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=personal_app), base_url="http://test") as client:
        response = await client.post("/api/v1/usuarios", headers=auth_header(RolUsuario.RECEPCION), json={
            "nombre_usuario": "nuevo", "email": "nuevo@example.test",
            "password": "Clave-123456789", "rol": "recepcion",
        })
    assert response.status_code == 403


async def test_actualizacion_y_baja_preservan_usuario_y_no_filtran_otro_consultorio(personal_app, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=personal_app), base_url="http://test") as client:
        creada = await client.post("/api/v1/usuarios", headers=auth_header(), json={
            "nombre_usuario": "odontologa", "email": "odonto@example.test",
            "password": "Clave-123456789", "rol": "profesional",
        })
        assert creada.status_code == 201
        user_id = creada.json()["id"]
        incompatible = await client.patch(f"/api/v1/usuarios/{user_id}", headers=auth_header(), json={"rol": "paciente"})
        assert incompatible.status_code == 422
        update = await client.patch(f"/api/v1/usuarios/{user_id}", headers=auth_header(), json={"email": "editada@example.test"})
        assert update.status_code == 200
        assert update.json()["email"] == "editada@example.test"
        listing = await client.get("/api/v1/usuarios", headers=auth_header(consultorio_id=2))
        assert listing.status_code == 200
        assert listing.json() == []
        deleted = await client.delete(f"/api/v1/usuarios/{user_id}", headers=auth_header())
        assert deleted.status_code == 204
    async with sesiones() as session:
        user = await session.scalar(select(UsuarioModel).where(UsuarioModel.id == user_id))
        assert user is not None
        assert user.activo is False
        assert user.email == "editada@example.test"

