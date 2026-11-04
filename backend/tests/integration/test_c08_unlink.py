"""RN-63: desvinculación conserva ficha y revoca sesiones atómicamente."""
from datetime import timedelta
import asyncio

import httpx
import pytest
from sqlalchemy import delete, select, text

from app.domain.services.auth_crypto import calcular_token_hash
from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, RefreshTokenModel, UsuarioModel
from tests.integration.c07_support import AHORA
from tests.integration.test_c08_linking import caso

pytestmark = pytest.mark.integration


def auth(sesion):
    from app.application.services.auth_service import AuthService
    from app.application.services.rate_limiter import LoginRateLimiter
    from app.application.services.token_service import AuthTokenService
    from app.domain.ports.reloj import RelojSimulado

    reloj = RelojSimulado(AHORA)
    return AuthService(sesion, reloj, AuthTokenService(reloj, "j" * 32),
                       LoginRateLimiter(sesion, reloj, "o" * 32))


async def vincular_caso(caso):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                                      json={"paciente_id": caso["pid"]}, headers=escenario.headers())
    assert respuesta.status_code == 200


@pytest.mark.parametrize("rol", ["recepcion", "administrador"])
async def test_desvincular_conserva_ficha_y_registra_origen_y_revocacion(sesiones, caso, rol):
    await vincular_caso(caso)
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        datos_antes = (ficha.nombre, ficha.apellido, ficha.dni, ficha.telefono, ficha.email, ficha.activo)
        sesion.add(RefreshTokenModel(consultorio_id=1, usuario_id=caso["uid"],
                    token_hash=calcular_token_hash("refresh-a-revocar"), expira_en=AHORA+timedelta(days=1),
                    creado_en=AHORA))
        await sesion.commit()
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/pacientes/{caso["pid"]}/desvincular',
                                      json={"motivo": "Corrección verificada"}, headers=escenario.headers(rol))
    assert respuesta.status_code == 200
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        token = await sesion.scalar(select(RefreshTokenModel))
        assert ficha.usuario_id is None
        assert (ficha.nombre, ficha.apellido, ficha.dni, ficha.telefono, ficha.email, ficha.activo) == datos_antes
        assert solicitud.estado == "rechazada"
        assert solicitud.paciente_id == ficha.id
        assert solicitud.motivo_rechazo == "Corrección verificada"
        assert solicitud.resuelta_por_id == escenario.usuarios[1, rol]
        assert solicitud.resuelta_en == AHORA
        assert token.revocado_en == AHORA
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


async def desvincular_caso(caso, **opciones):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,
                         raise_app_exceptions=False), base_url="http://test") as cliente:
        return await cliente.post(f'/api/v1/pacientes/{caso["pid"]}/desvincular',
            headers=opciones.pop("headers", escenario.headers()),
            json=opciones.pop("json", {"motivo": "Corrección"}), **opciones)


async def test_sin_solicitud_crea_rechazada_con_dni_actual(sesiones, caso):
    await vincular_caso(caso)
    async with sesiones() as sesion:
        await sesion.execute(delete(SolicitudVinculacionModel))
        (await sesion.get(PacienteModel, caso["pid"])).dni = "76543210"
        await sesion.commit()
    assert (await desvincular_caso(caso)).status_code == 200
    async with sesiones() as sesion:
        solicitud = await sesion.scalar(select(SolicitudVinculacionModel))
        assert solicitud.usuario_id == caso["uid"]
        assert solicitud.dni_declarado == "76543210"
        assert solicitud.paciente_id == caso["pid"]
        assert solicitud.estado == "rechazada"
        assert solicitud.creada_en == AHORA


