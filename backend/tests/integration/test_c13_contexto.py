"""Contexto de agenda del personal sin exponer identidades ajenas."""
import httpx
import pytest

from app.application.services.token_service import AuthTokenService
from app.domain.entities.auth import Principal, RolUsuario
from app.infrastructure.db.models import ProfesionalModel
from tests.integration.c07_support import INICIO, preparar_escenario
from tests.integration.test_c07_agenda import registrar_turno

pytestmark = pytest.mark.integration


async def test_profesional_recibe_solo_su_propia_agenda(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/api/v1/agenda/contexto", headers=escenario.headers("profesional"))
    assert respuesta.status_code == 200
    assert respuesta.json() == {"profesional_id": escenario.profesionales[1]}


async def test_administrador_con_y_sin_agenda(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/api/v1/agenda/contexto", headers=escenario.headers("administrador"))
        assert respuesta.json() == {"profesional_id": None}
        async with sesiones() as sesion:
            profesional = await sesion.get(ProfesionalModel, escenario.profesionales[1])
            profesional.usuario_id = escenario.usuarios[1, "administrador"]
            await sesion.commit()
        respuesta = await cliente.get("/api/v1/agenda/contexto", headers=escenario.headers("administrador"))
        assert respuesta.json() == {"profesional_id": escenario.profesionales[1]}


@pytest.mark.parametrize("rol", ["recepcion", "paciente", "administrativo"])
async def test_roles_no_autorizados_no_pueden_obtener_contexto(sesiones, url_base, rol):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/api/v1/agenda/contexto", headers=escenario.headers(rol))
    assert respuesta.status_code == 403


async def test_contexto_no_cruza_consultorios_ni_acepta_filtro_ajeno(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    token = AuthTokenService(escenario.reloj, "j" * 32).emitir_access_token(
        Principal(escenario.usuarios[2, "profesional"], 1, RolUsuario.PROFESIONAL)
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get("/api/v1/agenda/contexto", headers={"Authorization": f"Bearer {token}"},
                                      params={"usuario_id": escenario.usuarios[2, "profesional"]})
    assert respuesta.status_code == 200
    assert respuesta.json() == {"profesional_id": None}


async def test_recepcion_ve_acciones_vigentes_de_turno_pendiente(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    turno_id = await registrar_turno(sesiones, escenario)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("recepcion"))
    assert respuesta.status_code == 200
    assert set(respuesta.json()["acciones_permitidas"]) == {"confirmar", "cancelar", "reprogramar"}


async def test_profesional_ve_acciones_al_inicio_y_no_en_estado_final(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    turno_id = await registrar_turno(sesiones, escenario)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("profesional"))
        assert set(respuesta.json()["acciones_permitidas"]) == {"atendido", "ausente"}
        async with sesiones() as sesion:
            from app.infrastructure.db.models import TurnoModel
            turno = await sesion.get(TurnoModel, turno_id)
            turno.estado = "atendido"
            await sesion.commit()
        respuesta = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("profesional"))
        assert respuesta.json()["acciones_permitidas"] == []


async def test_agenda_y_lista_muestran_las_mismas_acciones_que_el_detalle(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    turno_id = await registrar_turno(sesiones, escenario)
    escenario.reloj.fijar(INICIO)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        headers = escenario.headers("profesional")
        detalle = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=headers)
        agenda = await cliente.get("/api/v1/agenda", headers=headers,
                                   params={"profesional_id": escenario.profesionales[1], "fecha": "2026-11-09"})
        lista = await cliente.get("/api/v1/turnos", headers=headers)
    assert set(detalle.json()["acciones_permitidas"]) == {"atendido", "ausente"}
    assert agenda.json()[0]["acciones_permitidas"] == detalle.json()["acciones_permitidas"]
    assert lista.json()[0]["acciones_permitidas"] == detalle.json()["acciones_permitidas"]


async def test_accion_leida_se_revalida_si_el_estado_cambio(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    turno_id = await registrar_turno(sesiones, escenario)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        headers = escenario.headers("recepcion")
        detalle = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=headers)
        assert "confirmar" in detalle.json()["acciones_permitidas"]
        async with sesiones() as sesion:
            from app.infrastructure.db.models import TurnoModel
            turno = await sesion.get(TurnoModel, turno_id)
            turno.estado = "cancelado"
            await sesion.commit()
        respuesta = await cliente.post(f"/api/v1/turnos/{turno_id}/confirmar", headers=headers)
        assert respuesta.status_code in (403, 409)


async def test_administrador_con_agenda_puede_ver_accion_de_respuesta_en_lista(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    await registrar_turno(sesiones, escenario)
    async with sesiones() as sesion:
        profesional = await sesion.get(ProfesionalModel, escenario.profesionales[1])
        profesional.usuario_id = escenario.usuarios[1, "administrador"]
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        headers = escenario.headers("administrador")
        creado = await cliente.post("/api/v1/sobreturnos", headers=headers,
                                    json=escenario.payload(autorizado=True, motivo="Urgencia"))
        assert creado.status_code == 201
        lista = await cliente.get("/api/v1/turnos", headers=headers)
    sobreturno = next(t for t in lista.json() if t["id"] == creado.json()["id"])
    assert "responder_sobreturno" in sobreturno["acciones_permitidas"]


async def test_profesional_inactivo_no_recibe_accion_de_respuesta(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    await registrar_turno(sesiones, escenario)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        creado = await cliente.post("/api/v1/sobreturnos", headers=escenario.headers(),
                                    json=escenario.payload(autorizado=True, motivo="Urgencia"))
        assert creado.status_code == 201
        async with sesiones() as sesion:
            profesional = await sesion.get(ProfesionalModel, escenario.profesionales[1])
            profesional.activo = False
            await sesion.commit()
        detalle = await cliente.get(f"/api/v1/turnos/{creado.json()['id']}", headers=escenario.headers("profesional"))
    assert detalle.status_code == 200
    assert "responder_sobreturno" not in detalle.json()["acciones_permitidas"]


async def test_profesional_inactivo_no_recibe_acciones_de_atencion(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    turno_id = await registrar_turno(sesiones, escenario)
    escenario.reloj.fijar(INICIO)
    async with sesiones() as sesion:
        profesional = await sesion.get(ProfesionalModel, escenario.profesionales[1])
        profesional.activo = False
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as cliente:
        detalle = await cliente.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("profesional"))
    assert detalle.status_code == 200
    assert detalle.json()["acciones_permitidas"] == []
