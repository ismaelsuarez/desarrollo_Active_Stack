"""RN-62: vinculación manual atómica, con PostgreSQL real."""
import asyncio
import pytest
import httpx
from sqlalchemy import text, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.infrastructure.db.account_models import SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, UsuarioModel
from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def caso(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with sesiones() as sesion:
        usuario = await sesion.get(UsuarioModel, escenario.usuarios[1, "paciente"])
        usuario.email_verificado = True
        solicitud = SolicitudVinculacionModel(
            consultorio_id=1, usuario_id=usuario.id, dni_declarado="12345671",
            estado="pendiente", creada_en=AHORA,
        )
        sesion.add(solicitud)
        await sesion.commit()
        return {"escenario": escenario, "pid": escenario.pacientes[1],
                "uid": usuario.id, "sid": solicitud.id,
                "actor": escenario.usuarios[1, "recepcion"]}


async def test_repo_vincula_solicitud_y_ficha_en_una_transaccion(sesiones, caso):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    async with sesiones() as sesion:
        repo = RepositorioVinculacionSQL(sesion)
        solicitud = await repo.obtener_solicitud(1, caso["sid"])
        ficha = await repo.bloquear_ficha(1, caso["pid"])
        assert ficha.usuario_id is None
        assert await repo.vincular_solicitud(1, solicitud.id, solicitud.estado,
                                            ficha.id, caso["actor"], AHORA)
        assert await repo.vincular_ficha(1, ficha.id, caso["uid"], AHORA)
        await sesion.commit()

    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert ficha.usuario_id == caso["uid"]
        assert solicitud.estado == "vinculada"
        assert solicitud.paciente_id == ficha.id
        assert solicitud.resuelta_por_id == caso["actor"]
        assert solicitud.resuelta_en == AHORA


@pytest.mark.parametrize("estado,estado_leido,esperado", [
    ("pendiente", "pendiente", True),
    ("rechazada", "rechazada", True),
    ("vinculada", "vinculada", False),
    ("rechazada", "pendiente", False),
])
async def test_solicitud_usa_estado_leido_y_conserva_motivo(sesiones, caso, estado,
                                                         estado_leido, esperado):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    async with sesiones() as sesion:
        fila = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        fila.estado, fila.motivo_rechazo = estado, "motivo previo"
        await sesion.commit()
        repo = RepositorioVinculacionSQL(sesion)
        assert await repo.vincular_solicitud(1, fila.id, estado_leido, caso["pid"],
                                            caso["actor"], AHORA) is esperado
        await sesion.commit()
    async with sesiones() as sesion:
        fila = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert fila.estado == ("vinculada" if esperado else estado)
        assert fila.motivo_rechazo == "motivo previo"


@pytest.mark.parametrize("inactiva,ocupada", [(True, False), (False, True)])
async def test_ficha_incompatible_no_afecta_ninguna_fila(sesiones, caso, inactiva, ocupada):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        ficha.activo = not inactiva
        ficha.usuario_id = caso["actor"] if ocupada else None
        await sesion.commit()
        repo = RepositorioVinculacionSQL(sesion)
        assert not await repo.vincular_ficha(1, ficha.id, caso["uid"], AHORA)
        await sesion.commit()
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        assert ficha.usuario_id == (caso["actor"] if ocupada else None)
        assert ficha.activo is (not inactiva)


async def test_repositorio_no_encuentra_referencias_de_otro_consultorio(sesiones, caso):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    async with sesiones() as sesion:
        repo = RepositorioVinculacionSQL(sesion)
        assert await repo.obtener_solicitud(2, caso["sid"]) is None
        assert await repo.bloquear_ficha(2, caso["pid"]) is None
        assert not await repo.vincular_solicitud(2, caso["sid"], "pendiente", caso["pid"],
                                                caso["actor"], AHORA)
        assert not await repo.vincular_ficha(2, caso["pid"], caso["uid"], AHORA)


async def test_api_vincula_cuenta_verificada_con_ficha_elegida(sesiones, caso):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                                      json={"paciente_id": caso["pid"]}, headers=escenario.headers())
    assert respuesta.status_code == 200
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id == caso["uid"]