@pytest.mark.parametrize("estado", ["pendiente", "rechazada"])
async def test_solicitud_incompatible_revierte_ficha(sesiones, caso, estado):
    await vincular_caso(caso)
    async with sesiones() as sesion:
        (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado = estado
        await sesion.commit()
    assert (await desvincular_caso(caso)).status_code == 409
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == estado


@pytest.mark.parametrize("payload", [{}, {"motivo": "  "}, {"motivo": None},
                                    {"motivo": "Corrección", "usuario_id": 3}])
async def test_motivo_requerido_y_extras_rechazados(caso, payload):
    assert (await desvincular_caso(caso, json=payload)).status_code == 422


@pytest.mark.parametrize("rol", ["paciente", "profesional", "administrativo"])
async def test_desvincular_solo_personal(caso, rol):
    assert (await desvincular_caso(caso, headers=caso["escenario"].headers(rol))).status_code == 403


async def test_sin_cuenta_y_referencias_ajenas(caso):
    assert (await desvincular_caso(caso)).status_code == 409
    assert (await desvincular_caso(caso, headers=caso["escenario"].headers(consultorio=2))).status_code == 404
    caso["pid"] = 99999
    assert (await desvincular_caso(caso)).status_code == 404


@pytest.mark.parametrize("paso,error_sql,codigo", [
    ("desvincular_ficha", None, 500), ("registrar_desvinculacion", None, 500),
    ("registrar_desvinculacion", "40P01", 409),
    ("registrar_desvinculacion", "40001", 409), ("revocar_sesiones", None, 500),
])
async def test_fallo_en_cada_escritura_revierte_todo(sesiones, caso, monkeypatch,
                                                   paso, error_sql, codigo):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL
    from app.infrastructure.db.cuentas import RepositorioCuentas
    await vincular_caso(caso)
    async with sesiones() as sesion:
        sesion.add(RefreshTokenModel(consultorio_id=1, usuario_id=caso["uid"],
                    token_hash=calcular_token_hash("vigente"), expira_en=AHORA+timedelta(days=1),
                    creado_en=AHORA))
        await sesion.commit()
    clase = RepositorioCuentas if paso == "revocar_sesiones" else RepositorioVinculacionSQL
    original = getattr(clase, paso)

    async def escribir_y_fallar(repo, *args):
        await original(repo, *args)
        if error_sql:
            await repo.sesion.execute(text(
                f"DO $$ BEGIN RAISE EXCEPTION 'controlado' USING ERRCODE = '{error_sql}'; END $$"))
        raise RuntimeError("controlado")

    monkeypatch.setattr(clase, paso, escribir_y_fallar)
    assert (await desvincular_caso(caso)).status_code == codigo
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "vinculada"
        assert (await sesion.scalar(select(RefreshTokenModel))).revocado_en is None


async def test_doble_desvinculacion_serializa_dos_conexiones(sesiones, caso, monkeypatch):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL
    await vincular_caso(caso)
    barrera, conexiones = asyncio.Barrier(2), set()
    original = RepositorioVinculacionSQL.bloquear_ficha

    async def simultaneas(repo, *args):
        conexiones.add(await repo.sesion.scalar(text("select pg_backend_pid()")))
        await asyncio.wait_for(barrera.wait(), 3)
        return await original(repo, *args)

    monkeypatch.setattr(RepositorioVinculacionSQL, "bloquear_ficha", simultaneas)
    respuestas = await asyncio.gather(desvincular_caso(caso), desvincular_caso(caso))
    assert sorted(r.status_code for r in respuestas) == [200, 409]
    assert len(conexiones) == 2
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id is None
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "rechazada"


async def crear_refresh(sesiones, caso, raw="refresh-desvinculacion", revocado_en=None):
    async with sesiones() as sesion:
        sesion.add(RefreshTokenModel(
            consultorio_id=1, usuario_id=caso["uid"], token_hash=calcular_token_hash(raw),
            expira_en=AHORA + timedelta(days=1), creado_en=AHORA, revocado_en=revocado_en,
        ))
        await sesion.commit()
    return raw


async def test_desvincular_entre_lectura_y_rotacion_revoca_refresh_en_vuelo(sesiones, caso):
    from app.application.services.auth_service import SesionInvalidaError

    await vincular_caso(caso)
    raw = await crear_refresh(sesiones, caso)
    leido, continuar = asyncio.Event(), asyncio.Event()
    async with sesiones() as sesion:
        scalar = sesion.scalar
        pid_refresh = await scalar(text("select pg_backend_pid()"))

        async def leer_y_pausar(sentencia, *args, **kwargs):
            resultado = await scalar(sentencia, *args, **kwargs)
            if isinstance(resultado, RefreshTokenModel) and not leido.is_set():
                leido.set()
                await continuar.wait()
            return resultado

        sesion.scalar = leer_y_pausar
        tarea = asyncio.create_task(auth(sesion).refresh(raw))
        await asyncio.wait_for(leido.wait(), 3)
        try:
            assert (await desvincular_caso(caso)).status_code == 200
            async with sesiones() as observador:
                assert await observador.scalar(text("select pg_backend_pid()")) != pid_refresh
        finally:
            continuar.set()
        with pytest.raises(SesionInvalidaError):
            await tarea

    async with sesiones() as sesion:
        tokens = (await sesion.scalars(select(RefreshTokenModel))).all()
        assert len(tokens) == 1
        assert tokens[0].revocado_en == AHORA
        assert tokens[0].reemplazado_por_id is None


async def test_refresh_con_lock_previo_desvincular_revoca_tambien_reemplazo(sesiones, caso, monkeypatch):
    from app.application.services.auth_service import SesionInvalidaError
    from app.infrastructure.db.cuentas import RepositorioCuentas

    await vincular_caso(caso)
    raw = await crear_refresh(sesiones, caso)
    usuario_bloqueado, continuar, desvinculacion_solicitada = (
        asyncio.Event(), asyncio.Event(), asyncio.Event()
    )
    conexiones = set()
    original = RepositorioCuentas.usuario_por_id

    async def avisar_desvinculacion(repo, *args):
        conexiones.add(await repo.sesion.scalar(text("select pg_backend_pid()")))
        desvinculacion_solicitada.set()
        return await original(repo, *args)

    monkeypatch.setattr(RepositorioCuentas, "usuario_por_id", avisar_desvinculacion)
    async with sesiones() as sesion:
        scalar = sesion.scalar
        conexiones.add(await scalar(text("select pg_backend_pid()")))

        async def pausar_usuario(sentencia, *args, **kwargs):
            resultado = await scalar(sentencia, *args, **kwargs)
            if isinstance(resultado, UsuarioModel):
                usuario_bloqueado.set()
                await continuar.wait()
            return resultado

        sesion.scalar = pausar_usuario
        refresh = asyncio.create_task(auth(sesion).refresh(raw))
        await asyncio.wait_for(usuario_bloqueado.wait(), 3)
        desvinculacion = asyncio.create_task(desvincular_caso(caso))
        await asyncio.wait_for(desvinculacion_solicitada.wait(), 3)
        try:
            # El refresh mantiene el lock de cuenta: la revocación debe esperar.
            with pytest.raises(TimeoutError):
                await asyncio.wait_for(asyncio.shield(desvinculacion), 0.2)
        finally:
            continuar.set()
        _, reemplazo, _ = await refresh
        assert (await desvinculacion).status_code == 200

    assert len(conexiones) == 2
    async with sesiones() as sesion:
        tokens = (await sesion.scalars(select(RefreshTokenModel))).all()
        assert len(tokens) == 2
        assert all(token.revocado_en == AHORA for token in tokens)
        with pytest.raises(SesionInvalidaError):
            await auth(sesion).refresh(reemplazo)


async def test_jwt_previo_pierde_ficha_y_recupera_solo_nuevo_vinculo(sesiones, caso):
    from tests.integration.test_c07_agenda import registrar_turno

    await vincular_caso(caso)
    raw = await crear_refresh(sesiones, caso)
    escenario = caso["escenario"]
    turno_id = await registrar_turno(sesiones, escenario)
    headers_previos = escenario.headers("paciente")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        ruta = f'/api/v1/pacientes/{caso["pid"]}'
        assert (await cliente.get(ruta, headers=headers_previos)).status_code == 200
        assert (await desvincular_caso(caso)).status_code == 200
        assert (await cliente.get(ruta, headers=headers_previos)).status_code == 404
        assert (await cliente.patch(ruta, json={"telefono": "1144445555"},
                                    headers=headers_previos)).status_code == 404
        assert (await cliente.get("/api/v1/pacientes", headers=headers_previos)).json()["items"] == []
        detalle = await cliente.get(ruta, headers=escenario.headers())
        assert detalle.json()["cuenta"] is None
        historial = await cliente.get(ruta + "/turnos", headers=escenario.headers())
        assert [turno["id"] for turno in historial.json()] == [turno_id]
        refresh = await cliente.post("/api/v1/auth/refresh",
                                     headers={"Cookie": f"refresh_token={raw}"})
        assert refresh.status_code == 401
        assert "revocad" in refresh.json()["detail"]

        nueva = await cliente.post("/api/v1/pacientes", headers=escenario.headers(), json={
            "nombre": "Otra", "apellido": "Ficha", "dni": "44444444",
            "telefono": "1133334444", "email": "otra@example.test",
        })
        assert nueva.status_code == 201
        nuevo_id = nueva.json()["id"]
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                    json={"paciente_id": nuevo_id}, headers=escenario.headers())
        assert respuesta.status_code == 200
        assert (await cliente.get(ruta, headers=headers_previos)).status_code == 404
        assert (await cliente.get(f"/api/v1/pacientes/{nuevo_id}", headers=headers_previos)).status_code == 200
        assert (await cliente.patch(f"/api/v1/pacientes/{nuevo_id}",
                    json={"telefono": "1144445555"}, headers=headers_previos)).status_code == 200
        detalle_nuevo = await cliente.get(f"/api/v1/pacientes/{nuevo_id}", headers=headers_previos)
        assert detalle_nuevo.json()["telefono"] == "1144445555"
        assert "cuenta" not in detalle_nuevo.json()
        historial = await cliente.get(ruta + "/turnos", headers=escenario.headers())
        assert [turno["id"] for turno in historial.json()] == [turno_id]


