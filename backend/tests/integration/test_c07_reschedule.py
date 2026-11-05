from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.infrastructure.db.historial import RepositorioHistorialSQL
from app.infrastructure.db.repositorios import RepositorioTurnosSQL

from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


@pytest.mark.parametrize("offset,ajuste,duracion", [(1440, None, 45), (15, None, 45), (1440, 60, 60)])
async def test_reschedule_keeps_id_and_adjusted_duration_and_restarts_cycle(escenario, sesiones, offset, ajuste, duracion):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(duracion_min=45, confirmar=True))
        assert alta.status_code == 201
        identificador = alta.json()["id"]
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET ciclo_confirmacion=2, marcado_sin_confirmar_en=:ahora, confirmacion_solicitada_en=:ahora, recordatorio_enviado_en=:ahora WHERE id=:id"), {"id": identificador, "ahora": escenario.reloj.ahora()})
            await sesion.commit()
        destino = INICIO + timedelta(minutes=offset)
        payload = {"inicio": destino.isoformat()}
        if ajuste is not None:
            payload["duracion_min"] = ajuste
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json=payload)
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json()["id"] == identificador
    assert respuesta.json()["estado"] == "pendiente"
    assert respuesta.json()["ciclo_confirmacion"] == 3
    async with sesiones() as sesion:
        fila = (await sesion.execute(text("SELECT inicio,fin,reprogramado_de_inicio,marcado_sin_confirmar_en,confirmado_en,confirmacion_solicitada_en,recordatorio_enviado_en FROM turno WHERE id=:id"), {"id": identificador})).one()
        assert fila.inicio == destino
        assert (fila.fin-fila.inicio).total_seconds() / 60 == duracion
        assert fila.reprogramado_de_inicio == INICIO
        assert fila.marcado_sin_confirmar_en is fila.confirmado_en is fila.confirmacion_solicitada_en is fila.recordatorio_enviado_en is None
        assert list((await sesion.scalars(text("SELECT accion FROM turno_historial WHERE turno_id=:id ORDER BY id"), {"id": identificador})).all()) == ["crear", "reprogramar"]


@pytest.mark.parametrize("minutes,estado,motivo", [(2879, "confirmado", "RN-29"), (2880, "pendiente", "RN-32"), (2881, "pendiente", "RN-32")])
async def test_reschedule_exact_confirmation_threshold_resets_mark_once(escenario, sesiones, minutes, estado, motivo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        identificador = alta.json()["id"]
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET ciclo_confirmacion=2,marcado_sin_confirmar_en=:ahora WHERE id=:id"), {"id": identificador, "ahora": escenario.reloj.ahora()})
            await sesion.commit()
        destino = INICIO + timedelta(days=1)
        escenario.reloj.fijar(destino - timedelta(minutes=minutes))
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": destino.isoformat()})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == estado
    assert respuesta.json()["ciclo_confirmacion"] == 3
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT marcado_sin_confirmar_en FROM turno WHERE id=:id"), {"id": identificador}) is None
        detalle = await sesion.scalar(text("SELECT detalle FROM turno_historial WHERE turno_id=:id ORDER BY id DESC LIMIT 1"), {"id": identificador})
        assert detalle["motivo"] == motivo


@pytest.mark.parametrize("failure", ["regular", "sobreturno", "history"])
async def test_failed_reschedule_preserves_every_original_value_and_history(escenario, sesiones, monkeypatch, failure):
    destino = INICIO + timedelta(days=1)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(duracion_min=45))
        identificador = alta.json()["id"]
        if failure != "history":
            ocupante = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(inicio=destino))
            assert ocupante.status_code == 201
            if failure == "sobreturno":
                async with sesiones() as sesion:
                    await sesion.execute(text("UPDATE turno SET es_sobreturno=true WHERE id=:id"), {"id": ocupante.json()["id"]})
                    await sesion.commit()
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET ciclo_confirmacion=2,marcado_sin_confirmar_en=:ahora WHERE id=:id"), {"id": identificador, "ahora": escenario.reloj.ahora()})
            await sesion.commit()
            anterior = await sesion.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": identificador})
            historia = list((await sesion.scalars(text("SELECT row_to_json(h) FROM turno_historial h WHERE turno_id=:id ORDER BY id"), {"id": identificador})).all())
        if failure == "history":
            async def fallar(repo, hecho):
                raise RuntimeError("historia controlada")
            monkeypatch.setattr(RepositorioHistorialSQL, "agregar", fallar)
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": destino.isoformat()})
    assert respuesta.status_code == (500 if failure == "history" else 409)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT row_to_json(t) FROM turno t WHERE id=:id"), {"id": identificador}) == anterior
        assert list((await sesion.scalars(text("SELECT row_to_json(h) FROM turno_historial h WHERE turno_id=:id ORDER BY id"), {"id": identificador})).all()) == historia


