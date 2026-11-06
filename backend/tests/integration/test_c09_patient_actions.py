"""C09: lecturas y acciones sobre la ficha vigente del paciente."""
from datetime import timedelta

import httpx
import pytest

from app.infrastructure.db.models import ConsultorioModel, PacienteModel, TurnoModel, UsuarioModel
from tests.integration.c07_support import AHORA, INICIO, preparar_escenario
from tests.integration.test_c07_agenda import registrar_turno
from tests.integration.test_c07_lifecycle import hechos

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.usuario_id = escenario.usuarios[1, "paciente"]
        usuario = await sesion.get(UsuarioModel, escenario.usuarios[1, "paciente"])
        usuario.email_verificado = True
        usuario.email_verificado_en = AHORA
        await sesion.commit()
    return escenario


@pytest.fixture
async def cliente(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        yield cliente


async def test_lista_propia_incluye_pasados_y_futuros_sin_otro_consultorio(cliente, escenario, sesiones):
    pasado = await registrar_turno(sesiones, escenario, inicio=INICIO-timedelta(days=10), estado="atendido")
    futuro = await registrar_turno(sesiones, escenario)
    await registrar_turno(sesiones, escenario, cid=2)
    async with sesiones() as sesion:
        otro = PacienteModel(consultorio_id=1, nombre="Otro", apellido="Paciente",
            dni="98765432", creado_en=AHORA, actualizado_en=AHORA)
        sesion.add(otro)
        await sesion.commit()
        otro_id = otro.id
    await registrar_turno(sesiones, escenario, paciente_id=otro_id, inicio=INICIO+timedelta(hours=1))
    respuesta = await cliente.get("/api/v1/turnos", headers=escenario.headers("paciente"))
    assert respuesta.status_code == 200
    assert [fila["id"] for fila in respuesta.json()] == [pasado, futuro]
    assert respuesta.json()[1]["prestacion_nombre"] == "Consulta"
    assert respuesta.json()[1]["profesional_id"] == escenario.profesionales[1]


async def test_lista_sin_ficha_es_vacia_y_no_muestra_la_ficha_previa(cliente, escenario, sesiones):
    await registrar_turno(sesiones, escenario)
    headers = escenario.headers("paciente")
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.usuario_id = None
        await sesion.commit()
    respuesta = await cliente.get("/api/v1/turnos", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.json() == []


async def test_detalle_historial_propios_y_ajenos_resuelven_vinculo_actual(cliente, escenario, sesiones):
    propio = await registrar_turno(sesiones, escenario)
    ajeno = await registrar_turno(sesiones, escenario, cid=2)
    for sufijo in ("", "/historial"):
        assert (await cliente.get(f"/api/v1/turnos/{propio}{sufijo}", headers=escenario.headers("paciente"))).status_code == 200
        respuesta = await cliente.get(f"/api/v1/turnos/{ajeno}{sufijo}", headers=escenario.headers("paciente"))
        assert respuesta.status_code == 404
        assert "Consulta" not in respuesta.text


@pytest.mark.parametrize("estado,horas,minutos,acciones", [
    ("pendiente", 24, 0, ["confirmar", "cancelar", "reprogramar"]),
    ("confirmado", 24, 0, ["cancelar", "reprogramar"]),
    ("pendiente", 23, 59, ["confirmar"]),
    ("confirmado", 23, 59, []),
    ("atendido", 72, 0, []), ("ausente", 72, 0, []),
    ("liberado", 72, 0, []), ("cancelado", 72, 0, []),
])
async def test_acciones_permitidas_concuerdan_con_estado_y_reloj(cliente, escenario, sesiones, estado, horas, minutos, acciones):
    tid = await registrar_turno(sesiones, escenario, estado=estado)
    escenario.reloj.fijar(INICIO-timedelta(hours=horas, minutes=minutos))
    headers = escenario.headers("paciente")
    respuesta = await cliente.get(f"/api/v1/turnos/{tid}", headers=headers)
    assert respuesta.status_code == 200
    assert respuesta.json()["acciones_permitidas"] == acciones
    listado = await cliente.get("/api/v1/turnos", headers=headers)
    assert listado.json()[0]["acciones_permitidas"] == acciones
    personal = await cliente.get(f"/api/v1/turnos/{tid}", headers=escenario.headers())
    assert personal.status_code == 200
    esperadas_personal = {
        "pendiente": ["confirmar", "cancelar", "reprogramar"],
        "confirmado": ["cancelar", "reprogramar"],
        "atendido": [], "ausente": ["corregir_ausente"],
        "liberado": [], "cancelado": [],
    }
    assert personal.json()["acciones_permitidas"] == esperadas_personal[estado]
    assert personal.json()["marcado_sin_confirmar_en"] is None


async def test_titular_confirma_pendiente_y_guarda_historial(cliente, escenario, sesiones):
    tid = await registrar_turno(sesiones, escenario)
    respuesta = await cliente.post(f"/api/v1/turnos/{tid}/confirmar", json={}, headers=escenario.headers("paciente"))
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "confirmado"
    historia = await hechos(sesiones, tid)
    assert [h.accion for h in historia] == ["crear", "confirmar"]
    assert historia[-1].usuario_id == escenario.usuarios[1, "paciente"]
    assert historia[-1].ocurrido_en == AHORA


async def test_confirmacion_propia_rechaza_ajeno_y_estado_liberado(cliente, escenario, sesiones):
    propio = await registrar_turno(sesiones, escenario, estado="liberado")
    ajeno = await registrar_turno(sesiones, escenario, cid=2)
    assert (await cliente.post(f"/api/v1/turnos/{propio}/confirmar", json={}, headers=escenario.headers("paciente"))).status_code == 403
    assert (await cliente.post(f"/api/v1/turnos/{ajeno}/confirmar", json={}, headers=escenario.headers("paciente"))).status_code == 404
    assert [h.accion for h in await hechos(sesiones, propio)] == ["crear"]


@pytest.mark.parametrize("minutos,codigo", [(24*60, 200), (24*60-1, 403)])
async def test_cancelar_propietario_respeta_ventana_exacta_y_telefono(cliente, escenario, sesiones, minutos, codigo):
    tid = await registrar_turno(sesiones, escenario, estado="confirmado")
    async with sesiones() as sesion:
        config = await sesion.get(ConsultorioModel, 1)
        config.telefono = "011-5555-0101"
        await sesion.commit()
    escenario.reloj.fijar(INICIO-timedelta(minutes=minutos))
    respuesta = await cliente.post(f"/api/v1/turnos/{tid}/cancelar", json={}, headers=escenario.headers("paciente"))
    assert respuesta.status_code == codigo
    if codigo == 200:
        assert respuesta.json()["estado"] == "cancelado"
        reservado = await cliente.post("/api/v1/turnos", json=escenario.payload(), headers=escenario.headers())
        assert reservado.status_code == 201
        assert [h.accion for h in await hechos(sesiones, tid)] == ["crear", "cancelar"]
    else:
        assert "011-5555-0101" in respuesta.text
        assert [h.accion for h in await hechos(sesiones, tid)] == ["crear"]
        async with sesiones() as sesion:
            assert (await sesion.get(TurnoModel, tid)).estado.value == "confirmado"


async def test_cancelar_ajeno_no_revela_telefono_y_final_no_modifica(cliente, escenario, sesiones):
    ajeno = await registrar_turno(sesiones, escenario, cid=2)
    final = await registrar_turno(sesiones, escenario, estado="atendido")
    escenario.reloj.fijar(INICIO-timedelta(hours=1))
    respuesta = await cliente.post(f"/api/v1/turnos/{ajeno}/cancelar", json={}, headers=escenario.headers("paciente"))
    assert respuesta.status_code == 404
    assert "telefono" not in respuesta.text
    assert (await cliente.post(f"/api/v1/turnos/{final}/cancelar", json={}, headers=escenario.headers("paciente"))).status_code == 403
    assert [h.accion for h in await hechos(sesiones, final)] == ["crear"]


async def test_jwt_previo_a_desvincular_no_da_lecturas_ni_acciones(cliente, escenario, sesiones):
    tid = await registrar_turno(sesiones, escenario)
    headers = escenario.headers("paciente")
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.usuario_id = None
        await sesion.commit()
    respuesta = await cliente.get("/api/v1/turnos", headers=headers)
    assert respuesta.status_code == 200 and respuesta.json() == []
    for sufijo in ("", "/historial"):
        assert (await cliente.get(f"/api/v1/turnos/{tid}{sufijo}", headers=headers)).status_code == 404
    for accion in ("confirmar", "cancelar"):
        assert (await cliente.post(f"/api/v1/turnos/{tid}/{accion}", json={}, headers=headers)).status_code == 404
    assert [h.accion for h in await hechos(sesiones, tid)] == ["crear"]


@pytest.mark.parametrize("accion", ["confirmar", "cancelar"])
@pytest.mark.parametrize("fallo", ["historial", "commit"])
async def test_accion_propia_revierte_ante_fallo_transaccional(cliente, escenario, sesiones, monkeypatch, accion, fallo):
    from app.infrastructure.db.historial import RepositorioHistorialSQL
    from sqlalchemy.ext.asyncio import AsyncSession

    tid = await registrar_turno(sesiones, escenario)

    async def fallar(*args, **kwargs):
        raise RuntimeError("fallo controlado")

    monkeypatch.setattr(RepositorioHistorialSQL if fallo == "historial" else AsyncSession,
        "agregar" if fallo == "historial" else "commit", fallar)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as cliente:
        respuesta = await cliente.post(f"/api/v1/turnos/{tid}/{accion}", json={}, headers=escenario.headers("paciente"))
    assert respuesta.status_code == 500
    async with sesiones() as sesion:
        persistido = await sesion.get(TurnoModel, tid)
        assert persistido.estado.value == "pendiente"
        assert persistido.actualizado_en == AHORA
        assert persistido.confirmado_en is None
        assert persistido.cancelado_en is None
    assert [h.accion for h in await hechos(sesiones, tid)] == ["crear"]


async def test_ventana_configurada_se_comparte_con_lectura_y_no_filtra_contacto_en_logs(cliente, escenario, sesiones, caplog):
    tid = await registrar_turno(sesiones, escenario)
    async with sesiones() as sesion:
        config = await sesion.get(ConsultorioModel, 1)
        config.horas_limite_paciente = 36
        config.telefono = "011-5555-9900"
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.telefono = "contacto-privado"
        ficha.email = "privado@example.test"
        await sesion.commit()
    escenario.reloj.fijar(INICIO-timedelta(hours=35))
    headers = escenario.headers("paciente")
    detalle = await cliente.get(f"/api/v1/turnos/{tid}", headers=headers)
    assert detalle.json()["acciones_permitidas"] == ["confirmar"]
    cancelacion = await cliente.post(f"/api/v1/turnos/{tid}/cancelar", json={}, headers=headers)
    assert cancelacion.status_code == 403
    assert "011-5555-9900" in cancelacion.text
    assert "011-5555-9900" not in caplog.text
    assert "contacto-privado" not in caplog.text
    assert "privado@example.test" not in detalle.text + cancelacion.text + caplog.text