@pytest.mark.parametrize("variante,codigo", [
    ("rechazada", 200), ("vinculada", 409), ("inactiva", 409),
    ("ocupada", 409), ("sin_verificar", 409), ("cuenta_con_otra_ficha", 409),
    ("dni_cambiado", 200), ("ficha_ajena", 404), ("ficha_inexistente", 404),
    ("solicitud_inexistente", 404),
])
async def test_api_vinculacion_respeta_elegibilidad_y_revierte_rechazos(sesiones, caso,
                                                                    variante, codigo):
    escenario = caso["escenario"]
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        solicitud.motivo_rechazo = "motivo previo"
        if variante in ("rechazada", "vinculada"):
            solicitud.estado = variante
        elif variante == "inactiva":
            ficha.activo = False
        elif variante == "ocupada":
            ficha.usuario_id = caso["actor"]
        elif variante == "sin_verificar":
            (await sesion.get(UsuarioModel, caso["uid"])).email_verificado = False
        elif variante == "cuenta_con_otra_ficha":
            sesion.add(PacienteModel(consultorio_id=1, usuario_id=caso["uid"],
                       nombre="Otra", apellido="Ficha", dni="99999888", activo=True,
                       creado_en=AHORA, actualizado_en=AHORA))
        elif variante == "dni_cambiado":
            ficha.dni = "87654321"
        await sesion.commit()
        antes = (ficha.usuario_id, ficha.activo, ficha.dni, solicitud.estado,
                 solicitud.paciente_id, solicitud.resuelta_por_id, solicitud.resuelta_en)
    pid = escenario.pacientes[2] if variante == "ficha_ajena" else caso["pid"]
    pid = 999999 if variante == "ficha_inexistente" else pid
    sid = 999999 if variante == "solicitud_inexistente" else caso["sid"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid}/vincular",
                                      json={"paciente_id": pid}, headers=escenario.headers())
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso["pid"])
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert solicitud.motivo_rechazo == "motivo previo"
        if codigo == 200:
            assert ficha.usuario_id == caso["uid"]
            assert solicitud.estado == "vinculada"
            assert ficha.dni == antes[2]
        else:
            assert (ficha.usuario_id, ficha.activo, ficha.dni, solicitud.estado,
                    solicitud.paciente_id, solicitud.resuelta_por_id, solicitud.resuelta_en) == antes


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_vincular_denegado_a_otros_roles(sesiones, caso, rol):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                                      json={"paciente_id": caso["pid"]}, headers=escenario.headers(rol))
    assert respuesta.status_code == 403
    async with sesiones() as sesion:
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "pendiente"
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id is None


@pytest.mark.parametrize("extra", ["consultorio_id", "usuario_id", "estado"])
async def test_vincular_rechaza_campos_del_servidor(caso, extra):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                        json={"paciente_id": caso["pid"], extra: "privado"}, headers=escenario.headers())
    assert respuesta.status_code == 422
    assert "privado" not in respuesta.text


@pytest.mark.parametrize("estado,codigo", [("40P01", 409), ("40001", 409), ("23503", 500)])
async def test_error_real_postgres_despues_de_solicitud_revierte_todo(sesiones, caso,
                                                                  monkeypatch, estado, codigo):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    async def fallar(repo, *args):
        await repo.sesion.execute(text(
            f"DO $$ BEGIN RAISE EXCEPTION 'Fallo controlado' USING ERRCODE = '{estado}'; END $$"))

    monkeypatch.setattr(RepositorioVinculacionSQL, "vincular_ficha", fallar)
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,
                                                             raise_app_exceptions=False),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                        json={"paciente_id": caso["pid"]}, headers=escenario.headers())
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, caso["sid"])
        assert solicitud.estado == "pendiente"
        assert solicitud.resuelta_en is None
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id is None


