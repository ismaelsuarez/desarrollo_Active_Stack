"""Confirmación bearer atómica por turno/ciclo (RN-30, RN-59)."""
import asyncio
import httpx
import pytest
from datetime import timedelta
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.domain.services.auth_crypto import calcular_token_hash
from app.application.errors_turnos import RechazoDeTurno
from app.infrastructure.db.models import TokenUsuarioModel, TurnoHistorialModel, TurnoModel
from tests.integration.c07_support import AHORA, INICIO, preparar_escenario

pytestmark = pytest.mark.integration
RAW = "enlace-confirmacion-sintetico"


async def preparar_enlace(sesiones, url_base, *, con_cuenta=False, consultorio=1, **token_cambios):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        response = await client.post("/api/v1/turnos", headers=escenario.headers(consultorio=consultorio), json=escenario.payload(consultorio=consultorio))
    assert response.status_code == 201, response.text
    turno_id = response.json()["id"]
    async with sesiones() as sesion:
        if con_cuenta:
            await sesion.execute(text("UPDATE paciente SET usuario_id=:uid WHERE id=:pid"),
                {"uid": escenario.usuarios[consultorio, "paciente"], "pid": escenario.pacientes[consultorio]})
        sesion.add(TokenUsuarioModel(**(dict(
            consultorio_id=consultorio, usuario_id=escenario.usuarios[consultorio, "paciente"] if con_cuenta else None,
            turno_id=turno_id, ciclo=1, tipo="confirmar_turno", token_hash=calcular_token_hash(RAW),
            expira_en=INICIO, creado_en=AHORA,
        ) | token_cambios)))
        await sesion.commit()
    return escenario, turno_id


@pytest.mark.parametrize("con_cuenta,consultorio", [(False, 1), (True, 1), (False, 2), (True, 2)])
async def test_valid_link_without_account_confirms_consumes_and_audits_atomically(sesiones, url_base, con_cuenta, consultorio):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace

    escenario, tid = await preparar_enlace(sesiones, url_base, con_cuenta=con_cuenta, consultorio=consultorio)
    resultado = await ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar(RAW)
    assert (resultado.turno_id, resultado.estado) == (tid, "confirmado")
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, tid)
        token = await sesion.scalar(select(TokenUsuarioModel))
        hecho = await sesion.scalar(select(TurnoHistorialModel).where(TurnoHistorialModel.accion == "confirmar"))
        assert (turno.estado.value, turno.confirmado_en, token.usado_en) == ("confirmado", AHORA, AHORA)
        assert (hecho.usuario_id, hecho.estado_anterior, hecho.estado_nuevo) == (
            escenario.usuarios[consultorio, "paciente"] if con_cuenta else None, "pendiente", "confirmado")
        assert hecho.consultorio_id == consultorio
        assert hecho.detalle == {"medio": "enlace", "actor": "paciente" if con_cuenta else "paciente_sin_cuenta"}
        assert await sesion.scalar(text("SELECT count(*) FROM usuario")) == 10


@pytest.mark.parametrize("problema", ["inexistente", "usado", "vencido", "vencido_antes", "tipo", "ciclo"])
async def test_invalid_link_is_generic_and_keeps_turn_token_and_history(sesiones, url_base, problema):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace

    escenario, tid = await preparar_enlace(sesiones, url_base)
    async with sesiones() as sesion:
        token = await sesion.scalar(select(TokenUsuarioModel))
        if problema == "usado":
            token.usado_en = AHORA - timedelta(seconds=1)
        elif problema in ("vencido", "vencido_antes"):
            token.expira_en = AHORA - timedelta(seconds=1 if problema == "vencido_antes" else 0)
        elif problema == "tipo":
            token.tipo = "verificar_email"
            token.usuario_id = escenario.usuarios[1, "paciente"]
        elif problema == "ciclo":
            token.ciclo = 2
        await sesion.commit()
        usado_antes = token.usado_en
    with pytest.raises(RechazoDeTurno) as error:
        await ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar("inexistente" if problema == "inexistente" else RAW)
    assert (error.value.codigo, error.value.motivo) == (400, "Enlace inválido o vencido")
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, tid)
        token = await sesion.scalar(select(TokenUsuarioModel))
        assert (turno.estado.value, turno.confirmado_en, token.usado_en) == ("pendiente", None, usado_antes)
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 0