@pytest.mark.parametrize("estado", ["atendido", "ausente", "cancelado", "liberado"])
async def test_reschedule_rejects_final_states_without_history(escenario, sesiones, estado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        identificador = alta.json()["id"]
        async with sesiones() as sesion:
            await sesion.execute(text("UPDATE turno SET estado=CAST(:estado AS estado_turno) WHERE id=:id"), {"id": identificador, "estado": estado})
            await sesion.commit()
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": (INICIO + timedelta(days=1)).isoformat()})
    assert respuesta.status_code == 403
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT inicio FROM turno WHERE id=:id"), {"id": identificador}) == INICIO
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": identificador}) == 1


async def test_stale_reschedule_is_http_conflict_without_history(escenario, sesiones, monkeypatch):
    original_update = RepositorioTurnosSQL.actualizar

    async def modificar_antes(repo, original, cambios):
        async with sesiones() as otra:
            await otra.execute(text("UPDATE turno SET ciclo_confirmacion=ciclo_confirmacion+1 WHERE id=:id"), {"id": original.id})
            await otra.commit()
        return await original_update(repo, original, cambios)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        identificador = alta.json()["id"]
        monkeypatch.setattr(RepositorioTurnosSQL, "actualizar", modificar_antes)
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": (INICIO + timedelta(days=1)).isoformat()})
    assert respuesta.status_code == 409
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT inicio FROM turno WHERE id=:id"), {"id": identificador}) == INICIO
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": identificador}) == 1


@pytest.mark.parametrize("extra", [{"fin": "2026-11-10T11:00:00-03:00"}, {"consultorio_id": 2}, {"profesional_id": 2}, {"confirmar": True}, {"duracion_min": 20}, {"duracion_min": 0}, {"duracion_min": -1}, {"inicio": "2026-11-10T10:00:00"}])
async def test_patch_has_strict_payload_and_keeps_original_on_validation_failure(escenario, sesiones, extra):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        identificador = alta.json()["id"]
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(), json={"inicio": (INICIO + timedelta(days=1)).isoformat(), **extra})
    assert respuesta.status_code == 422
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT inicio FROM turno WHERE id=:id"), {"id": identificador}) == INICIO
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": identificador}) == 1


@pytest.mark.parametrize("rol,expected", [("administrador", 200), ("profesional", 403), ("paciente", 404), ("administrativo", 403), (None, 401)])
async def test_patch_authorization_uses_staff_roles_and_tenant_scope(escenario, sesiones, rol, expected):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        identificador = alta.json()["id"]
        respuesta = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(rol) if rol else {}, json={"inicio": (INICIO + timedelta(days=1)).isoformat()})
        ajeno = await client.patch(f"/api/v1/turnos/{identificador}", headers=escenario.headers(consultorio=2), json={"inicio": (INICIO + timedelta(days=2)).isoformat()})
    assert respuesta.status_code == expected
    assert ajeno.status_code == 404
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE turno_id=:id"), {"id": identificador}) == (2 if expected == 200 else 1)


async def test_patch_openapi_lists_transaction_errors_and_strict_input(escenario):
    schema = escenario.app.openapi()
    patch = schema["paths"]["/api/v1/turnos/{turno_id}"]["patch"]
    assert {"200", "401", "403", "404", "409", "422"} <= set(patch["responses"])
    assert schema["components"]["schemas"]["ReprogramacionEntrada"]["additionalProperties"] is False


@pytest.mark.parametrize("method", ["post", "patch"])
@pytest.mark.parametrize("duration", [6_000_000_000, 15 * 10**30])
async def test_unrepresentable_interval_is_422_without_partial_data(escenario, sesiones, method, duration):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        if method == "post":
            respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload(duracion_min=duration))
        else:
            alta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
            assert alta.status_code == 201
            respuesta = await client.patch(f"/api/v1/turnos/{alta.json()['id']}", headers=escenario.headers(), json={"inicio": (INICIO+timedelta(days=1)).isoformat(), "duracion_min": duration})
    assert respuesta.status_code == 422
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == (0 if method == "post" else 1)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == (0 if method == "post" else 1)
        if method == "patch":
            assert await sesion.scalar(text("SELECT inicio FROM turno")) == INICIO