async def nueva_cuenta_y_solicitud(sesiones):
    async with sesiones() as sesion:
        usuario = UsuarioModel(consultorio_id=1, nombre_usuario="otra-cuenta",
                    email="otra-cuenta@example.test", password_hash="sintetico",
                    rol="paciente", activo=True, email_verificado=True,
                    creado_en=AHORA, actualizado_en=AHORA,
                    aviso_privacidad_aceptado_en=AHORA, aviso_privacidad_version="prueba")
        sesion.add(usuario)
        await sesion.flush()
        solicitud = SolicitudVinculacionModel(consultorio_id=1, usuario_id=usuario.id,
                    dni_declarado="12345671", estado="pendiente", creada_en=AHORA)
        sesion.add(solicitud)
        await sesion.commit()
        return usuario.id, solicitud.id


@pytest.mark.parametrize("carrera", ["dos_cuentas_una_ficha", "una_solicitud_dos_fichas", "compatibles"])
async def test_vinculos_concurrentes_usan_conexiones_independientes(sesiones, caso,
                                                                 monkeypatch, carrera):
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    otra_uid, otra_sid = await nueva_cuenta_y_solicitud(sesiones)
    async with sesiones() as sesion:
        otra_ficha = PacienteModel(consultorio_id=1, nombre="Otra", apellido="Ficha",
                                  dni="99123456", activo=True, creado_en=AHORA, actualizado_en=AHORA)
        sesion.add(otra_ficha)
        await sesion.commit()
        otra_pid = otra_ficha.id
    sid2 = caso["sid"] if carrera == "una_solicitud_dos_fichas" else otra_sid
    pid2 = caso["pid"] if carrera == "dos_cuentas_una_ficha" else otra_pid
    barrera, conexiones = asyncio.Barrier(2), set()
    original = RepositorioVinculacionSQL.obtener_solicitud

    async def leer_antes_de_competir(repo, cid, sid):
        resultado = await original(repo, cid, sid)
        conexiones.add(await repo.sesion.scalar(select(func.pg_backend_pid())))
        await asyncio.wait_for(barrera.wait(), 10)
        return resultado

    monkeypatch.setattr(RepositorioVinculacionSQL, "obtener_solicitud", leer_antes_de_competir)
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuestas = await asyncio.wait_for(asyncio.gather(
            cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                         json={"paciente_id": caso["pid"]}, headers=escenario.headers()),
            cliente.post(f"/api/v1/solicitudes-vinculacion/{sid2}/vincular",
                         json={"paciente_id": pid2}, headers=escenario.headers()),
        ), 15)
    assert len(conexiones) == 2
    assert sorted(r.status_code for r in respuestas) == ([200, 200] if carrera == "compatibles" else [200, 409])
    async with sesiones() as sesion:
        fichas = (await sesion.scalars(select(PacienteModel).where(
            PacienteModel.id.in_((caso["pid"], otra_pid))))).all()
        solicitudes = (await sesion.scalars(select(SolicitudVinculacionModel))).all()
        vinculadas = [s for s in solicitudes if s.estado == "vinculada"]
        assert len(vinculadas) == (2 if carrera == "compatibles" else 1)
        assert len([f for f in fichas if f.usuario_id is not None]) == len(vinculadas)
        assert all(s.estado == "pendiente" for s in solicitudes if s not in vinculadas)
        assert all(s.resuelta_en is None for s in solicitudes if s not in vinculadas)


async def test_fallo_commit_no_anuncia_exito_y_revierte_vinculo(engine, sesiones, caso):
    eventos = []

    class CommitFallido(AsyncSession):
        async def commit(self):
            await self.flush()
            raise RuntimeError("commit controlado")

        async def rollback(self):
            eventos.append("rollback")
            await super().rollback()

    escenario = caso["escenario"]
    escenario.app.state.session_factory = async_sessionmaker(engine, class_=CommitFallido,
                                                             expire_on_commit=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app,
                                                             raise_app_exceptions=False),
                                base_url="http://test") as cliente:
        respuesta = await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                        json={"paciente_id": caso["pid"]}, headers=escenario.headers())
    assert respuesta.status_code == 500
    assert eventos == ["rollback"]
    async with sesiones() as sesion:
        assert (await sesion.get(SolicitudVinculacionModel, caso["sid"])).estado == "pendiente"
        assert (await sesion.get(PacienteModel, caso["pid"])).usuario_id is None