@pytest.mark.parametrize("estado", ["liberado", "cancelado", "confirmado", "atendido", "ausente"])
async def test_incompatible_state_returns_conflict_without_consuming_link(sesiones, url_base, estado):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace

    escenario, tid = await preparar_enlace(sesiones, url_base)
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE turno SET estado=CAST(:estado AS estado_turno) WHERE id=:tid"), {"estado": estado, "tid": tid})
        await sesion.commit()
    with pytest.raises(RechazoDeTurno) as error:
        await ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar(RAW)
    assert error.value.codigo == 409
    if estado == "liberado":
        assert "reservar de nuevo" in error.value.motivo
    async with sesiones() as sesion:
        assert (await sesion.get(TurnoModel, tid)).estado.value == estado
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 0


@pytest.mark.parametrize("tabla,event", [("turno_historial", "INSERT"), ("token_usuario", "UPDATE")])
async def test_failure_rolls_back_state_token_and_audit(sesiones, url_base, engine, tabla, event):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace

    escenario, tid = await preparar_enlace(sesiones, url_base)
    async with engine.begin() as conexion:
        await conexion.execute(text("CREATE FUNCTION c16_fallar_confirmacion() RETURNS trigger LANGUAGE plpgsql AS 'BEGIN RAISE EXCEPTION ''fallo sintetico C16''; END'"))
        await conexion.execute(text(f"CREATE TRIGGER c16_fallar BEFORE {event} ON {tabla} FOR EACH ROW EXECUTE FUNCTION c16_fallar_confirmacion()"))
    try:
        with pytest.raises(DBAPIError):
            await ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar(RAW)
    finally:
        async with engine.begin() as conexion:
            await conexion.execute(text(f"DROP TRIGGER c16_fallar ON {tabla}"))
            await conexion.execute(text("DROP FUNCTION c16_fallar_confirmacion()"))
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, tid)
        assert (turno.estado.value, turno.confirmado_en) == ("pendiente", None)
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 0


async def test_http_link_works_without_session_using_token_clinic(sesiones, url_base):
    escenario, tid = await preparar_enlace(sesiones, url_base, consultorio=2)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos/confirmar-por-enlace", json={"token": RAW})
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {"turno_id": tid, "estado": "confirmado"}


@pytest.mark.parametrize("extra", [{"consultorio_id": 1}, {"estado": "confirmado"}, {"usuario_id": 1}])
async def test_http_link_rejects_extra_fields_without_echoing_secrets(sesiones, url_base, extra, capsys):
    escenario, tid = await preparar_enlace(sesiones, url_base, consultorio=2)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos/confirmar-por-enlace", json={"token": RAW, **extra})
    assert respuesta.status_code == 422
    logs = capsys.readouterr().err
    assert "HTTP request completed" in logs
    assert RAW not in respuesta.text and RAW not in logs
    async with sesiones() as sesion:
        assert (await sesion.get(TurnoModel, tid)).estado.value == "pendiente"
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None


