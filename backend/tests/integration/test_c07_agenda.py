"""Lecturas C-07: agenda propia, aislamiento y datos operativos mínimos."""
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db.models import TurnoHistorialModel, TurnoModel
from tests.integration.c07_support import AHORA, INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


@pytest.fixture
async def cliente(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        yield cliente


async def registrar_turno(sesiones, escenario, *, cid=1, inicio=INICIO, profesional_id=None,
                          paciente_id=None, estado="pendiente", sobreturno=False, historial=True):
    from app.infrastructure.db.models import ProfesionalModel
    async with sesiones() as sesion:
        profesional_id = profesional_id or escenario.profesionales[cid]
        profesional = await sesion.get(ProfesionalModel, profesional_id)
        turno = TurnoModel(
            consultorio_id=cid, paciente_id=paciente_id or escenario.pacientes[cid],
            profesional_id=profesional_id, box_id=profesional.box_id,
            prestacion_id=escenario.prestaciones[cid], inicio=inicio, fin=inicio + timedelta(minutes=30),
            estado=estado, es_sobreturno=sobreturno, origen="recepcion",
            creado_por_id=escenario.usuarios[cid, "recepcion"], creado_en=AHORA, actualizado_en=AHORA,
        )
        sesion.add(turno)
        await sesion.flush()
        if historial:
            sesion.add(TurnoHistorialModel(
                consultorio_id=cid, turno_id=turno.id, usuario_id=escenario.usuarios[cid, "recepcion"],
                accion="crear", estado_anterior=None, estado_nuevo=estado, ocurrido_en=AHORA,
            ))
        await sesion.commit()
        return turno.id


async def otro_profesional(sesiones, cid=1):
    from app.infrastructure.db.models import BoxModel, ProfesionalModel
    async with sesiones() as sesion:
        box = BoxModel(consultorio_id=cid, nombre="Box secundario")
        sesion.add(box)
        await sesion.flush()
        profesional = ProfesionalModel(consultorio_id=cid, box_id=box.id, nombre="Otro", apellido="Profesional")
        sesion.add(profesional)
        await sesion.commit()
        return profesional.id


async def test_recepcion_consulta_detalle_operativo_de_su_consultorio(cliente, escenario, sesiones):
    turno_id = await registrar_turno(sesiones, escenario)
    respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers())
    assert respuesta.status_code == 200
    assert respuesta.json()["id"] == turno_id
    assert respuesta.json()["paciente_nombre"] == "Ana"
    assert respuesta.json()["prestacion_nombre"] == "Consulta"


@pytest.mark.parametrize("rol,objetivo,codigo", [
    ("administrador", "propio", 200), ("profesional", "propio", 200),
    ("profesional", "colega", 404), ("recepcion", "extranjero", 404),
    ("administrador", "inexistente", 404), ("paciente", "propio", 403),
    ("administrativo", "propio", 403),
])
async def test_detalle_respeta_rol_agenda_y_consultorio(cliente, escenario, sesiones, rol, objetivo, codigo):
    if objetivo == "inexistente":
        turno_id = 99999
    else:
        profesional_id = await otro_profesional(sesiones) if objetivo == "colega" else None
        turno_id = await registrar_turno(sesiones, escenario,
            cid=2 if objetivo == "extranjero" else 1, profesional_id=profesional_id)
    respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers(rol))
    assert respuesta.status_code == codigo
    if codigo != 200:
        assert "Ana" not in respuesta.text
        assert "Consulta" not in respuesta.text


async def test_lista_profesional_solo_devuelve_su_agenda(cliente, escenario, sesiones):
    propio = await registrar_turno(sesiones, escenario)
    colega = await otro_profesional(sesiones)
    await registrar_turno(sesiones, escenario, profesional_id=colega)
    await registrar_turno(sesiones, escenario, cid=2)
    respuesta = await cliente.get("/api/v1/turnos", headers=escenario.headers("profesional"))
    assert respuesta.status_code == 200
    assert [turno["id"] for turno in respuesta.json()] == [propio]