async def test_revoca_vigentes_sin_reescribir_revocados_ni_password(sesiones, caso):
    await vincular_caso(caso)
    await crear_refresh(sesiones, caso, "token-vigente")
    anterior = AHORA - timedelta(hours=1)
    await crear_refresh(sesiones, caso, "token-revocado", anterior)
    async with sesiones() as sesion:
        password_antes = (await sesion.get(UsuarioModel, caso["uid"])).password_hash

    assert (await desvincular_caso(caso)).status_code == 200
    async with sesiones() as sesion:
        tokens = {t.token_hash: t.revocado_en for t in (await sesion.scalars(select(RefreshTokenModel))).all()}
        assert tokens == {calcular_token_hash("token-vigente"): AHORA,
                          calcular_token_hash("token-revocado"): anterior}
        assert (await sesion.get(UsuarioModel, caso["uid"])).password_hash == password_antes


async def test_predicado_desvincular_rechaza_usuario_obsoleto_sin_cambios(sesiones, caso):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    await vincular_caso(caso)
    async with sesiones() as sesion:
        repo = RepositorioVinculacionSQL(sesion)
        assert not await repo.desvincular_ficha(1, caso["pid"], caso["actor"])
        assert not await repo.desvincular_ficha(2, caso["pid"], caso["uid"])
        await sesion.commit()
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "vinculada"