async def test_http_invalid_link_and_limited_scope_do_not_change_turn(sesiones, url_base):
    escenario, tid = await preparar_enlace(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos/confirmar-por-enlace", json={"token": "inexistente"})
        assert respuesta.status_code == 400
        assert respuesta.json() == {"detail": "Enlace inválido o vencido"}
        for accion in ("confirmar", "cancelar", "liberar"):
            respuesta = await client.post(f"/api/v1/turnos/{tid}/{accion}", headers={"Authorization": f"Bearer {RAW}"}, json={})
            assert respuesta.status_code == 401, respuesta.text
        respuesta = await client.patch(f"/api/v1/turnos/{tid}", headers={"Authorization": f"Bearer {RAW}"}, json={"inicio": INICIO.isoformat()})
        assert respuesta.status_code == 401
    async with sesiones() as sesion:
        assert (await sesion.get(TurnoModel, tid)).estado.value == "pendiente"
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None


async def test_http_link_openapi_has_minimal_contract_and_no_session_requirement(sesiones, url_base):
    escenario, _ = await preparar_enlace(sesiones, url_base)
    schema = escenario.app.openapi()
    operation = schema["paths"]["/api/v1/turnos/confirmar-por-enlace"]["post"]
    assert not operation.get("security")
    assert {"200", "400", "409", "422"} <= set(operation["responses"])
    entrada = schema["components"]["schemas"]["TokenRequest"]
    assert set(entrada["properties"]) == {"token"}
    assert entrada["additionalProperties"] is False
    salida = schema["components"]["schemas"]["ConfirmacionTurnoRespuesta"]
    assert set(salida["properties"]) == {"turno_id", "estado"}


@pytest.mark.parametrize("mismo_token", [True, False])
async def test_concurrent_links_confirm_once_with_distinct_postgres_connections(sesiones, url_base, monkeypatch, mismo_token):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace
    from app.infrastructure.db.confirmacion_turno import RepositorioConfirmacionTurnoSQL

    escenario, tid = await preparar_enlace(sesiones, url_base)
    segundo_raw = RAW if mismo_token else "segundo-enlace-sintetico"
    if not mismo_token:
        async with sesiones() as sesion:
            sesion.add(TokenUsuarioModel(consultorio_id=1, usuario_id=None, turno_id=tid,
                ciclo=1, tipo="confirmar_turno", token_hash=calcular_token_hash(segundo_raw),
                expira_en=INICIO, creado_en=AHORA))
            await sesion.commit()
    pids = set()
    ambas_localizadas = asyncio.Event()
    original = RepositorioConfirmacionTurnoSQL.localizar

    async def localizar(self, token_hash):
        resultado = await original(self, token_hash)
        pids.add(await self._sesion.scalar(text("SELECT pg_backend_pid()")))
        if len(pids) == 2:
            ambas_localizadas.set()
        return resultado

    monkeypatch.setattr(RepositorioConfirmacionTurnoSQL, "localizar", localizar)
    caso = ConfirmarTurnoPorEnlace(sesiones, escenario.reloj)
    async with sesiones() as bloqueador:
        await bloqueador.execute(text("SELECT id FROM turno WHERE id=:tid FOR UPDATE"), {"tid": tid})
        tareas = [asyncio.create_task(caso.ejecutar(raw)) for raw in (RAW, segundo_raw)]
        try:
            await asyncio.wait_for(ambas_localizadas.wait(), timeout=5)
            async with sesiones() as observador:
                async with asyncio.timeout(5):
                    while True:
                        esperando = await observador.scalar(text("""SELECT count(*) FROM pg_stat_activity
                            WHERE datname=current_database() AND wait_event_type='Lock'"""))
                        if esperando == 2:
                            break
                        await asyncio.sleep(0.01)
            await bloqueador.rollback()
            resultados = await asyncio.gather(*tareas, return_exceptions=True)
        finally:
            for tarea in tareas:
                if not tarea.done():
                    tarea.cancel()
            await asyncio.gather(*tareas, return_exceptions=True)
    assert len(pids) == 2
    exitos = [r for r in resultados if not isinstance(r, BaseException)]
    errores = [r for r in resultados if isinstance(r, RechazoDeTurno)]
    assert len(exitos) == 1, resultados
    assert len(errores) == 1 and errores[0].codigo == (400 if mismo_token else 409)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 1
        assert await sesion.scalar(text("SELECT count(*) FROM token_usuario WHERE usado_en IS NOT NULL")) == 1


@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
async def test_staff_change_winning_race_prevents_obsolete_link_confirmation(sesiones, url_base, monkeypatch, accion):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace
    from app.infrastructure.db.confirmacion_turno import RepositorioConfirmacionTurnoSQL
    from app.infrastructure.db.repositorios import RepositorioTurnosSQL

    escenario, tid = await preparar_enlace(sesiones, url_base)
    cambio_listo, token_leido, terminar_cambio = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original_actualizar = RepositorioTurnosSQL.actualizar
    original_localizar = RepositorioConfirmacionTurnoSQL.localizar
    pids = set()

    async def actualizar(self, original, cambios):
        resultado = await original_actualizar(self, original, cambios)
        pids.add(await self._sesion.scalar(text("SELECT pg_backend_pid()")))
        cambio_listo.set()
        await asyncio.wait_for(terminar_cambio.wait(), timeout=5)
        return resultado

    async def localizar(self, token_hash):
        resultado = await original_localizar(self, token_hash)
        pids.add(await self._sesion.scalar(text("SELECT pg_backend_pid()")))
        token_leido.set()
        return resultado

    monkeypatch.setattr(RepositorioTurnosSQL, "actualizar", actualizar)
    monkeypatch.setattr(RepositorioConfirmacionTurnoSQL, "localizar", localizar)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        operacion = client.post(f"/api/v1/turnos/{tid}/cancelar", headers=escenario.headers(), json={"motivo": "cambio sintético"}) if accion == "cancelar" else client.patch(
            f"/api/v1/turnos/{tid}", headers=escenario.headers(), json={"inicio": (INICIO + timedelta(days=1)).isoformat()})
        tarea_staff = asyncio.create_task(operacion)
        tarea_link = None
        try:
            await asyncio.wait_for(cambio_listo.wait(), timeout=5)
            tarea_link = asyncio.create_task(ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar(RAW))
            await asyncio.wait_for(token_leido.wait(), timeout=5)
            terminar_cambio.set()
            respuesta = await tarea_staff
            assert respuesta.status_code == 200, respuesta.text
            with pytest.raises(RechazoDeTurno) as error:
                await tarea_link
            assert error.value.codigo == (409 if accion == "cancelar" else 400)
        finally:
            terminar_cambio.set()
            for tarea in (tarea_staff, tarea_link):
                if tarea is not None and not tarea.done():
                    tarea.cancel()
            await asyncio.gather(*(t for t in (tarea_staff, tarea_link) if t is not None), return_exceptions=True)
    assert len(pids) == 2
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, tid)
        assert turno.estado.value == ("cancelado" if accion == "cancelar" else "pendiente")
        assert turno.ciclo_confirmacion == (1 if accion == "cancelar" else 2)
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 0