@pytest.mark.parametrize("rol", ["recepcion", "administrador"])
async def test_lista_personal_incluye_colegas_sin_fugas_y_ordena_por_inicio(cliente, escenario, sesiones, rol):
    tardio = await registrar_turno(sesiones, escenario, inicio=INICIO + timedelta(hours=1))
    colega = await otro_profesional(sesiones)
    temprano = await registrar_turno(sesiones, escenario, profesional_id=colega)
    await registrar_turno(sesiones, escenario, cid=2)
    respuesta = await cliente.get("/api/v1/turnos", headers=escenario.headers(rol))
    assert respuesta.status_code == 200
    assert [turno["id"] for turno in respuesta.json()] == [temprano, tardio]


async def test_listado_vacio_y_rechazos_de_autenticacion(cliente, escenario):
    respuesta = await cliente.get("/api/v1/turnos", headers=escenario.headers("profesional"))
    assert respuesta.status_code == 200
    assert respuesta.json() == []
    assert (await cliente.get("/api/v1/turnos")).status_code == 401
    assert (await cliente.get("/api/v1/turnos", headers=escenario.headers("paciente"))).status_code == 403


async def test_historial_propio_muestra_actor_fecha_y_estados(cliente, escenario, sesiones):
    turno_id = await registrar_turno(sesiones, escenario)
    respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}/historial", headers=escenario.headers())
    assert respuesta.status_code == 200
    assert len(respuesta.json()) == 1
    hecho = respuesta.json()[0]
    assert hecho["usuario_id"] == escenario.usuarios[1, "recepcion"]
    assert hecho["accion"] == "crear"
    assert hecho["estado_anterior"] is None
    assert hecho["estado_nuevo"] == "pendiente"
    assert hecho["ocurrido_en"].startswith("2026-11-06T11:00")


@pytest.mark.parametrize("rol", ["administrador", "profesional"])
async def test_historial_vacio_y_lectura_de_varios_hechos(cliente, escenario, sesiones, rol):
    turno_id = await registrar_turno(sesiones, escenario, historial=False)
    ruta = f"/api/v1/turnos/{turno_id}/historial"
    respuesta = await cliente.get(ruta, headers=escenario.headers(rol))
    assert respuesta.status_code == 200
    assert respuesta.json() == []
    async with sesiones() as sesion:
        for accion, anterior, nuevo, diferencia in [
            ("crear", None, "pendiente", 0), ("confirmar", "pendiente", "confirmado", 1),
        ]:
            sesion.add(TurnoHistorialModel(consultorio_id=1, turno_id=turno_id,
                usuario_id=None, accion=accion, estado_anterior=anterior, estado_nuevo=nuevo,
                ocurrido_en=AHORA + timedelta(seconds=diferencia)))
        await sesion.commit()
    respuesta = await cliente.get(ruta, headers=escenario.headers(rol))
    assert [hecho["accion"] for hecho in respuesta.json()] == ["crear", "confirmar"]
    assert respuesta.json()[1]["usuario_id"] is None


@pytest.mark.parametrize("objetivo", ["colega", "extranjero", "inexistente"])
async def test_historial_ajeno_no_revela_existencia(cliente, escenario, sesiones, objetivo):
    turno_id = 99999
    if objetivo != "inexistente":
        profesional_id = await otro_profesional(sesiones) if objetivo == "colega" else None
        turno_id = await registrar_turno(sesiones, escenario,
            cid=2 if objetivo == "extranjero" else 1, profesional_id=profesional_id)
    respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}/historial", headers=escenario.headers("profesional"))
    assert respuesta.status_code == 404
    assert "crear" not in respuesta.text


