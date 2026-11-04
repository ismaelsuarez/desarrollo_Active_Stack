"""RN-62: rechazo y correo durable sólo después del commit."""
import httpx
import pytest
import os
import asyncio
from uuid import uuid4
from sqlalchemy import select, text, func

from app.api.v1.routers.cuentas import get_enviador_correo
from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, UsuarioModel
from tests.integration.test_c08_linking import caso

pytestmark = pytest.mark.integration


async def test_rechazo_verificado_programa_y_despacha_tras_commit(sesiones, caso):
    enviados = []

    class Correo:
        async def enviar(self, destinatario, asunto, cuerpo):
            async with sesiones() as sesion:
                solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
                assert solicitud.estado == "rechazada"
            enviados.append((destinatario, cuerpo))

    escenario = caso["escenario"]
    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            json={"motivo": "motivo privado 12345671"}, headers=escenario.headers())
    assert respuesta.status_code == 200
    assert len(enviados) == 1
    assert enviados[0][0] == "paciente1@example.test"
    assert "consultorio" in enviados[0][1].lower()
    assert "motivo privado" not in enviados[0][1]
    assert "12345671" not in enviados[0][1]
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        notificaciones = (await sesion.scalars(select(NotificacionModel))).all()
        assert solicitud.estado == "rechazada"
        assert solicitud.motivo_rechazo == "motivo privado 12345671"
        assert solicitud.resuelta_por_id == caso["actor"]
        assert len(notificaciones) == 1
        assert notificaciones[0].tipo == "vinculacion_rechazada"
        assert notificaciones[0].estado == "enviada"


@pytest.mark.parametrize("verificado,sin_cuerpo", [(True, False), (False, False), (False, True)])
async def test_motivo_opcional_y_cuenta_sin_verificar_no_envia_correo(sesiones, caso,
                                                                 verificado, sin_cuerpo):
    enviados = []

    class Correo:
        async def enviar(self, *argumentos):
            enviados.append(argumentos)

    async with sesiones() as sesion:
        (await sesion.get(UsuarioModel, caso["uid"])).email_verificado = verificado
        await sesion.commit()
    escenario = caso["escenario"]
    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        opciones = {} if sin_cuerpo else {"json": {}}
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            headers=escenario.headers("administrador"), **opciones)
        repetida = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            json={}, headers=escenario.headers())
    assert respuesta.status_code == 200
    assert repetida.status_code == 409
    assert len(enviados) == (1 if verificado else 0)
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert solicitud.estado == "rechazada"
        assert solicitud.motivo_rechazo is None
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id is None
        assert len((await sesion.scalars(select(NotificacionModel))).all()) == (1 if verificado else 0)


@pytest.mark.parametrize("error_sql,codigo", [(None, 500), ("40P01", 409), ("40001", 409)])
async def test_fallo_outbox_revierte_rechazo_y_notificacion(sesiones, caso, monkeypatch,
                                                         error_sql, codigo):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    original = RepositorioVinculacionSQL.programar_rechazo

    async def escribir_y_fallar(repo, *args):
        await original(repo, *args)
        if error_sql:
            await repo.sesion.execute(text(
                f"DO $$ BEGIN RAISE EXCEPTION 'controlado' USING ERRCODE = '{error_sql}'; END $$"))
        raise RuntimeError("programación controlada")

    monkeypatch.setattr(RepositorioVinculacionSQL, "programar_rechazo", escribir_y_fallar)
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,
                                                             raise_app_exceptions=False),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                                      json={}, headers=escenario.headers())
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "pendiente"
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


async def test_fallo_smtp_conserva_rechazo_y_trabajo_durable(sesiones, caso, caplog):
    class CorreoFallido:
        async def enviar(self, *argumentos):
            raise OSError("secreto-y-dni-no-registrables")

    escenario = caso["escenario"]
    escenario.app.dependency_overrides[get_enviador_correo] = CorreoFallido
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                                      json={}, headers=escenario.headers())
    assert respuesta.status_code == 200
    assert "secreto-y-dni-no-registrables" not in caplog.text
    async with sesiones() as sesion:
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "rechazada"
        notificacion = await sesion.scalar(select(NotificacionModel))
        assert notificacion.estado == "programada"
        assert notificacion.intentos == 1
        assert notificacion.ultimo_error == "OSError"


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_rechazo_solo_personal(caso, rol):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                                      json={}, headers=escenario.headers(rol))
    assert respuesta.status_code == 403


