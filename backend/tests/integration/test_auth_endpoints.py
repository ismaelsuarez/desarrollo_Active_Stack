from datetime import datetime, timezone
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.domain.services.auth_crypto import hashear_password
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel
from app.main import create_app
from app.core.config import Settings
from app.api.deps import get_reloj

pytestmark = pytest.mark.integration

JWT_SECRET = "jwt-secret-for-api-tests-32-bytes-minimum"
ORIGIN_SECRET = "origin-hash-secret-for-api-tests-32-bytes"
AHORA = datetime(2026, 10, 30, 19, 0, 0, tzinfo=timezone.utc)


def crear_test_app(db_url: str, reloj: RelojSimulado):
    settings = Settings(
        database_url=db_url,
        jwt_secret_key=JWT_SECRET,
        origin_hash_secret=ORIGIN_SECRET,
        app_env="test",
        consultorio_activo_id=1,
        trusted_proxy_hops=0,
        login_max_attempts=5,
        login_lockout_minutes=15,
        login_max_attempts_per_origin=20,
        cookie_secure=False,
    )
    app = create_app(settings)
    app.dependency_overrides[get_reloj] = lambda: reloj
    return app


async def sembrar_datos_base(sesion: AsyncSession):
    consultorio = ConsultorioModel(
        id=1,
        nombre="Consultorio API Test",
        telefono="12345678",
        direccion="Av. Siempre Viva 123",
        zona_horaria="America/Argentina/Buenos_Aires",
        modo_liberacion="automatico",
        horas_confirmacion=48,
        horas_recordatorio=24,
        horas_liberacion=12,
        horas_limite_paciente=24,
        minutos_granularidad=15,
        dias_anticipacion_maxima=60,
        max_turnos_activos_paciente=2,
        activo=True,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    sesion.add(consultorio)
    await sesion.flush()

    admin = UsuarioModel(
        consultorio_id=1,
        nombre_usuario="admin",
        email="admin@test.com",
        password_hash=hashear_password("AdminPass123!"),
        rol=RolUsuario.ADMINISTRADOR.value,
        activo=True,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    paciente_no_verificado = UsuarioModel(
        consultorio_id=1,
        nombre_usuario="paciente_nov",
        email="nov@test.com",
        password_hash=hashear_password("PacientePass123!"),
        rol=RolUsuario.PACIENTE.value,
        email_verificado=False,
        aviso_privacidad_aceptado_en=AHORA,
        aviso_privacidad_version="1.0",
        activo=True,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    recepcion = UsuarioModel(
        consultorio_id=1,
        nombre_usuario="recepcionista",
        email="recepcion@test.com",
        password_hash=hashear_password("RecepcionPass123!"),
        rol=RolUsuario.RECEPCION.value,
        activo=True,
        creado_en=AHORA,
        actualizado_en=AHORA,
    )
    sesion.add_all([admin, paciente_no_verificado, recepcion])
    await sesion.commit()


async def test_flujo_completo_login_me_refresh_logout(
    sesiones: async_sessionmaker[AsyncSession],
    url_base: str,
):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        await sembrar_datos_base(sesion)

    app = crear_test_app(url_base, reloj)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 1. Login exitoso
        resp_login = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "admin", "password": "AdminPass123!"},
        )
        assert resp_login.status_code == 200
        data_login = resp_login.json()
        assert "access_token" in data_login
        assert data_login["token_type"] == "bearer"
        assert "refresh_token" in resp_login.cookies
        access_token = data_login["access_token"]

        # 2. GET /me autenticado
        resp_me = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert resp_me.status_code == 200
        data_me = resp_me.json()
        assert data_me["nombre_usuario"] == "admin"
        assert data_me["rol"] == "administrador"
        assert data_me["consultorio_id"] == 1

        # 3. POST /refresh rotando sesión
        resp_refresh = await client.post("/api/v1/auth/refresh")
        assert resp_refresh.status_code == 200
        data_refresh = resp_refresh.json()
        assert "access_token" in data_refresh
        assert data_refresh["access_token"] != access_token
        nuevo_token = data_refresh["access_token"]

        # 4. GET /me con nuevo token funciona
        resp_me2 = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {nuevo_token}"},
        )
        assert resp_me2.status_code == 200

        # 5. POST /logout revoca y elimina cookie
        resp_logout = await client.post("/api/v1/auth/logout")
        assert resp_logout.status_code == 200
        assert "refresh_token" not in client.cookies or client.cookies.get("refresh_token") == ""

        # 6. Intentar refrescar tras logout falla con 401
        resp_refresh_post_logout = await client.post("/api/v1/auth/refresh")
        assert resp_refresh_post_logout.status_code == 401


async def test_login_credenciales_erroneas_y_paciente_no_verificado(
    sesiones: async_sessionmaker[AsyncSession],
    url_base: str,
):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        await sembrar_datos_base(sesion)

    app = crear_test_app(url_base, reloj)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Credenciales erróneas -> 401
        resp_err = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "admin", "password": "WrongPassword!"},
        )
        assert resp_err.status_code == 401
        assert resp_err.json()["detail"] == "Credenciales inválidas"

        # Paciente no verificado con clave correcta -> 403 (RN-02)
        resp_nov = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "paciente_nov", "password": "PacientePass123!"},
        )
        assert resp_nov.status_code == 403
        assert "verificación" in resp_nov.json()["detail"].lower()


async def test_login_rate_limiting_bloquea_sexto_intento(
    sesiones: async_sessionmaker[AsyncSession],
    url_base: str,
):
    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        await sembrar_datos_base(sesion)

    app = crear_test_app(url_base, reloj)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # 5 intentos fallidos
        for _ in range(5):
            res = await client.post(
                "/api/v1/auth/login",
                json={"identificador": "admin", "password": "BadPassword!"},
            )
            assert res.status_code == 401

        # 6to intento: bloqueado con 401 incluso si la contraseña fuera la correcta
        res6 = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "admin", "password": "AdminPass123!"},
        )
        assert res6.status_code == 401
        assert res6.json()["detail"] == "Credenciales inválidas"


async def test_endpoint_protegido_con_requiere_rol(
    sesiones: async_sessionmaker[AsyncSession],
    url_base: str,
):
    from fastapi import Depends
    from app.api.deps import requiere_rol

    reloj = RelojSimulado(AHORA)
    async with sesiones() as sesion:
        await sembrar_datos_base(sesion)

    app = crear_test_app(url_base, reloj)

    # Endpoint protegido para testear RBAC
    @app.get("/api/v1/solo-admin")
    async def ruta_admin(principal: Principal = Depends(requiere_rol(RolUsuario.ADMINISTRADOR))):
        return {"ok": True, "user": principal.usuario_id}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Login como recepcionista
        resp_rec = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "recepcionista", "password": "RecepcionPass123!"},
        )
        token_rec = resp_rec.json()["access_token"]

        # Intento de acceder a ruta admin con token de recepcionista -> 403
        resp_denegado = await client.get(
            "/api/v1/solo-admin",
            headers={"Authorization": f"Bearer {token_rec}"},
        )
        assert resp_denegado.status_code == 403

        # Login como admin
        resp_adm = await client.post(
            "/api/v1/auth/login",
            json={"identificador": "admin", "password": "AdminPass123!"},
        )
        token_adm = resp_adm.json()["access_token"]

        # Acceso con admin -> 200
        resp_permitido = await client.get(
            "/api/v1/solo-admin",
            headers={"Authorization": f"Bearer {token_adm}"},
        )
        assert resp_permitido.status_code == 200
        assert resp_permitido.json()["ok"] is True