async def test_agenda_usa_dia_local_y_ordena_identificando_sobreturnos(cliente, escenario, sesiones):
    from datetime import datetime
    from tests.integration.c07_support import ZONA
    temprano = await registrar_turno(sesiones, escenario, inicio=datetime(2026, 11, 9, 0, 5, tzinfo=ZONA))
    tarde = await registrar_turno(sesiones, escenario,
        inicio=datetime(2026, 11, 9, 23, 30, tzinfo=ZONA), sobreturno=True)
    await registrar_turno(sesiones, escenario, inicio=datetime(2026, 11, 8, 23, 30, tzinfo=ZONA))
    await registrar_turno(sesiones, escenario, inicio=datetime(2026, 11, 10, 0, 5, tzinfo=ZONA))
    respuesta = await cliente.get("/api/v1/agenda", headers=escenario.headers("profesional"),
        params={"profesional_id": escenario.profesionales[1], "fecha": "2026-11-09"})
    assert respuesta.status_code == 200
    assert [turno["id"] for turno in respuesta.json()] == [temprano, tarde]
    assert [turno["es_sobreturno"] for turno in respuesta.json()] == [False, True]
    assert all(turno["paciente_nombre"] == "Ana" for turno in respuesta.json())


@pytest.mark.parametrize("rol,objetivo,codigo", [
    ("recepcion", "propio", 200), ("administrador", "propio", 200),
    ("profesional", "colega", 403), ("profesional", "extranjero", 404),
    ("recepcion", "extranjero", 404), ("paciente", "propio", 403),
])
async def test_agenda_distingue_colega_de_otro_consultorio(cliente, escenario, sesiones, rol, objetivo, codigo):
    profesional_id = escenario.profesionales[2 if objetivo == "extranjero" else 1]
    if objetivo == "colega":
        profesional_id = await otro_profesional(sesiones)
    respuesta = await cliente.get("/api/v1/agenda", headers=escenario.headers(rol),
        params={"profesional_id": profesional_id, "fecha": "2026-11-09"})
    assert respuesta.status_code == codigo
    if codigo == 200:
        assert respuesta.json() == []


@pytest.mark.parametrize("parametros", [
    {"profesional_id": 1, "fecha": "fecha-invalida"},
    {"profesional_id": 0, "fecha": "2026-11-09"},
    {"profesional_id": 1, "fecha": "2026-11-09", "consultorio_id": 2},
    {"profesional_id": 1},
])
async def test_agenda_rechaza_filtros_invalidos_o_autoridad_de_consultorio(cliente, escenario, parametros):
    respuesta = await cliente.get("/api/v1/agenda", headers=escenario.headers(), params=parametros)
    assert respuesta.status_code == 422


