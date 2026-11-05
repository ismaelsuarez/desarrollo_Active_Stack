"""Avisos de hechos consumados con snapshot mínimo y sin SMTP transaccional."""
import asyncio
import logging
import os
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.c07_support import INICIO
from tests.integration.test_c16_planning import escenario, payload

pytestmark = pytest.mark.integration


async def test_booking_creates_one_minimal_snapshot_even_after_rescheduling(escenario, sesiones):
    async with sesiones() as s:
        p = await s.get(PacienteModel, escenario.pacientes[1])
        p.notas, p.obra_social = "historia clínica secreta", "obra privada"
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        assert r.status_code == 201
        tid = r.json()["id"]
        cambiado = await c.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
        assert cambiado.status_code == 200
    async with sesiones() as s:
        resumen = (await s.scalars(select(NotificacionModel).where(NotificacionModel.tipo == "resumen_reserva"))).one()
        assert (resumen.turno_id, resumen.ciclo, resumen.estado, resumen.destinatario) == (tid,1,"programada","ana-c16@example.test")
        assert "09/11/2026 10:00" in resumen.mensaje and "reservado" in resumen.mensaje
        assert "10/11/2026" not in resumen.mensaje
        assert all(privado not in resumen.mensaje for privado in ("12345671", "historia clínica secreta", "obra privada", "Consulta"))


@pytest.mark.parametrize("rol,accion,tipo", [
    ("paciente", "cancelar", "cancelacion_por_paciente"),
    ("recepcion", "liberar", "liberacion"),
])
async def test_patient_cancellation_and_release_create_corresponding_notice(escenario, sesiones, rol, accion, tipo):
    async with sesiones() as s:
        await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        tid = r.json()["id"]
        r = await c.post(f"/api/v1/turnos/{tid}/{accion}", headers=escenario.headers(rol), json={})
    assert r.status_code == 200, r.text
    async with sesiones() as s:
        n = (await s.scalars(select(NotificacionModel).where(NotificacionModel.tipo == tipo))).one()
        assert (n.turno_id,n.ciclo,n.estado,n.programada_para) == (tid,1,"programada",escenario.reloj.ahora())
        assert "09/11/2026 10:00" in n.mensaje
        assert await s.scalar(text("SELECT count(*) FROM notificacion WHERE tipo='cancelacion_por_personal'")) == 0


@pytest.mark.parametrize("rol", ["recepcion", "paciente"])
async def test_summary_exists_for_both_booking_actors_and_repeated_programming(escenario, sesiones, rol):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(rol), json=payload(escenario, rol))
    assert r.status_code == 201
    tid = r.json()["id"]
    async with UnidadDeTrabajoSQL(sesiones) as u:
        turno = await u.turnos.obtener(1, tid)
        assert await u.notificaciones.programar_aviso_reserva(turno, escenario.reloj.ahora()) is None
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM notificacion WHERE tipo='resumen_reserva' AND turno_id=:id"), {"id": tid}) == 1


@pytest.mark.parametrize("accion,metodo", [
    ("crear", "programar_aviso_reserva"),
    ("cancelar", "programar_aviso_cancelacion_paciente"),
    ("liberar", "programar_aviso_liberacion"),
])
async def test_notice_insert_failure_reverts_fact_and_history(escenario, sesiones, monkeypatch, accion, metodo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as c:
        if accion != "crear":
            r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
            tid = r.json()["id"]
            async with sesiones() as s:
                await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
                await s.commit()
                antes = await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid})
                avisos_antes = (await s.execute(text("SELECT id,estado FROM notificacion ORDER BY id"))).all()
        async def fallar(*args, **kwargs):
            raise RuntimeError("aviso controlado")
        monkeypatch.setattr(RepositorioAvisosDeTurnoSQL, metodo, fallar)
        if accion == "crear":
            r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        else:
            r = await c.post(f"/api/v1/turnos/{tid}/{accion}", headers=escenario.headers("paciente" if accion == "cancelar" else "recepcion"), json={})
    assert r.status_code == 500
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno_historial")) == (0 if accion == "crear" else 1)
        if accion == "crear":
            assert await s.scalar(text("SELECT count(*) FROM turno")) == await s.scalar(text("SELECT count(*) FROM notificacion")) == 0
        else:
            assert await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid}) == antes
            assert (await s.execute(text("SELECT id,estado FROM notificacion ORDER BY id"))).all() == avisos_antes


