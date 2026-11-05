"""Recorrido de avisos staff con SMTP/Mailpit y observación operativa reales."""
import asyncio
import os
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
async def test_staff_notice_to_sweep_smtp_and_operations_with_retry(accion, sesiones, url_base, caplog):
    e = await preparar_escenario(sesiones, url_base)
    settings = e.app.state.settings
    settings.sweep_shared_secret = SecretStr("c15-journey-test")
    settings.smtp_host = os.environ.get("SMTP_TEST_HOST", "127.0.0.1")
    settings.smtp_port = 1
    settings.smtp_starttls = False
    settings.smtp_user = settings.smtp_password = None
    settings.smtp_from = "Consultorio <consultorio@example.test>"
    address = f"c15-{uuid4().hex}@example.test"
    async with sesiones() as session:
        patient = await session.get(PacienteModel, e.pacientes[1])
        patient.email, patient.notas, patient.obra_social = address, "salud confidencial", "obra privada"
        await session.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=e.app), base_url="http://test") as client:
        created = await client.post("/api/v1/turnos", headers=e.headers(), json=e.payload())
        tid = created.json()["id"]
        if accion == "cancelar":
            changed = await client.post(f"/api/v1/turnos/{tid}/cancelar", headers=e.headers(), json={"motivo": "motivo interno"})
        else:
            changed = await client.patch(f"/api/v1/turnos/{tid}", headers=e.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
        assert changed.status_code == 200
        async with sesiones() as session:
            notice = (await session.scalars(select(NotificacionModel))).one()
            identifier, snapshot = notice.id, notice.mensaje
            original = await session.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid})
        first = await client.post("/internal/barrido", headers={"X-Sweep-Secret": "c15-journey-test"})
        assert first.status_code == 200, first.text
        assert first.json()["reintentadas"] == 1 and first.json()["enviadas"] == 0
        async with sesiones() as session:
            assert await session.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid}) == original
            failed = await session.get(NotificacionModel, identifier)
            assert (failed.estado, failed.intentos) == ("programada", 1)
            session.add(NotificacionModel(consultorio_id=1, tipo="verificacion_email", canal="email",
                estado="programada", destinatario=address, mensaje="Correo de cuenta sintético",
                programada_para=e.reloj.ahora(), intentos=0))
            await session.commit()
        settings.smtp_port = int(os.environ.get("SMTP_TEST_PORT", "11025"))
        second = await client.post("/internal/barrido", headers={"X-Sweep-Secret": "c15-journey-test"})
        assert second.status_code == 200, second.text
        assert second.json()["enviadas"] == second.json()["reclamadas"] == 2
        repeat = await client.post("/internal/barrido", headers={"X-Sweep-Secret": "c15-journey-test"})
        assert repeat.json()["reclamadas"] == repeat.json()["enviadas"] == 0
        listado = await client.get("/api/v1/notificaciones", headers=e.headers(), params={"estado": "enviada"})
        assert listado.status_code == 200
        assert len(listado.json()) == 2
        assert all("destinatario" not in item and "mensaje" not in item and "ultimo_error" not in item for item in listado.json())
        indicadores = await client.get("/api/v1/notificaciones/indicadores", headers=e.headers())
        assert indicadores.status_code == 200
        assert indicadores.json()["correos_del_dia"] == 2
        assert indicadores.json()["ultimo_barrido"]["estado"] == "exitoso"
        assert indicadores.json()["ultimo_barrido"]["ejecucion_id"] == repeat.json()["ejecucion_id"]
    async with httpx.AsyncClient(base_url=os.environ.get("MAILPIT_API_URL", "http://127.0.0.1:18025"), trust_env=False) as mailbox:
        own = []
        for _ in range(30):
            messages = (await mailbox.get("/api/v1/messages", params={"limit": 1000})).json()["messages"]
            own = [item for item in messages if any(to["Address"] == address for to in item["To"])]
            if len(own) == 2:
                break
            await asyncio.sleep(0.05)
        assert len(own) == 2
        bodies = [(await mailbox.get(f"/api/v1/message/{item['ID']}")).json()["Text"] for item in own]
        assert any(snapshot in body for body in bodies)
        assert all(private not in body for body in bodies for private in ("12345671", "salud confidencial", "obra privada", "motivo interno", "c15-journey-test"))
    assert all(private not in caplog.text for private in (address, "12345671", "salud confidencial", "c15-journey-test"))
    async with sesiones() as session:
        assert await session.scalar(text("SELECT count(*) FROM notificacion WHERE tipo IN ('solicitud_confirmacion','recordatorio','resumen_reserva','cancelacion_por_paciente')")) == 0
