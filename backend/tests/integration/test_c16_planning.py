"""Planificación durable y omisión en la transacción real del turno."""
import asyncio
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration
HITOS = ("solicitud_confirmacion", "recordatorio")


@pytest.fixture
async def escenario(sesiones, url_base):
    e = await preparar_escenario(sesiones, url_base)
    async with sesiones() as s:
        paciente = await s.get(PacienteModel, e.pacientes[1])
        paciente.email = "ana-c16@example.test"
        paciente.usuario_id = e.usuarios[1, "paciente"]
        await s.execute(text("UPDATE usuario SET email_verificado=true WHERE id=:id"),
                        {"id": e.usuarios[1, "paciente"]})
        await s.commit()
    return e


def payload(e, rol="recepcion", inicio=INICIO):
    datos = e.payload(inicio=inicio)
    if rol == "paciente":
        datos.pop("paciente_id")
    return datos


async def test_staff_booking_programs_both_milestones_in_current_cycle(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
    assert r.status_code == 201, r.text
    async with sesiones() as s:
        filas = (await s.scalars(select(NotificacionModel).where(
            NotificacionModel.tipo.in_(HITOS)).order_by(NotificacionModel.programada_para))).all()
        assert [(n.tipo, n.programada_para, n.ciclo, n.estado) for n in filas] == [
            ("solicitud_confirmacion", INICIO-timedelta(hours=48), 1, "programada"),
            ("recordatorio", INICIO-timedelta(hours=24), 1, "programada"),
        ]
        assert all(n.turno_id == r.json()["id"] and n.destinatario == "ana-c16@example.test" for n in filas)
        assert all(n.intentos == 0 and n.reclamada_en is None for n in filas)


@pytest.mark.parametrize("rol", ["recepcion", "paciente"])
@pytest.mark.parametrize("horas,tipos,estado", [
    (48, HITOS, "pendiente"), (30, ("recordatorio",), "confirmado"),
    (24, (), "confirmado"), (10, (), "confirmado"),
])
async def test_real_booking_observes_exact_birth_thresholds(escenario, sesiones, rol, horas, tipos, estado):
    escenario.reloj.fijar(INICIO-timedelta(hours=horas))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(rol), json=payload(escenario, rol))
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == estado
    async with sesiones() as s:
        filas = (await s.scalars(select(NotificacionModel).where(NotificacionModel.tipo.in_(HITOS))
                                .order_by(NotificacionModel.programada_para))).all()
        assert tuple(n.tipo for n in filas) == tipos
        assert all(n.programada_para >= escenario.reloj.ahora() for n in filas)


async def test_configuration_values_are_loaded_from_real_consultorio(escenario, sesiones):
    async with sesiones() as s:
        await s.execute(text("UPDATE consultorio SET horas_confirmacion=60,horas_recordatorio=36,horas_liberacion=18 WHERE id=1"))
        await s.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
    assert r.status_code == 201
    async with sesiones() as s:
        assert (await s.execute(text("SELECT tipo,programada_para FROM notificacion WHERE tipo IN ('solicitud_confirmacion','recordatorio') ORDER BY programada_para"))).all() == [
            ("solicitud_confirmacion", INICIO-timedelta(hours=60)),
            ("recordatorio", INICIO-timedelta(hours=36)),
        ]


async def test_repeated_and_concurrent_planning_is_deduplicated(escenario, sesiones):
    from app.application.services.hitos import ProgramadorHitos
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
    tid = r.json()["id"]
    async with sesiones() as s:
        await s.execute(text("DELETE FROM notificacion WHERE tipo IN ('solicitud_confirmacion','recordatorio')"))
        await s.commit()
    barrier = asyncio.Barrier(2)
    pids = set()
    async def planificar():
        async with UnidadDeTrabajoSQL(sesiones) as u:
            pids.add(await u._sesion.scalar(text("SELECT pg_backend_pid()")))
            turno = await u.turnos.obtener(1, tid)
            await barrier.wait()
            await ProgramadorHitos().planificar(u, turno, "crear", escenario.reloj.ahora())
            await ProgramadorHitos().planificar(u, turno, "crear", escenario.reloj.ahora())
    await asyncio.wait_for(asyncio.gather(planificar(), planificar()), 5)
    assert len(pids) == 2
    async with sesiones() as s:
        assert (await s.execute(text("SELECT tipo,count(*) FROM notificacion WHERE tipo IN ('solicitud_confirmacion','recordatorio') GROUP BY tipo ORDER BY tipo"))).all() == [
            ("recordatorio", 1), ("solicitud_confirmacion", 1)]