@pytest.mark.parametrize("primera", ["desvincular", "vincular"])
async def test_vincular_compite_con_desvincular_respetando_orden_serial(sesiones, caso, monkeypatch, primera):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    await vincular_caso(caso)
    async with sesiones() as sesion:
        candidato = UsuarioModel(consultorio_id=1, nombre_usuario="otra-cuenta",
            email="otra-cuenta@example.test", password_hash="sintetico", rol="paciente",
            email_verificado=True, creado_en=AHORA, actualizado_en=AHORA,
            aviso_privacidad_aceptado_en=AHORA, aviso_privacidad_version="prueba")
        sesion.add(candidato)
        await sesion.flush()
        solicitud = SolicitudVinculacionModel(consultorio_id=1, usuario_id=candidato.id,
            dni_declarado="12345671", estado="pendiente", creada_en=AHORA)
        sesion.add(solicitud)
        await sesion.commit()
        nuevo_uid, nuevo_sid = candidato.id, solicitud.id

    bloqueada, competidora, continuar = asyncio.Event(), asyncio.Event(), asyncio.Event()
    conexiones = set()
    original = RepositorioVinculacionSQL.bloquear_ficha
    entradas = 0

    async def ordenar(repo, *args):
        nonlocal entradas
        entradas += 1
        es_primera = entradas == 1
        conexiones.add(await repo.sesion.scalar(text("select pg_backend_pid()")))
        if not es_primera:
            competidora.set()
        ficha = await original(repo, *args)
        if es_primera:
            bloqueada.set()
            await continuar.wait()
        return ficha

    monkeypatch.setattr(RepositorioVinculacionSQL, "bloquear_ficha", ordenar)

    async def vincular_otra():
        escenario = caso["escenario"]
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                    base_url="http://test") as cliente:
            return await cliente.post(f"/api/v1/solicitudes-vinculacion/{nuevo_sid}/vincular",
                    headers=escenario.headers(), json={"paciente_id": caso["pid"]})

    operaciones = {"desvincular": lambda: desvincular_caso(caso), "vincular": vincular_otra}
    segunda = "vincular" if primera == "desvincular" else "desvincular"
    tarea_primera = asyncio.create_task(operaciones[primera]())
    await asyncio.wait_for(bloqueada.wait(), 3)
    tarea_segunda = asyncio.create_task(operaciones[segunda]())
    try:
        await asyncio.wait_for(competidora.wait(), 3)
    finally:
        continuar.set()
    respuesta_primera, respuesta_segunda = await asyncio.gather(tarea_primera, tarea_segunda)
    assert len(conexiones) == 2
    assert respuesta_primera.status_code == (200 if primera == "desvincular" else 409)
    assert respuesta_segunda.status_code == 200
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        vieja = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        nueva = await sesion.get(SolicitudVinculacionModel, nuevo_sid)
        assert ficha.usuario_id == (nuevo_uid if primera == "desvincular" else None)
        assert vieja.estado == "rechazada"
        assert vieja.paciente_id == caso["pid"]
        assert nueva.estado == ("vinculada" if primera == "desvincular" else "pendiente")
        assert nueva.paciente_id == (caso["pid"] if primera == "desvincular" else None)
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


