from datetime import datetime, timezone
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select

from app.application.services.token_service import AuthTokenService
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import BoxModel, HorarioSemanalModel, ProfesionalModel
from app.main import create_app
from tests.integration.test_core_models import crear_consultorio_ejemplo

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
async def agenda_app(sesiones, url_base):
    async with sesiones() as sesion:
        sesion.add_all((crear_consultorio_ejemplo(1), crear_consultorio_ejemplo(2)))
        from app.infrastructure.db.models import UsuarioModel
        sesion.add(UsuarioModel(
            id=10, consultorio_id=1, nombre_usuario="admin-api", email="admin-api@example.test",
            password_hash="hash", rol="administrador", activo=True,
            creado_en=AHORA, actualizado_en=AHORA,
        ))
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


def headers(app, rol=RolUsuario.ADMINISTRADOR, consultorio_id=1, usuario_id=10):
    token = AuthTokenService(RelojSimulado(AHORA), "j" * 32).emitir_access_token(
        Principal(usuario_id=usuario_id, consultorio_id=consultorio_id, rol=rol)
    )
    return {"Authorization": f"Bearer {token}"}


async def crear_usuario_profesional(sesiones, consultorio_id=1):
    from app.infrastructure.db.models import UsuarioModel
    async with sesiones() as sesion:
        usuario = UsuarioModel(
            consultorio_id=consultorio_id,
            nombre_usuario=f"prof{consultorio_id}-{uuid4().hex[:8]}",
            email=f"prof{consultorio_id}-{uuid4().hex[:8]}@example.test",
            password_hash="argon-placeholder",
            rol="profesional",
            activo=True,
            creado_en=AHORA,
            actualizado_en=AHORA,
        )
        sesion.add(usuario)
        await sesion.commit()
        return usuario.id


