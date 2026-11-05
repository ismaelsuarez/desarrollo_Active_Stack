from datetime import timedelta
import asyncio
from dataclasses import replace

import httpx
import pytest
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
from app.infrastructure.db.historial import RepositorioHistorialSQL
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with sesiones() as session:
        patient = await session.get(PacienteModel, escenario.pacientes[1])
        patient.email = "ana@example.test"
        await session.commit()
    return escenario


async def test_staff_reschedule_saves_notice_with_new_cycle_in_same_transaction(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        response = await client.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(),
                                      json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert response.status_code == 200, response.text
    async with sesiones() as session:
        notice = (await session.scalars(select(NotificacionModel))).one()
        assert (notice.turno_id, notice.tipo, notice.ciclo, notice.estado) == (tid, "reprogramacion_por_personal", 2, "programada")
        assert notice.destinatario == "ana@example.test"
        assert notice.intentos == 0
        assert notice.reclamada_en is None


@pytest.mark.parametrize("rol", ["recepcion", "administrador"])
async def test_staff_cancellation_saves_notice_for_current_cycle(escenario, sesiones, rol):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        response = await client.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers(rol), json={"motivo": "dato clínico interno"})
    assert response.status_code == 200, response.text
    async with sesiones() as session:
        notice = (await session.scalars(select(NotificacionModel))).one()
        assert (notice.turno_id, notice.tipo, notice.ciclo) == (tid, "cancelacion_por_personal", 1)
        assert "cancelado" in notice.mensaje
        assert "dato clínico" not in notice.mensaje


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
@pytest.mark.parametrize("fallo", ["insertar", "historial", "commit"])
async def test_notice_failure_rolls_back_turn_and_history(escenario, sesiones, monkeypatch, accion, fallo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        async with sesiones() as session:
            original = await session.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid})
        async def fallar(*args, **kwargs):
            raise RuntimeError("fallo controlado sin datos")
        if fallo == "insertar":
            monkeypatch.setattr(RepositorioAvisosDeTurnoSQL, "programar_aviso_personal", fallar)
        elif fallo == "historial":
            monkeypatch.setattr(RepositorioHistorialSQL, "agregar", fallar)
        else:
            monkeypatch.setattr(AsyncSession, "commit", fallar)
        if accion == "cancelar":
            response = await client.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers(), json={})
        else:
            response = await client.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert response.status_code == 500
    async with sesiones() as session:
        assert await session.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid}) == original
        assert await session.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": tid}) == 1
        assert await session.scalar(text("SELECT count(*) FROM notificacion")) == 0


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
@pytest.mark.parametrize("contacto", [None, ""])
async def test_missing_contact_does_not_prevent_staff_change_or_invent_recipient(escenario, sesiones, accion, contacto, caplog):
    import logging
    caplog.set_level(logging.INFO)
    async with sesiones() as session:
        patient = await session.get(PacienteModel, escenario.pacientes[1])
        patient.email = contacto
        await session.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        if accion == "cancelar":
            response = await client.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers(), json={})
        else:
            response = await client.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert response.status_code == 200
    async with sesiones() as session:
        assert await session.scalar(text("SELECT count(*) FROM notificacion")) == 0
    assert "aviso_personal_sin_contacto" in caplog.text
    assert "ana@example.test" not in caplog.text and "12345671" not in caplog.text


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
async def test_patient_change_does_not_create_staff_notice(escenario, sesiones, accion):
    async with sesiones() as session:
        patient = await session.get(PacienteModel, escenario.pacientes[1])
        patient.usuario_id = escenario.usuarios[1, "paciente"]
        await session.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        if accion == "cancelar":
            response = await client.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers("paciente"), json={})
        else:
            response = await client.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers("paciente"), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert response.status_code == 200
    async with sesiones() as session:
        assert await session.scalar(text("SELECT count(*) FROM notificacion")) == 0


async def test_reschedule_notice_keeps_snapshot_after_later_change(escenario, sesiones):
    async with sesiones() as session:
        patient = await session.get(PacienteModel, escenario.pacientes[1])
        patient.notas, patient.obra_social = "salud confidencial", "obra privada"
        await session.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        tid = created.json()["id"]
        for dia in (1, 2):
            response = await client.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers("administrador"), json={"inicio": (INICIO+timedelta(days=dia)).isoformat()})
            assert response.status_code == 200
    async with sesiones() as session:
        rows = (await session.scalars(select(NotificacionModel).order_by(NotificacionModel.id))).all()
        assert [row.ciclo for row in rows] == [2, 3]
        assert "10/11/2026 10:00" in rows[0].mensaje
        assert "11/11/2026 10:00" in rows[1].mensaje
        assert all("Ana Prueba" in row.mensaje and "Patricia Dental" in row.mensaje and "Consultorio Centro" in row.mensaje for row in rows)
        assert all(private not in row.mensaje for row in rows for private in ("12345671", "salud confidencial", "obra privada", "Consulta"))


async def test_exact_duplicate_programming_is_noop_with_two_connections(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    tid = created.json()["id"]
    barrier = asyncio.Barrier(2)
    pids = set()
    async def programar():
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            pids.add(await unidad._sesion.scalar(text("SELECT pg_backend_pid()")))
            turno = await unidad.turnos.obtener(1, tid)
            await barrier.wait()
            return await unidad.notificaciones.programar_aviso_personal(turno, "cancelar", escenario.reloj.ahora())
    results = await asyncio.wait_for(asyncio.gather(programar(), programar()), 5)
    assert len(pids) == 2
    assert sum(result is not None for result in results) == 1
    async with sesiones() as session:
        assert await session.scalar(text("SELECT count(*) FROM notificacion")) == 1


async def test_programmer_does_not_commit_and_does_not_hide_real_fk_errors(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    tid = created.json()["id"]
    with pytest.raises(RuntimeError):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            turno = await unidad.turnos.obtener(1, tid)
            await unidad.notificaciones.programar_aviso_personal(turno, "cancelar", escenario.reloj.ahora())
            raise RuntimeError("fallo despues de programar")
    async with sesiones() as session:
        assert await session.scalar(text("SELECT count(*) FROM notificacion")) == 0
    with pytest.raises(IntegrityError):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            turno = await unidad.turnos.obtener(1, tid)
            await unidad.notificaciones.programar_aviso_personal(replace(turno, id=999999), "cancelar", escenario.reloj.ahora())
