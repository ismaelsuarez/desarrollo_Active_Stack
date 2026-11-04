import asyncio

import httpx
import pytest
from sqlalchemy import select, text

from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel
from app.infrastructure.db.models import PacienteModel, TurnoModel, TurnoHistorialModel, UsuarioModel
from tests.integration.c07_support import AHORA, preparar_escenario
from tests.integration.test_c07_agenda import registrar_turno

pytestmark = pytest.mark.integration


@pytest.fixture
async def caso(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.activo = False
        await sesion.commit()
    return escenario


async def test_reactivar_cambia_solo_activo_y_conserva_ficha(sesiones, caso):
    turno_id = await registrar_turno(sesiones, caso)
    async with sesiones() as sesion:
        anterior = (await sesion.execute(select(PacienteModel.__table__).where(
            PacienteModel.id == caso.pacientes[1]))).mappings().one()
        turno_anterior = (await sesion.execute(select(TurnoModel.__table__).where(
            TurnoModel.id == turno_id))).mappings().one()
        historial_anterior = (await sesion.execute(select(TurnoHistorialModel.__table__).where(
            TurnoHistorialModel.turno_id == turno_id))).mappings().all()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/pacientes/{caso.pacientes[1]}/reactivar", headers=caso.headers())
    assert respuesta.status_code == 200
    async with sesiones() as sesion:
        posterior = (await sesion.execute(select(PacienteModel.__table__).where(
            PacienteModel.id == caso.pacientes[1]))).mappings().one()
        assert posterior["activo"] is True
        assert {k: v for k, v in posterior.items() if k != "activo"} == {
            k: v for k, v in anterior.items() if k != "activo"
        }
        assert (await sesion.execute(select(TurnoModel.__table__).where(
            TurnoModel.id == turno_id))).mappings().one() == turno_anterior
        assert (await sesion.execute(select(TurnoHistorialModel.__table__).where(
            TurnoHistorialModel.turno_id == turno_id))).mappings().all() == historial_anterior
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
        assert (await sesion.scalars(select(SolicitudVinculacionModel))).all() == []


@pytest.mark.parametrize("rol,objetivo,cuerpo,codigo", [
    ("administrador", "propio", {}, 200),
    ("recepcion", "activa", None, 409),
    ("recepcion", "ajena", None, 404),
    ("recepcion", "inexistente", None, 404),
    ("profesional", "propio", None, 403),
    ("paciente", "propio", None, 403),
    ("administrativo", "propio", None, 403),
    (None, "propio", None, 401),
    ("recepcion", "propio", {"motivo": "no necesario"}, 422),
    ("recepcion", "propio", {"activo": True}, 422),
    ("recepcion", "propio", {"activo": False}, 422),
    ("recepcion", "propio", {"consultorio_id": 2}, 422),
])
async def test_reactivacion_respuestas_estrictas_sin_mutaciones_en_rechazo(sesiones, caso, rol, objetivo, cuerpo, codigo):
    if objetivo == "activa":
        async with sesiones() as sesion:
            ficha = await sesion.get(PacienteModel, caso.pacientes[1])
            ficha.activo = True
            await sesion.commit()
    pid = caso.pacientes[2] if objetivo == "ajena" else (99999 if objetivo == "inexistente" else caso.pacientes[1])
    async with sesiones() as sesion:
        fichas_antes = (await sesion.execute(select(PacienteModel.__table__).order_by(
            PacienteModel.id))).mappings().all()
    argumentos = {"headers": caso.headers(rol) if rol else {}}
    if cuerpo is not None:
        argumentos["json"] = cuerpo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/pacientes/{pid}/reactivar", **argumentos)
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso.pacientes[1])
        assert ficha.activo is (codigo == 200 or objetivo == "activa")
        if codigo != 200:
            assert (await sesion.execute(select(PacienteModel.__table__).order_by(
                PacienteModel.id))).mappings().all() == fichas_antes


async def reactivar(caso):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app),
                                base_url="http://test") as cliente:
        return await cliente.post(f"/api/v1/pacientes/{caso.pacientes[1]}/reactivar",
                                  headers=caso.headers())


async def test_doble_reactivacion_serializa_y_solo_una_prospera(sesiones, caso, monkeypatch):
    from app.infrastructure.db.pacientes import RepositorioPacientesSQL

    original = RepositorioPacientesSQL.obtener
    barrera, conexiones = asyncio.Barrier(2), set()

    async def coincidir_antes_del_lock(repo, *args, **kwargs):
        assert kwargs["bloquear"] is True
        conexiones.add(await repo.sesion.scalar(text("select pg_backend_pid()")))
        await asyncio.wait_for(barrera.wait(), 3)
        return await original(repo, *args, **kwargs)

    monkeypatch.setattr(RepositorioPacientesSQL, "obtener", coincidir_antes_del_lock)
    respuestas = await asyncio.gather(reactivar(caso), reactivar(caso))
    assert sorted(r.status_code for r in respuestas) == [200, 409]
    assert len(conexiones) == 2
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, caso.pacientes[1])).activo is True
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
        assert (await sesion.scalars(select(SolicitudVinculacionModel))).all() == []