async def test_personal_lee_pasados_y_futuros_de_ficha_sin_cuenta(cliente, escenario, sesiones):
    futuro = await registrar_turno(sesiones, escenario)
    pasado = await registrar_turno(sesiones, escenario, inicio=INICIO - timedelta(days=30), estado="atendido")
    respuesta = await cliente.get(f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos", headers=escenario.headers())
    assert respuesta.status_code == 200
    assert [turno["id"] for turno in respuesta.json()] == [pasado, futuro]
    assert [turno["estado"] for turno in respuesta.json()] == ["atendido", "pendiente"]


async def test_profesional_ve_solo_sus_turnos_de_una_ficha_compartida(cliente, escenario, sesiones):
    propio = await registrar_turno(sesiones, escenario)
    colega = await otro_profesional(sesiones)
    await registrar_turno(sesiones, escenario, profesional_id=colega)
    respuesta = await cliente.get(f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos",
        headers=escenario.headers("profesional"))
    assert respuesta.status_code == 200
    assert [turno["id"] for turno in respuesta.json()] == [propio]


@pytest.mark.parametrize("rol,objetivo,codigo", [
    ("profesional", "sin_agenda", 404), ("profesional", "extranjero", 404),
    ("recepcion", "extranjero", 404), ("administrador", "inexistente", 404),
    ("administrador", "vacio", 200), ("paciente", "vacio", 403),
])
async def test_turnos_de_ficha_respeta_pertenencia_y_recurso_ausente(cliente, escenario, rol, objetivo, codigo):
    paciente_id = 99999 if objetivo == "inexistente" else escenario.pacientes[2 if objetivo == "extranjero" else 1]
    respuesta = await cliente.get(f"/api/v1/pacientes/{paciente_id}/turnos", headers=escenario.headers(rol))
    assert respuesta.status_code == codigo
    if codigo == 200:
        assert respuesta.json() == []


@pytest.mark.parametrize("global_", [False, True])
async def test_bloqueos_c06_informan_afectados_sin_guardar_y_admiten_hueco_libre(cliente, escenario, sesiones, global_):
    from app.infrastructure.db.models import BloqueoAgendaModel
    propio = await registrar_turno(sesiones, escenario)
    colega = await otro_profesional(sesiones)
    otro = await registrar_turno(sesiones, escenario, profesional_id=colega)
    await registrar_turno(sesiones, escenario, cid=2)
    async def snapshot():
        async with sesiones() as sesion:
            return (await sesion.execute(select(TurnoModel.id, TurnoModel.inicio, TurnoModel.fin,
                TurnoModel.estado, TurnoModel.ciclo_confirmacion, TurnoModel.marcado_sin_confirmar_en).order_by(TurnoModel.id))).all()
    antes = await snapshot()
    ruta = "/api/v1/bloqueos" if global_ else f"/api/v1/profesionales/{escenario.profesionales[1]}/bloqueos"
    respuesta = await cliente.post(ruta, headers=escenario.headers("administrador"), json={
        "tipo": "ausencia", "inicio": "2026-11-09T09:45:00", "fin": "2026-11-09T10:45:00",
    })
    assert respuesta.status_code == 409
    assert set(respuesta.json()["detail"]["turnos_afectados"]) == ({propio, otro} if global_ else {propio})
    async with sesiones() as sesion:
        assert list((await sesion.scalars(select(BloqueoAgendaModel))).all()) == []
    assert await snapshot() == antes
    libre = await cliente.post(ruta, headers=escenario.headers("administrador"), json={
        "tipo": "ausencia", "inicio": "2026-11-09T14:00:00", "fin": "2026-11-09T15:00:00",
    })
    assert libre.status_code == 201
    async with sesiones() as sesion:
        assert len((await sesion.scalars(select(BloqueoAgendaModel))).all()) == 1
    assert await snapshot() == antes


async def test_lecturas_y_rechazos_no_exponen_datos_privados_en_respuestas_ni_logs(cliente, escenario, sesiones, caplog):
    import logging
    from app.infrastructure.db.models import PacienteModel
    turno_id = await registrar_turno(sesiones, escenario)
    colega = await otro_profesional(sesiones)
    turno_colega = await registrar_turno(sesiones, escenario, profesional_id=colega)
    secretos = ["30999888", "+54-privado-telefono", "contacto-privado@example.test",
                "obra-social-privada", "nota-clinica-privada", "detalle-historia-privado"]
    async with sesiones() as sesion:
        paciente = await sesion.get(PacienteModel, escenario.pacientes[1])
        paciente.dni, paciente.telefono, paciente.email, paciente.obra_social, paciente.notas = secretos[:5]
        turno = await sesion.get(TurnoModel, turno_id)
        turno.notas = secretos[4]
        hecho = await sesion.scalar(select(TurnoHistorialModel).where(TurnoHistorialModel.turno_id == turno_id))
        hecho.detalle = {"dni": secretos[0], "notas": secretos[5]}
        await sesion.commit()
    rutas = ["/api/v1/turnos", f"/api/v1/turnos/{turno_id}",
        f"/api/v1/turnos/{turno_id}/historial",
        f"/api/v1/agenda?profesional_id={escenario.profesionales[1]}&fecha=2026-11-09",
        f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos"]
    logger = logging.getLogger("tpi")
    logger.addHandler(caplog.handler)
    try:
        for ruta in rutas:
            respuesta = await cliente.get(ruta, headers=escenario.headers())
            assert respuesta.status_code == 200
            assert all(secreto not in respuesta.text for secreto in secretos)
            filas = respuesta.json() if isinstance(respuesta.json(), list) else [respuesta.json()]
            for fila in filas:
                assert not {"dni", "telefono", "email", "obra_social", "notas", "usuario", "cuenta", "detalle"} & fila.keys()
        for ruta, codigo in [
            (f"/api/v1/turnos/{turno_colega}", 404),
            (f"/api/v1/turnos/{turno_colega}/historial", 404),
            (f"/api/v1/agenda?profesional_id={colega}&fecha=2026-11-09", 403),
        ]:
            respuesta = await cliente.get(ruta, headers=escenario.headers("profesional"))
            assert respuesta.status_code == codigo
            assert all(secreto not in respuesta.text for secreto in secretos)
        invalida = await cliente.get("/api/v1/agenda", headers=escenario.headers(), params={
            "profesional_id": escenario.profesionales[1], "fecha": "2026-11-09", "dni": secretos[0],
        })
        assert invalida.status_code == 422
        assert secretos[0] not in invalida.text
    finally:
        logger.removeHandler(caplog.handler)
    assert any(registro.name == "tpi.acceso" for registro in caplog.records)
    assert all(secreto not in str([registro.__dict__ for registro in caplog.records]) for secreto in secretos)


async def test_historial_solo_lectura_no_ofrece_rutas_de_escritura_o_borrado(cliente, escenario, sesiones):
    turno_id = await registrar_turno(sesiones, escenario)
    ruta = f"/api/v1/turnos/{turno_id}/historial"
    antes = (await cliente.get(ruta, headers=escenario.headers())).json()
    for metodo in ("POST", "PATCH", "PUT", "DELETE"):
        respuesta = await cliente.request(metodo, ruta, headers=escenario.headers("administrador"), json={"accion": "borrar"})
        assert respuesta.status_code == 405
    despues = (await cliente.get(ruta, headers=escenario.headers())).json()
    assert despues == antes
    esquema = (await cliente.get("/openapi.json")).json()
    rutas_historial = {ruta: acciones for ruta, acciones in esquema["paths"].items() if "historial" in ruta}
    assert set(rutas_historial) == {"/api/v1/turnos/{turno_id}/historial"}
    assert set(next(iter(rutas_historial.values()))) == {"get"}


async def test_prestacion_desactivada_conserva_lecturas_de_turnos_y_rechaza_altas(cliente, escenario):
    creado = await cliente.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert creado.status_code == 201
    turno_id = creado.json()["id"]
    desactivada = await cliente.patch(f"/api/v1/prestaciones/{escenario.prestaciones[1]}",
        headers=escenario.headers("administrador"), json={"activa": False})
    assert desactivada.status_code == 200
    rutas = [f"/api/v1/turnos/{turno_id}", "/api/v1/turnos",
        f"/api/v1/agenda?profesional_id={escenario.profesionales[1]}&fecha=2026-11-09",
        f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos"]
    for ruta in rutas:
        respuesta = await cliente.get(ruta, headers=escenario.headers())
        assert respuesta.status_code == 200
        turno = respuesta.json()[0] if isinstance(respuesta.json(), list) else respuesta.json()
        assert turno["id"] == turno_id
        assert turno["prestacion_nombre"] == "Consulta"
        assert turno["inicio"] == creado.json()["inicio"]
        assert turno["fin"] == creado.json()["fin"]
    historial = await cliente.get(f"/api/v1/turnos/{turno_id}/historial", headers=escenario.headers())
    assert historial.status_code == 200
    assert [hecho["accion"] for hecho in historial.json()] == ["crear"]
    nueva = await cliente.post("/api/v1/turnos", headers=escenario.headers(),
        json=escenario.payload(inicio=INICIO + timedelta(hours=1)))
    assert nueva.status_code == 404


@pytest.mark.parametrize("rol", ["recepcion", "administrador", "profesional"])
async def test_profesional_inactivo_conserva_agenda_historica_sin_habilitar_altas(cliente, escenario, rol):
    creado = await cliente.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert creado.status_code == 201
    turno_id = creado.json()["id"]
    desactivado = await cliente.patch(f"/api/v1/profesionales/{escenario.profesionales[1]}",
        headers=escenario.headers("administrador"), json={"activo": False})
    assert desactivado.status_code == 200
    rutas = [f"/api/v1/agenda?profesional_id={escenario.profesionales[1]}&fecha=2026-11-09",
        "/api/v1/turnos", f"/api/v1/turnos/{turno_id}",
        f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos"]
    for ruta in rutas:
        respuesta = await cliente.get(ruta, headers=escenario.headers(rol))
        assert respuesta.status_code == 200
        turno = respuesta.json()[0] if isinstance(respuesta.json(), list) else respuesta.json()
        assert turno["id"] == turno_id
        assert turno["prestacion_nombre"] == "Consulta"
        assert turno["fin"] == creado.json()["fin"]
    historial = await cliente.get(f"/api/v1/turnos/{turno_id}/historial", headers=escenario.headers(rol))
    assert historial.status_code == 200
    assert [hecho["accion"] for hecho in historial.json()] == ["crear"]
    nueva = await cliente.post("/api/v1/turnos", headers=escenario.headers(),
        json=escenario.payload(inicio=INICIO + timedelta(hours=1)))
    assert nueva.status_code == 404


async def test_lecturas_de_inactivos_preservan_rol_agenda_y_consultorio(cliente, escenario, sesiones):
    from app.infrastructure.db.models import PrestacionModel, ProfesionalModel
    propio = await registrar_turno(sesiones, escenario)
    colega = await otro_profesional(sesiones)
    turno_colega = await registrar_turno(sesiones, escenario, profesional_id=colega)
    extranjero = await registrar_turno(sesiones, escenario, cid=2)
    async with sesiones() as sesion:
        for profesional_id in (colega, escenario.profesionales[2]):
            profesional = await sesion.get(ProfesionalModel, profesional_id)
            profesional.activo = False
        for prestacion_id in escenario.prestaciones.values():
            prestacion = await sesion.get(PrestacionModel, prestacion_id)
            prestacion.activa = False
        await sesion.commit()
    lecturas = [
        (f"/api/v1/turnos/{turno_colega}", 404),
        (f"/api/v1/turnos/{turno_colega}/historial", 404),
        (f"/api/v1/agenda?profesional_id={colega}&fecha=2026-11-09", 403),
        (f"/api/v1/turnos/{extranjero}", 404),
        (f"/api/v1/agenda?profesional_id={escenario.profesionales[2]}&fecha=2026-11-09", 404),
        (f"/api/v1/pacientes/{escenario.pacientes[2]}/turnos", 404),
    ]
    for ruta, codigo in lecturas:
        assert (await cliente.get(ruta, headers=escenario.headers("profesional"))).status_code == codigo
    for ruta in ("/api/v1/turnos", f"/api/v1/pacientes/{escenario.pacientes[1]}/turnos"):
        respuesta = await cliente.get(ruta, headers=escenario.headers("profesional"))
        assert respuesta.status_code == 200
        assert [turno["id"] for turno in respuesta.json()] == [propio]
    assert (await cliente.get(f"/api/v1/turnos/{turno_colega}", headers=escenario.headers("administrador"))).status_code == 200
    for rol in ("paciente", "administrativo"):
        assert (await cliente.get(f"/api/v1/turnos/{propio}", headers=escenario.headers(rol))).status_code == 403
