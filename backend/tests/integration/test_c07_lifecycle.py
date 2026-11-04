from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select, text

from app.infrastructure.db.models import ConsultorioModel, TurnoHistorialModel, TurnoModel
from tests.integration.c07_support import AHORA, INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


async def turno(sesiones, escenario, estado="pendiente", consultorio=1, marcado=False):
    from app.infrastructure.db.models import ProfesionalModel
    async with sesiones() as sesion:
        profesional = await sesion.get(ProfesionalModel, escenario.profesionales[consultorio])
        modelo = TurnoModel(
            consultorio_id=consultorio, paciente_id=escenario.pacientes[consultorio],
            profesional_id=profesional.id, box_id=profesional.box_id,
            prestacion_id=escenario.prestaciones[consultorio], inicio=INICIO,
            fin=INICIO + timedelta(minutes=30), estado=estado,
            creado_en=AHORA, actualizado_en=AHORA, origen="recepcion",
            marcado_sin_confirmar_en=AHORA if marcado else None,
        )
        sesion.add(modelo)
        await sesion.commit()
        return modelo.id


async def hechos(sesiones, identificador):
    async with sesiones() as sesion:
        return list((await sesion.scalars(select(TurnoHistorialModel).where(
            TurnoHistorialModel.turno_id == identificador,
        ).order_by(TurnoHistorialModel.id))).all())


async def test_confirmar_pendiente_confirma_estado_actor_fecha_e_historial(sesiones, escenario):
    identificador = await turno(sesiones, escenario)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/confirmar", headers=escenario.headers(), json={})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "confirmado"
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, identificador)
        assert persistido.confirmado_en == AHORA
        assert persistido.actualizado_en == AHORA
    historia = await hechos(sesiones, identificador)
    assert len(historia) == 1
    assert historia[0].accion == "confirmar"
    assert historia[0].usuario_id == escenario.usuarios[1, "recepcion"]
    assert historia[0].ocurrido_en == AHORA


@pytest.mark.parametrize("estado", ["confirmado", "cancelado", "liberado", "atendido", "ausente"])
async def test_confirmar_estado_no_pendiente_rechaza_sin_historial(sesiones, escenario, estado):
    identificador = await turno(sesiones, escenario, estado=estado)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/confirmar", headers=escenario.headers(), json={})
    assert respuesta.status_code == 403
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_confirmar_rol_no_autorizado_rechaza(sesiones, escenario, rol):
    identificador = await turno(sesiones, escenario)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/confirmar", headers=escenario.headers(rol), json={})
    assert respuesta.status_code == 403
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("consulta", ["ajeno", "inexistente", "extra"])
async def test_confirmar_rechaza_referencia_ajena_o_entrada_extra(sesiones, escenario, consulta):
    identificador = await turno(sesiones, escenario, consultorio=2 if consulta == "ajeno" else 1)
    destino = identificador + 999 if consulta == "inexistente" else identificador
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{destino}/confirmar", headers=escenario.headers(), json={"consultorio_id": 2} if consulta == "extra" else {})
    assert respuesta.status_code == (422 if consulta == "extra" else 404)
    assert await hechos(sesiones, identificador) == []


async def test_cancelar_con_motivo_conserva_fila_y_libera_hueco(sesiones, escenario):
    identificador = await turno(sesiones, escenario, estado="confirmado")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/cancelar", headers=escenario.headers(), json={"motivo": "Solicitado por teléfono"})
        assert respuesta.status_code == 200
        assert respuesta.json()["id"] == identificador
        assert respuesta.json()["estado"] == "cancelado"
        nuevo = await cliente.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert nuevo.status_code == 201
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, identificador)
        assert persistido.cancelado_en == AHORA
        assert persistido.cancelado_por_id == escenario.usuarios[1, "recepcion"]
        assert persistido.motivo_cancelacion == "Solicitado por teléfono"
    historia = await hechos(sesiones, identificador)
    assert len(historia) == 1
    assert historia[0].accion == "cancelar"
    assert historia[0].estado_anterior == "confirmado"
    assert historia[0].estado_nuevo == "cancelado"


@pytest.mark.parametrize("estado", ["pendiente", "atendido", "ausente", "cancelado", "liberado"])
async def test_cancelacion_solo_en_estados_modificables_y_motivo_opcional(sesiones, escenario, estado):
    identificador = await turno(sesiones, escenario, estado=estado)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/cancelar", headers=escenario.headers("administrador"))
    assert respuesta.status_code == (200 if estado == "pendiente" else 403)
    assert len(await hechos(sesiones, identificador)) == (1 if estado == "pendiente" else 0)