async def test_link_rechecks_clock_after_waiting_for_turn_lock(sesiones, url_base, monkeypatch):
    from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace
    from app.infrastructure.db.confirmacion_turno import RepositorioConfirmacionTurnoSQL

    escenario, tid = await preparar_enlace(sesiones, url_base)
    leido = asyncio.Event()
    original = RepositorioConfirmacionTurnoSQL.localizar

    async def localizar(self, token_hash):
        resultado = await original(self, token_hash)
        leido.set()
        return resultado

    monkeypatch.setattr(RepositorioConfirmacionTurnoSQL, "localizar", localizar)
    async with sesiones() as bloqueador:
        await bloqueador.execute(text("SELECT id FROM turno WHERE id=:tid FOR UPDATE"), {"tid": tid})
        tarea = asyncio.create_task(ConfirmarTurnoPorEnlace(sesiones, escenario.reloj).ejecutar(RAW))
        try:
            await asyncio.wait_for(leido.wait(), timeout=5)
            escenario.reloj.fijar(INICIO)
            await bloqueador.rollback()
            with pytest.raises(RechazoDeTurno) as error:
                await tarea
            assert error.value.codigo == 400
        finally:
            if not tarea.done():
                tarea.cancel()
            await asyncio.gather(tarea, return_exceptions=True)
    async with sesiones() as sesion:
        assert (await sesion.get(TurnoModel, tid)).estado.value == "pendiente"
        assert (await sesion.scalar(select(TokenUsuarioModel))).usado_en is None
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial WHERE accion='confirmar'")) == 0