@pytest.mark.parametrize("accion", ["crear", "reprogramar"])
async def test_planning_failure_rolls_back_turn_history_and_notifications(escenario, sesiones, monkeypatch, accion):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as c:
        if accion == "reprogramar":
            creado = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
            tid = creado.json()["id"]
            async with sesiones() as s:
                await s.execute(text("UPDATE turno SET marcado_sin_confirmar_en=:a,confirmacion_solicitada_en=:a,recordatorio_enviado_en=:a WHERE id=:id"),
                                {"a": escenario.reloj.ahora(), "id": tid})
                await s.commit()
                turno_antes = await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid})
                notificaciones_antes = (await s.execute(text("SELECT id,estado,ciclo FROM notificacion ORDER BY id"))).all()
        async def fallar(*args, **kwargs):
            raise RuntimeError("planificación controlada")
        monkeypatch.setattr(RepositorioAvisosDeTurnoSQL, "programar_hito", fallar)
        if accion == "crear":
            r = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        else:
            r = await c.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert r.status_code == 500
    async with sesiones() as s:
        assert await s.scalar(text("SELECT count(*) FROM turno_historial")) == (0 if accion == "crear" else 1)
        if accion == "crear":
            assert await s.scalar(text("SELECT count(*) FROM turno")) == await s.scalar(text("SELECT count(*) FROM notificacion")) == 0
        else:
            assert await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid}) == turno_antes
            assert (await s.execute(text("SELECT id,estado,ciclo FROM notificacion ORDER BY id"))).all() == notificaciones_antes


@pytest.mark.parametrize("accion", ["reprogramar", "cancelar", "liberar"])
@pytest.mark.parametrize("estado", ["programada", "preparada", "enviada", "enviando"])
async def test_change_omits_only_scheduled_milestones_of_appropriate_cycle(escenario, sesiones, accion, estado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        creado = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        tid = creado.json()["id"]
        async with sesiones() as s:
            await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
            await s.execute(text("UPDATE notificacion SET estado=:estado,reclamada_en=:reclamo WHERE turno_id=:id AND tipo IN ('solicitud_confirmacion','recordatorio')"),
                            {"estado": estado, "reclamo": escenario.reloj.ahora() if estado == "enviando" else None, "id": tid})
            for tipo in HITOS:
                s.add(NotificacionModel(consultorio_id=1, turno_id=tid, tipo=tipo, canal="whatsapp", ciclo=1,
                    estado="preparada", destinatario="sintetico", programada_para=INICIO-timedelta(hours=48), intentos=0))
            await s.commit()
        if accion == "reprogramar":
            r = await c.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
        else:
            r = await c.post(f"/api/v1/turnos/{tid}/{accion}", headers=escenario.headers(), json={})
    assert r.status_code == 200, r.text
    async with sesiones() as s:
        filas = (await s.execute(text("SELECT tipo,canal,estado FROM notificacion WHERE turno_id=:id AND ciclo=1 AND tipo IN ('solicitud_confirmacion','recordatorio','resumen_reserva') ORDER BY tipo,canal"), {"id": tid})).all()
        assert len(filas) == 5
        for tipo, canal, actual in filas:
            esperado = "programada" if tipo == "resumen_reserva" else "omitida" if canal == "whatsapp" or estado in ("programada", "preparada") else estado
            assert actual == esperado
        if accion == "reprogramar":
            assert await s.scalar(text("SELECT count(*) FROM notificacion WHERE turno_id=:id AND ciclo=2 AND tipo IN ('solicitud_confirmacion','recordatorio')"), {"id": tid}) == 2


@pytest.mark.parametrize("accion", ["reprogramar", "cancelar", "liberar"])
async def test_omission_failure_rolls_back_change(escenario, sesiones, monkeypatch, accion):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as c:
        creado = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        tid = creado.json()["id"]
        async with sesiones() as s:
            await s.execute(text("UPDATE consultorio SET modo_liberacion='manual' WHERE id=1"))
            await s.commit()
            antes = await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid})
        async def fallar(*args, **kwargs):
            raise RuntimeError("omisión controlada")
        monkeypatch.setattr(RepositorioAvisosDeTurnoSQL, "omitir_hitos", fallar, raising=False)
        if accion == "reprogramar":
            r = await c.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
        else:
            r = await c.post(f"/api/v1/turnos/{tid}/{accion}", headers=escenario.headers(), json={})
    assert r.status_code == 500
    async with sesiones() as s:
        assert await s.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": tid}) == antes
        assert await s.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": tid}) == 1
        assert await s.scalar(text("SELECT count(*) FROM notificacion WHERE estado='omitida'")) == 0


async def test_reschedule_clears_cycle_mark_and_delivery_dates(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as c:
        creado = await c.post("/api/v1/turnos", headers=escenario.headers(), json=payload(escenario))
        tid = creado.json()["id"]
        async with sesiones() as s:
            await s.execute(text("UPDATE turno SET marcado_sin_confirmar_en=:a,confirmacion_solicitada_en=:a,recordatorio_enviado_en=:a WHERE id=:id"),
                            {"a": escenario.reloj.ahora(), "id": tid})
            await s.commit()
        r = await c.patch(f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat()})
    assert r.status_code == 200
    async with sesiones() as s:
        assert (await s.execute(text("SELECT ciclo_confirmacion,marcado_sin_confirmar_en,confirmacion_solicitada_en,recordatorio_enviado_en FROM turno WHERE id=:id"), {"id": tid})).one() == (2,None,None,None)