@pytest.mark.parametrize("modo,marcado,estado,esperado", [
    ("manual", False, "pendiente", 200),
    ("automatico", True, "pendiente", 200),
    ("automatico", False, "pendiente", 403),
    ("manual", True, "confirmado", 403),
    ("manual", True, "liberado", 403),
])
async def test_liberar_respeta_modo_marca_estado_y_trazabilidad(sesiones, escenario, modo, marcado, estado, esperado):
    identificador = await turno(sesiones, escenario, estado=estado, marcado=marcado)
    async with sesiones() as sesion:
        config = await sesion.get(ConsultorioModel, 1)
        config.modo_liberacion = modo
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/liberar", headers=escenario.headers("administrador"), json={})
        assert respuesta.status_code == esperado
        if esperado == 200:
            nuevo = await cliente.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
            assert nuevo.status_code == 201
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, identificador)
        assert persistido.estado.value == ("liberado" if esperado == 200 else estado)
        assert persistido.liberado_en == (AHORA if esperado == 200 else None)
    historia = await hechos(sesiones, identificador)
    assert len(historia) == (1 if esperado == 200 else 0)
    if historia:
        assert historia[0].accion == "liberar"
        assert historia[0].usuario_id == escenario.usuarios[1, "administrador"]
        assert historia[0].ocurrido_en == AHORA


async def test_profesional_marca_ausente_exactamente_al_inicio(sesiones, escenario):
    identificador = await turno(sesiones, escenario)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/ausente", headers=escenario.headers("profesional"), json={})
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "ausente"
    historia = await hechos(sesiones, identificador)
    assert len(historia) == 1
    assert historia[0].accion == "ausente"
    assert historia[0].usuario_id == escenario.usuarios[1, "profesional"]
    assert historia[0].ocurrido_en == INICIO


@pytest.mark.parametrize("rol", ["profesional", "recepcion", "administrador"])
@pytest.mark.parametrize("accion", ["atendido", "ausente"])
@pytest.mark.parametrize("estado", ["pendiente", "confirmado"])
@pytest.mark.parametrize("segundos", [-1, 0, 1])
async def test_atencion_y_ausencia_matriz_temporal_con_estado_historial_atomicos(sesiones, escenario, rol, accion, estado, segundos):
    identificador = await turno(sesiones, escenario, estado=estado)
    ahora = INICIO + timedelta(seconds=segundos)
    escenario.reloj.fijar(ahora)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers(rol), json={})
    assert respuesta.status_code == (403 if segundos < 0 else 200)
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, identificador)
        assert persistido.estado.value == (estado if segundos < 0 else accion)
    historia = await hechos(sesiones, identificador)
    assert len(historia) == (0 if segundos < 0 else 1)
    if historia:
        assert historia[0].usuario_id == escenario.usuarios[1, rol]
        assert historia[0].ocurrido_en == ahora
        assert historia[0].estado_anterior == estado
        assert historia[0].estado_nuevo == accion


@pytest.mark.parametrize("rol,esperado", [("recepcion", 200), ("administrador", 200), ("profesional", 403)])
async def test_corregir_ausente_agrega_hecho_y_preserva_historia_anterior(sesiones, escenario, rol, esperado):
    identificador = await turno(sesiones, escenario)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        ausente = await cliente.post(f"/api/v1/turnos/{identificador}/ausente", headers=escenario.headers(), json={})
        assert ausente.status_code == 200
        antes = await hechos(sesiones, identificador)
        corregido = await cliente.post(f"/api/v1/turnos/{identificador}/atendido", headers=escenario.headers(rol), json={})
        assert corregido.status_code == esperado
        if esperado == 200:
            assert corregido.json()["estado"] == "atendido"
            repetido = await cliente.post(f"/api/v1/turnos/{identificador}/atendido", headers=escenario.headers(rol), json={})
            cancelado = await cliente.post(f"/api/v1/turnos/{identificador}/cancelar", headers=escenario.headers(), json={})
            assert repetido.status_code == cancelado.status_code == 403
    despues = await hechos(sesiones, identificador)
    assert len(despues) == (2 if esperado == 200 else 1)
    assert despues[0].id == antes[0].id
    assert despues[0].accion == "ausente"
    assert despues[0].estado_nuevo == "ausente"
    if esperado == 200:
        assert despues[1].accion == "corregir"
        assert despues[1].estado_anterior == "ausente"
        assert despues[1].estado_nuevo == "atendido"
        assert despues[1].usuario_id == escenario.usuarios[1, rol]