async def test_rechazo_valida_extras_y_recurso_ajeno(caso):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        extra = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            json={"usuario_id": 2}, headers=escenario.headers())
        ajena = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            json={}, headers=escenario.headers(consultorio=2))
    assert extra.status_code == 422
    assert ajena.status_code == 404


async def test_rechazo_se_entrega_por_smtp_real_en_mailpit(sesiones, caso):
    destinatario = f"rechazo-{uuid4().hex}@example.test"
    async with sesiones() as sesion:
        (await sesion.get(UsuarioModel, caso["uid"])).email = destinatario
        await sesion.commit()
    escenario = caso["escenario"]
    escenario.app.state.settings = escenario.app.state.settings.model_copy(update={
        "smtp_host": os.environ["SMTP_TEST_HOST"],
        "smtp_port": int(os.environ["SMTP_TEST_PORT"]), "smtp_starttls": False,
    })
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                            json={"motivo": "dato-privado 12345671"}, headers=escenario.headers())
    assert respuesta.status_code == 200
    async with httpx.AsyncClient(base_url=os.environ["MAILPIT_API_URL"], trust_env=False) as smtp:
        listado = (await smtp.get("/api/v1/messages", params={"limit": 1000})).json()
        mensajes = [m for m in listado["messages"]
                    if any(p["Address"] == destinatario for p in m["To"])]
        assert len(mensajes) == 1
        mensaje = (await smtp.get(f'/api/v1/message/{mensajes[0]["ID"]}')).json()
    assert "consultorio" in mensaje["Text"].lower()
    assert "dato-privado" not in mensaje["Text"]
    assert "12345671" not in mensaje["Text"]


async def test_rechazo_y_vinculo_concurrentes_conservan_solo_la_resolucion_ganadora(sesiones, caso,
                                                                               monkeypatch):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    class Correo:
        async def enviar(self, *args):
            pass

    barrera, conexiones = asyncio.Barrier(2), set()
    original = RepositorioVinculacionSQL.obtener_solicitud

    async def leer_y_esperar(repo, cid, sid):
        solicitud = await original(repo, cid, sid)
        conexiones.add(await repo.sesion.scalar(select(func.pg_backend_pid())))
        await asyncio.wait_for(barrera.wait(), 10)
        return solicitud

    monkeypatch.setattr(RepositorioVinculacionSQL, "obtener_solicitud", leer_y_esperar)
    escenario = caso["escenario"]
    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuestas = await asyncio.wait_for(asyncio.gather(
            cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                         json={"paciente_id": caso["pid"]}, headers=escenario.headers()),
            cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                         json={"motivo": "Revisión"}, headers=escenario.headers()),
        ), 15)
    assert sorted(r.status_code for r in respuestas) == [200, 409]
    assert len(conexiones) == 2
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        ficha = await sesion.get(PacienteModel, caso["pid"])
        notificaciones = (await sesion.scalars(select(NotificacionModel))).all()
        if solicitud.estado == "vinculada":
            assert ficha.usuario_id == caso["uid"]
            assert notificaciones == []
        else:
            assert solicitud.estado == "rechazada"
            assert ficha.usuario_id is None
            assert len(notificaciones) == 1


async def test_rechazada_puede_vincularse_despues_sin_borrar_motivo(sesiones, caso):
    class Correo:
        async def enviar(self, *args):
            pass

    escenario = caso["escenario"]
    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        rechazo = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                                     json={"motivo": "Verificar identidad"}, headers=escenario.headers())
        vinculo = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                                     json={"paciente_id": caso["pid"]}, headers=escenario.headers())
        repetido = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/rechazar',
                                     json={}, headers=escenario.headers())
    assert rechazo.status_code == vinculo.status_code == 200
    assert repetido.status_code == 409
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert solicitud.estado == "vinculada"
        assert solicitud.motivo_rechazo == "Verificar identidad"
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]
        assert len((await sesion.scalars(select(NotificacionModel))).all()) == 1