@pytest.mark.parametrize("primera", ["reactivar", "vincular"])
async def test_reactivacion_y_vinculo_compiten_con_dos_conexiones(sesiones, caso, monkeypatch, primera):
    from app.infrastructure.db.pacientes import RepositorioPacientesSQL
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    turno_id = await registrar_turno(sesiones, caso)
    uid = caso.usuarios[1, "paciente"]
    async with sesiones() as sesion:
        (await sesion.get(UsuarioModel, uid)).email_verificado = True
        solicitud = SolicitudVinculacionModel(consultorio_id=1, usuario_id=uid,
            dni_declarado="12345671", estado="pendiente", creada_en=AHORA)
        sesion.add(solicitud)
        await sesion.commit()
        sid = solicitud.id
        turno_anterior = (await sesion.execute(select(TurnoModel.__table__).where(
            TurnoModel.id == turno_id))).mappings().one()

    bloqueada, competidora, continuar = asyncio.Event(), asyncio.Event(), asyncio.Event()
    conexiones = set()
    original_reactivar = RepositorioPacientesSQL.obtener
    original_vincular = RepositorioVinculacionSQL.bloquear_ficha

    async def ordenar(accion, original, repo, *args, **kwargs):
        conexiones.add(await repo.sesion.scalar(text("select pg_backend_pid()")))
        if accion != primera:
            competidora.set()
        ficha = await original(repo, *args, **kwargs)
        if accion == primera:
            bloqueada.set()
            await continuar.wait()
        return ficha

    async def obtener_para_reactivar(repo, *args, **kwargs):
        return await ordenar("reactivar", original_reactivar, repo, *args, **kwargs)

    async def bloquear_para_vincular(repo, *args, **kwargs):
        return await ordenar("vincular", original_vincular, repo, *args, **kwargs)

    monkeypatch.setattr(RepositorioPacientesSQL, "obtener", obtener_para_reactivar)
    monkeypatch.setattr(RepositorioVinculacionSQL, "bloquear_ficha", bloquear_para_vincular)

    async def vincular():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app),
                                    base_url="http://test") as cliente:
            return await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid}/vincular",
                json={"paciente_id": caso.pacientes[1]}, headers=caso.headers())

    operaciones = {"reactivar": lambda: reactivar(caso), "vincular": vincular}
    segunda = "vincular" if primera == "reactivar" else "reactivar"
    tarea_primera = asyncio.create_task(operaciones[primera]())
    await asyncio.wait_for(bloqueada.wait(), 3)
    tarea_segunda = asyncio.create_task(operaciones[segunda]())
    try:
        await asyncio.wait_for(competidora.wait(), 3)
    finally:
        continuar.set()
    respuestas = await asyncio.gather(tarea_primera, tarea_segunda)
    assert len(conexiones) == 2
    assert [r.status_code for r in respuestas] == ([200, 200] if primera == "reactivar" else [409, 200])
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, caso.pacientes[1])
        solicitud = await sesion.get(SolicitudVinculacionModel, sid)
        assert ficha.activo is True
        assert ficha.usuario_id == (uid if primera == "reactivar" else None)
        assert solicitud.estado == ("vinculada" if primera == "reactivar" else "pendiente")
        assert solicitud.paciente_id == (ficha.id if primera == "reactivar" else None)
        assert (await sesion.execute(select(TurnoModel.__table__).where(
            TurnoModel.id == turno_id))).mappings().one() == turno_anterior
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
    if primera == "vincular":
        assert (await vincular()).status_code == 200
        async with sesiones() as sesion:
            assert (await sesion.get(PacienteModel, caso.pacientes[1])).usuario_id == uid


async def test_no_hay_desactivacion_por_ruta_ni_patch(caso):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=caso.app),
                                base_url="http://test") as cliente:
        ruta = f"/api/v1/pacientes/{caso.pacientes[1]}"
        assert (await cliente.post(ruta + "/desactivar", headers=caso.headers())).status_code == 404
        assert (await cliente.patch(ruta, json={"activo": True}, headers=caso.headers())).status_code == 422
        assert (await cliente.delete(ruta, headers=caso.headers())).status_code == 405