@pytest.mark.parametrize("paso,error_sql,codigo", [
    ("flush", None, 500), ("commit", None, 500),
    ("commit", "40P01", 409), ("commit", "40001", 409),
])
async def test_flush_y_commit_fallidos_revierten_vinculo_resolucion_y_sesiones(
        sesiones, caso, monkeypatch, paso, error_sql, codigo):
    from sqlalchemy.ext.asyncio import AsyncSession

    await vincular_caso(caso)
    await crear_refresh(sesiones, caso)
    original_flush = AsyncSession.flush

    async def flush_y_fallar(sesion, *args, **kwargs):
        await original_flush(sesion, *args, **kwargs)
        if paso == "flush":
            raise RuntimeError("flush de desvinculación controlado")

    async def commit_fallido(sesion):
        await sesion.flush()
        if error_sql:
            await sesion.execute(text(
                f"DO $$ BEGIN RAISE EXCEPTION 'controlado' USING ERRCODE = '{error_sql}'; END $$"))
        raise RuntimeError("commit de desvinculación controlado")

    monkeypatch.setattr(AsyncSession, "flush", flush_y_fallar)
    monkeypatch.setattr(AsyncSession, "commit", commit_fallido)
    assert (await desvincular_caso(caso)).status_code == codigo
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        token = await sesion.scalar(select(RefreshTokenModel))
        assert ficha.usuario_id == caso["uid"]
        assert solicitud.estado == "vinculada"
        assert solicitud.motivo_rechazo is None
        assert token.revocado_en is None
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


@pytest.mark.parametrize("nuevo_usuario", [None, "actor"])
async def test_vinculo_cambiado_antes_de_escribir_responde_409_y_revierte(
        sesiones, caso, monkeypatch, nuevo_usuario):
    from sqlalchemy import update
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    await vincular_caso(caso)
    await crear_refresh(sesiones, caso)
    original = RepositorioVinculacionSQL.desvincular_ficha

    async def cambiar_y_comprobar_predicado(repo, cid, pid, uid):
        await repo.sesion.execute(update(PacienteModel).where(PacienteModel.id == pid).values(
            usuario_id=caso["actor"] if nuevo_usuario == "actor" else None))
        return await original(repo, cid, pid, uid)

    monkeypatch.setattr(RepositorioVinculacionSQL, "desvincular_ficha", cambiar_y_comprobar_predicado)
    assert (await desvincular_caso(caso)).status_code == 409
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "vinculada"
        assert (await sesion.scalar(select(RefreshTokenModel))).revocado_en is None


async def test_solicitud_existente_conserva_dni_declarado_al_desvincular(sesiones, caso):
    await vincular_caso(caso)
    async with sesiones() as sesion:
        (await sesion.get(PacienteModel, caso["pid"])).dni = "76543210"
        await sesion.commit()

    assert (await desvincular_caso(caso)).status_code == 200
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert solicitud.dni_declarado == "12345671"
        assert solicitud.estado == "rechazada"
        assert solicitud.paciente_id == caso["pid"]
        assert (await sesion.get(PacienteModel, caso["pid"])).dni == "76543210"


async def test_desvincular_exige_cuerpo_con_motivo(caso):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/pacientes/{caso["pid"]}/desvincular',
                                       headers=escenario.headers())
    assert respuesta.status_code == 422