@pytest.mark.parametrize("accion", ["atendido", "ausente"])
@pytest.mark.parametrize("caso", ["rol_paciente", "rol_administrativo", "agenda_ajena", "consultorio_ajeno"])
async def test_atencion_rechaza_rol_agenda_y_consultorio_sin_fugas(sesiones, escenario, accion, caso):
    from app.infrastructure.db.models import BoxModel, ProfesionalModel
    identificador = await turno(sesiones, escenario, consultorio=2 if caso == "consultorio_ajeno" else 1)
    escenario.reloj.fijar(INICIO)
    if caso == "agenda_ajena":
        async with sesiones() as sesion:
            box = BoxModel(consultorio_id=1, nombre="Box adicional")
            sesion.add(box)
            await sesion.flush()
            profesional = ProfesionalModel(consultorio_id=1, box_id=box.id, nombre="Otro", apellido="Profesional")
            sesion.add(profesional)
            await sesion.flush()
            persistido = await sesion.get(TurnoModel, identificador)
            persistido.profesional_id = profesional.id
            persistido.box_id = box.id
            await sesion.commit()
    rol = caso.removeprefix("rol_") if caso.startswith("rol_") else "profesional"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers(rol), json={})
    assert respuesta.status_code == (403 if caso.startswith("rol_") else 404)
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("accion", ["atendido", "ausente"])
@pytest.mark.parametrize("estado", ["atendido", "ausente", "cancelado", "liberado"])
async def test_profesional_no_modifica_estados_finales(sesiones, escenario, accion, estado):
    identificador = await turno(sesiones, escenario, estado=estado)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers("profesional"), json={})
    assert respuesta.status_code == 403
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("accion", ["confirmar", "cancelar", "liberar", "atendido", "ausente"])
async def test_acciones_rechazan_campos_extra(sesiones, escenario, accion):
    identificador = await turno(sesiones, escenario, marcado=True)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers(), json={"consultorio_id": 2})
    assert respuesta.status_code == 422
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("accion", ["confirmar", "cancelar", "liberar", "atendido", "ausente"])
async def test_fallo_del_historial_revierte_cada_accion_sin_exito_http(sesiones, escenario, monkeypatch, accion):
    from app.infrastructure.db.historial import RepositorioHistorialSQL
    identificador = await turno(sesiones, escenario, marcado=True)
    escenario.reloj.fijar(INICIO)

    async def fallar_historial(self, hecho):
        raise RuntimeError("fallo controlado de historial")

    monkeypatch.setattr(RepositorioHistorialSQL, "agregar", fallar_historial)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers(), json={})
    assert respuesta.status_code == 500
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, identificador)
        assert persistido.estado.value == "pendiente"
        assert persistido.actualizado_en == AHORA
        assert persistido.confirmado_en is None
        assert persistido.cancelado_en is None
        assert persistido.liberado_en is None
        assert persistido.marcado_sin_confirmar_en == AHORA
    assert await hechos(sesiones, identificador) == []


@pytest.mark.parametrize("accion", ["confirmar", "cancelar", "liberar", "atendido", "ausente"])
async def test_accion_con_lectura_obsoleta_devuelve_409_y_no_crea_historial(sesiones, escenario, monkeypatch, accion):
    from app.infrastructure.db.repositorios import RepositorioTurnosSQL
    identificador = await turno(sesiones, escenario, marcado=True)
    escenario.reloj.fijar(INICIO)
    actualizar = RepositorioTurnosSQL.actualizar

    async def cambiar_antes_de_escribir(self, original, cambios):
        async with sesiones() as otra:
            await otra.execute(text("UPDATE turno SET ciclo_confirmacion=ciclo_confirmacion+1 WHERE id=:id"), {"id": original.id})
            await otra.commit()
        return await actualizar(self, original, cambios)

    monkeypatch.setattr(RepositorioTurnosSQL, "actualizar", cambiar_antes_de_escribir)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{identificador}/{accion}", headers=escenario.headers(), json={})
    assert respuesta.status_code == 409
    assert await hechos(sesiones, identificador) == []