async def test_admin_creates_exclusive_box_professional_and_nonoverlapping_schedule(agenda_app, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        auth = headers(agenda_app)
        box = await client.post("/api/v1/boxes", headers=auth, json={"nombre": "Box A"})
        assert box.status_code == 201
        usuario_id = await crear_usuario_profesional(sesiones)
        professional = await client.post("/api/v1/profesionales", headers=auth, json={
            "usuario_id": usuario_id, "box_id": box.json()["id"], "nombre": "Ada", "apellido": "Lovelace"
        })
        assert professional.status_code == 201
        professional_id = professional.json()["id"]
        schedule = await client.put(f"/api/v1/profesionales/{professional_id}/horario-semanal", headers=auth, json={
            "bloques": [
                {"dia_semana": 1, "hora_inicio": "09:00", "hora_fin": "12:00"},
                {"dia_semana": 1, "hora_inicio": "12:00", "hora_fin": "14:00"},
            ]
        })
        assert schedule.status_code == 200
        assert len(schedule.json()["bloques"]) == 2
        before = await client.get(f"/api/v1/profesionales/{professional_id}/horario-semanal", headers=auth)
        overlap = await client.put(f"/api/v1/profesionales/{professional_id}/horario-semanal", headers=auth, json={
            "bloques": [
                {"dia_semana": 1, "hora_inicio": "09:00", "hora_fin": "12:30"},
                {"dia_semana": 1, "hora_inicio": "12:00", "hora_fin": "14:00"},
            ]
        })
        assert overlap.status_code == 422
        after = await client.get(f"/api/v1/profesionales/{professional_id}/horario-semanal", headers=auth)
        assert after.json() == before.json()


async def test_schedule_and_boxes_are_tenant_scoped_and_write_admin_only(agenda_app, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        denied = await client.post("/api/v1/boxes", headers=headers(agenda_app, RolUsuario.PROFESIONAL), json={"nombre": "Nope"})
        assert denied.status_code == 403
        created = await client.post("/api/v1/boxes", headers=headers(agenda_app), json={"nombre": "Box A"})
        assert created.status_code == 201
        other = await client.get("/api/v1/boxes", headers=headers(agenda_app, consultorio_id=2))
        assert other.json() == []
        extra = await client.post("/api/v1/boxes", headers=headers(agenda_app), json={"nombre": "B", "consultorio_id": 2})
        assert extra.status_code == 422

async def test_professional_rejects_incompatible_account_duplicate_box_and_cross_tenant_references(agenda_app, sesiones):
    from app.infrastructure.db.models import UsuarioModel
    async with sesiones() as session:
        incompatible = UsuarioModel(
            consultorio_id=1, nombre_usuario="recep", email="recep@example.test",
            password_hash="hash", rol="recepcion", activo=True,
            creado_en=AHORA, actualizado_en=AHORA,
        )
        foreign = UsuarioModel(
            consultorio_id=2, nombre_usuario="otro", email="otro@example.test",
            password_hash="hash", rol="profesional", activo=True,
            creado_en=AHORA, actualizado_en=AHORA,
        )
        session.add_all((incompatible, foreign))
        await session.commit()
        incompatible_id, foreign_id = incompatible.id, foreign.id
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        auth = headers(agenda_app)
        box = await client.post("/api/v1/boxes", headers=auth, json={"nombre": "Box A"})
        box_id = box.json()["id"]
        prof_id = await crear_usuario_profesional(sesiones)
        body = {"usuario_id": prof_id, "box_id": box_id, "nombre": "Ada", "apellido": "Lovelace"}
        first = await client.post("/api/v1/profesionales", headers=auth, json=body)
        assert first.status_code == 201
        duplicate_box_user = await crear_usuario_profesional(sesiones)
        duplicate = await client.post("/api/v1/profesionales", headers=auth, json={**body, "usuario_id": duplicate_box_user})
        assert duplicate.status_code == 409
        wrong_role = await client.post("/api/v1/profesionales", headers=auth, json={**body, "usuario_id": incompatible_id, "box_id": box_id + 1})
        assert wrong_role.status_code == 422
        foreign_tenant = await client.post("/api/v1/profesionales", headers=auth, json={**body, "usuario_id": foreign_id})
        assert foreign_tenant.status_code == 404
        deactivate = await client.patch(f"/api/v1/profesionales/{first.json()['id']}", headers=auth, json={"activo": False})
        assert deactivate.status_code == 200
        assert deactivate.json()["activo"] is False
    async with sesiones() as session:
        stored = await session.scalar(select(ProfesionalModel).where(ProfesionalModel.id == first.json()["id"]))
        assert stored is not None and stored.activo is False


async def test_local_block_converts_to_consultorio_zone_and_can_be_deleted(agenda_app, sesiones):
    from app.infrastructure.db.models import BloqueoAgendaModel
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        auth = headers(agenda_app)
        created = await client.post("/api/v1/bloqueos", headers=auth, json={
            "tipo": "feriado", "inicio": "2026-12-25T09:00:00",
            "fin": "2026-12-25T12:00:00", "motivo": "Feriado"
        })
        assert created.status_code == 201
        assert created.json()["inicio"] == "2026-12-25T12:00:00Z"
        listed = await client.get("/api/v1/bloqueos", headers=auth)
        assert len(listed.json()) == 1
        deleted = await client.delete(f"/api/v1/bloqueos/{created.json()['id']}", headers=auth)
        assert deleted.status_code == 204
    async with sesiones() as session:
        assert await session.scalar(select(BloqueoAgendaModel)) is None


async def test_overlap_block_reports_active_turn_without_persisting(agenda_app, sesiones):
    from tests.integration.fabricas import crear_prestacion, crear_profesional, crear_turno, hora
    from app.infrastructure.db.models import BloqueoAgendaModel
    professional_id = await crear_profesional(agenda_app.state.session_factory.kw["bind"], box_id=21)
    service_id = await crear_prestacion(agenda_app.state.session_factory.kw["bind"])
    await crear_turno(agenda_app.state.session_factory.kw["bind"], profesional_id=professional_id, prestacion_id=service_id, inicio=hora(10))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        blocked = await client.post(f"/api/v1/profesionales/{professional_id}/bloqueos", headers=headers(agenda_app), json={
            "tipo": "ausencia", "inicio": "2026-11-02T10:00:00",
            "fin": "2026-11-02T11:00:00"
        })
        assert blocked.status_code == 409
        assert blocked.json()["detail"]["turnos_afectados"]
    async with sesiones() as session:
        assert await session.scalar(select(BloqueoAgendaModel)) is None



async def test_exception_rejects_foreign_professional_and_invalid_interval(agenda_app):
    from tests.integration.fabricas import crear_profesional
    professional_id = await crear_profesional(agenda_app.state.session_factory.kw["bind"], consultorio_id=2, box_id=23)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=agenda_app), base_url="http://test") as client:
        auth = headers(agenda_app)
        foreign = await client.post(f"/api/v1/profesionales/{professional_id}/bloqueos", headers=auth, json={
            "tipo": "bloqueo", "inicio": "2026-12-25T09:00:00", "fin": "2026-12-25T10:00:00"
        })
        assert foreign.status_code == 404
        invalid = await client.post("/api/v1/bloqueos", headers=auth, json={
            "tipo": "otro", "inicio": "2026-12-25T09:00:00", "fin": "2026-12-25T09:00:00"
        })
        assert invalid.status_code == 422