async def test_lista_solicitudes_pendientes_y_resueltas_muestra_ficha_minima(sesiones, caso):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        pendiente = await cliente.get("/api/v1/solicitudes-vinculacion?estado=pendiente",
                                      headers=escenario.headers())
        assert pendiente.status_code == 200
        assert pendiente.json()["total"] == 1
        item = pendiente.json()["items"][0]
        assert item["dni_declarado"] == "12345671"
        assert item["email"] == "paciente1@example.test"
        assert item["email_verificado"] is True
        assert item["ficha_existente"] == {"id": caso["pid"], "nombre": "Ana", "apellido": "Prueba"}
        assert "ficha_vinculada" not in item
        assert "password_hash" not in item
        await cliente.post(f'/api/v1/solicitudes-vinculacion/{caso["sid"]}/vincular',
                          json={"paciente_id": caso["pid"]}, headers=escenario.headers())
        vacia = await cliente.get("/api/v1/solicitudes-vinculacion?estado=pendiente",
                                 headers=escenario.headers())
        completa = await cliente.get("/api/v1/solicitudes-vinculacion", headers=escenario.headers())
    assert vacia.json()["items"] == []
    assert vacia.json()["total"] == 0
    assert completa.json()["items"][0]["ficha_vinculada"] == item["ficha_existente"]
    assert completa.json()["items"][0]["resuelta_por_id"] == caso["actor"]


async def test_lista_solicitudes_pagina_estados_y_aisla_consultorio(sesiones, caso):
    _, otra_sid = await nueva_cuenta_y_solicitud(sesiones)
    escenario = caso["escenario"]
    async with sesiones() as sesion:
        solicitud = await sesion.get(SolicitudVinculacionModel, otra_sid)
        solicitud.estado, solicitud.motivo_rechazo = "rechazada", "Revisión manual"
        sesion.add(SolicitudVinculacionModel(consultorio_id=2,
                    usuario_id=escenario.usuarios[2, "paciente"], dni_declarado="12345672",
                    estado="pendiente", creada_en=AHORA))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        primera = (await cliente.get("/api/v1/solicitudes-vinculacion?limit=1", headers=escenario.headers())).json()
        segunda = (await cliente.get("/api/v1/solicitudes-vinculacion?limit=1&offset=1", headers=escenario.headers())).json()
        vacia = (await cliente.get("/api/v1/solicitudes-vinculacion?offset=20", headers=escenario.headers())).json()
        resueltas = (await cliente.get("/api/v1/solicitudes-vinculacion?estado=rechazada", headers=escenario.headers())).json()
    assert primera["total"] == segunda["total"] == vacia["total"] == 2
    assert primera["items"][0]["id"] == caso["sid"]
    assert segunda["items"][0]["id"] == otra_sid
    assert vacia["items"] == []
    assert resueltas["total"] == 1
    assert resueltas["items"][0]["motivo_rechazo"] == "Revisión manual"
    assert "ficha_vinculada" not in resueltas["items"][0]


@pytest.mark.parametrize("consulta", ["estado=inventado", "limit=0", "limit=101", "offset=-1", "consultorio_id=2"])
async def test_lista_solicitudes_valida_consulta(caso, consulta):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.get(f"/api/v1/solicitudes-vinculacion?{consulta}", headers=escenario.headers())
    assert respuesta.status_code == 422


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_lista_solicitudes_restringida_al_personal(caso, rol):
    escenario = caso["escenario"]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        respuesta = await cliente.get("/api/v1/solicitudes-vinculacion", headers=escenario.headers(rol))
    assert respuesta.status_code == 403