@pytest.mark.parametrize("contacto", [None, "", "invalido"])
@pytest.mark.parametrize("accion", ["crear", "cancelar", "liberar"])
async def test_missing_contact_keeps_fact_and_logs_no_patient_details(escenario, sesiones, contacto, accion, caplog):
    caplog.set_level(logging.INFO)
    async with sesiones() as s:
        p = await s.get(PacienteModel, escenario.pacientes[1])
        p.email = contacto
        await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        assert r.status_code == 201
        if accion != "crear":
            r = await c.post(f"/api/v1/turnos/{r.json()['id']}/{accion}", headers=escenario.headers("paciente" if accion == "cancelar" else "recepcion"), json={})
            assert r.status_code == 200
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM notificacion")) == 0
        assert await s.scalar(text("SELECT estado FROM turno")) == {"crear":"pendiente","cancelar":"cancelado","liberar":"liberado"}[accion]
    assert "aviso_turno_sin_contacto" in caplog.text
    assert all(privado not in caplog.text for privado in ("ana-c16@example.test", "Ana", "12345671", "invalido"))


async def test_failed_smtp_preserves_fact_then_mailpit_receives_original_snapshot(escenario, sesiones, caplog):
    from app.application.services.notificaciones import DespacharNotificacion
    from app.infrastructure.correo.smtp import EnviadorSMTP
    address = f"c16-{uuid4().hex}@example.test"
    settings = escenario.app.state.settings
    settings.smtp_host = os.environ.get("SMTP_TEST_HOST", "c16-mail")
    settings.smtp_port = 1
    settings.smtp_starttls = False
    settings.smtp_user = settings.smtp_password = None
    async with sesiones() as s:
        p = await s.get(PacienteModel, escenario.pacientes[1])
        p.email, p.notas, p.obra_social = address, "nota secreta", "obra privada"
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        tid = r.json()["id"]
        r = await c.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers("paciente"), json={})
        assert r.status_code == 200
    async with sesiones() as s:
        resumen = await s.scalar(select(NotificacionModel).where(NotificacionModel.tipo == "resumen_reserva"))
        nid, snapshot = resumen.id, resumen.mensaje
    dispatcher = DespacharNotificacion(sesiones, escenario.reloj, EnviadorSMTP(settings), settings)
    assert not await dispatcher.ejecutar(1,nid)
    async with sesiones() as s:
        assert await s.scalar(text("SELECT estado FROM turno WHERE id=:id"), {"id":tid}) == "cancelado"
        n = await s.get(NotificacionModel,nid)
        assert (n.estado,n.intentos) == ("programada",1)
    settings.smtp_port = int(os.environ.get("SMTP_TEST_PORT", "1025"))
    assert await dispatcher.ejecutar(1,nid)
    async with httpx.AsyncClient(base_url=os.environ.get("MAILPIT_API_URL", "http://c16-mail:8025"),trust_env=False) as mailbox:
        propios = []
        for _ in range(20):
            mensajes = (await mailbox.get("/api/v1/messages",params={"limit":1000})).json()["messages"]
            propios = [m for m in mensajes if any(to["Address"] == address for to in m["To"])]
            if propios:
                break
            await asyncio.sleep(.05)
        assert len(propios) == 1
        cuerpo = (await mailbox.get(f"/api/v1/message/{propios[0]['ID']}")).json()["Text"]
        assert snapshot in cuerpo and "09/11/2026 10:00" in cuerpo
        assert all(p not in cuerpo and p not in caplog.text for p in ("12345671","nota secreta","obra privada"))
