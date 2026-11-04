"""RN-63: recuperación manual mediante registro/verificación y APIs C-08."""
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from sqlalchemy import update

from app.api.v1.routers.cuentas import get_enviador_correo
from app.infrastructure.db.models import PacienteModel
from tests.integration.c07_support import preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def recuperacion(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    mensajes = []

    class Correo:
        async def enviar(self, destinatario, asunto, cuerpo):
            mensajes.append((destinatario, cuerpo))

    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app),
                                base_url="http://test") as cliente:
        yield escenario, cliente, mensajes


async def registrar_y_verificar(cliente, mensajes, nombre, dni):
    email = f"{nombre}@example.test"
    aviso = await cliente.get("/api/v1/publico/aviso-privacidad")
    assert aviso.status_code == 200
    registro = await cliente.post("/api/v1/auth/registro", json={
        "nombre": nombre, "apellido": "Recuperación", "dni": dni,
        "telefono": "1144445555", "email": email, "nombre_usuario": nombre,
        "password": "password-sintetica", "acepta_aviso_privacidad": True,
        "aviso_privacidad_version": aviso.json()["version"],
    })
    assert registro.status_code == 201
    correo = next(cuerpo for destinatario, cuerpo in reversed(mensajes) if destinatario == email)
    token = parse_qs(urlsplit(correo.splitlines()[-1]).fragment)["token"][0]
    verificacion = await cliente.post("/api/v1/auth/verificar-email", json={"token": token})
    assert verificacion.status_code == 200
    ingreso = await cliente.post("/api/v1/auth/login", json={
        "identificador": nombre, "password": "password-sintetica",
    })
    assert ingreso.status_code == 200
    return {"Authorization": f'Bearer {ingreso.json()["access_token"]}'}


async def solicitudes(cliente, escenario):
    respuesta = await cliente.get("/api/v1/solicitudes-vinculacion", headers=escenario.headers())
    assert respuesta.status_code == 200
    return {item["email"]: item for item in respuesta.json()["items"]}


async def detalle(cliente, escenario, pid):
    respuesta = await cliente.get(f"/api/v1/pacientes/{pid}", headers=escenario.headers())
    assert respuesta.status_code == 200
    return respuesta.json()


async def vincular(cliente, escenario, sid, pid):
    respuesta = await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid}/vincular",
                                  json={"paciente_id": pid}, headers=escenario.headers())
    assert respuesta.status_code == 200


async def desvincular(cliente, escenario, pid):
    respuesta = await cliente.post(f"/api/v1/pacientes/{pid}/desvincular",
                                  json={"motivo": "Identidad verificada por personal"},
                                  headers=escenario.headers())
    assert respuesta.status_code == 200


async def crear_ficha(cliente, escenario, dni):
    respuesta = await cliente.post("/api/v1/pacientes", headers=escenario.headers(), json={
        "nombre": "Ficha", "apellido": "Correcta", "dni": dni,
        "telefono": "1155556666", "email": "ficha@example.test",
    })
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


async def historial(cliente, escenario, pid):
    respuesta = await cliente.get(f"/api/v1/pacientes/{pid}/turnos", headers=escenario.headers())
    assert respuesta.status_code == 200
    return respuesta.json()


async def crear_turno(cliente, escenario, pid):
    respuesta = await cliente.post("/api/v1/turnos", headers=escenario.headers(),
                                  json=escenario.payload(paciente_id=pid))
    assert respuesta.status_code == 201
    return respuesta.json()["id"]


async def test_vinculo_equivocado_se_recupera_sin_mover_fichas_ni_turnos(recuperacion):
    escenario, cliente, mensajes = recuperacion
    f1 = escenario.pacientes[1]
    f2 = await crear_ficha(cliente, escenario, "87654321")
    headers_previos = await registrar_y_verificar(cliente, mensajes, "equivocada", "12345671")
    sid = (await solicitudes(cliente, escenario))["equivocada@example.test"]["id"]
    await vincular(cliente, escenario, sid, f1)
    turno = await crear_turno(cliente, escenario, f1)
    antes = await detalle(cliente, escenario, f1)
    assert antes["cuenta"]["nombre_usuario"] == "equivocada"
    assert (await solicitudes(cliente, escenario))["equivocada@example.test"]["ficha_vinculada"]["id"] == f1

    cantidad_correos = len(mensajes)
    await desvincular(cliente, escenario, f1)
    assert len(mensajes) == cantidad_correos
    assert (await cliente.get(f"/api/v1/pacientes/{f1}", headers=headers_previos)).status_code == 404
    rechazada = (await solicitudes(cliente, escenario))["equivocada@example.test"]
    assert rechazada["estado"] == "rechazada" and "ficha_vinculada" not in rechazada
    await vincular(cliente, escenario, sid, f2)

    despues = await detalle(cliente, escenario, f1)
    assert despues == {**antes, "cuenta": None}
    assert (await detalle(cliente, escenario, f2))["cuenta"]["nombre_usuario"] == "equivocada"
    assert (await cliente.get(f"/api/v1/pacientes/{f2}", headers=headers_previos)).status_code == 200
    assert (await cliente.get(f"/api/v1/pacientes/{f1}", headers=headers_previos)).status_code == 404
    assert [t["id"] for t in await historial(cliente, escenario, f1)] == [turno]
    assert await historial(cliente, escenario, f2) == []


@pytest.mark.parametrize("titular_correcto", ["actual", "solicitante"])
async def test_ficha_ocupada_se_resuelve_segun_identidad_verificada(recuperacion, titular_correcto):
    escenario, cliente, mensajes = recuperacion
    headers_b = await registrar_y_verificar(cliente, mensajes, "actual", "87654321")
    propias = await cliente.get("/api/v1/pacientes", headers=headers_b)
    f = propias.json()["items"][0]["id"]
    turno = await crear_turno(cliente, escenario, f)
    headers_a = await registrar_y_verificar(cliente, mensajes, "solicitante", "87654321")
    sid_a = (await solicitudes(cliente, escenario))["solicitante@example.test"]["id"]
    antes = await detalle(cliente, escenario, f)
    conflicto = await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid_a}/vincular",
                                  json={"paciente_id": f}, headers=escenario.headers())
    assert conflicto.status_code == 409
    assert (await solicitudes(cliente, escenario))["solicitante@example.test"]["estado"] == "pendiente"

    if titular_correcto == "actual":
        rechazo = await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid_a}/rechazar",
                                    json={"motivo": "La ficha corresponde a la cuenta actual"},
                                    headers=escenario.headers())
        assert rechazo.status_code == 200
        assert (await detalle(cliente, escenario, f)) == antes
        assert (await solicitudes(cliente, escenario))["solicitante@example.test"]["estado"] == "rechazada"
        assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_a)).status_code == 404
        assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_b)).status_code == 200
    else:
        await desvincular(cliente, escenario, f)
        await vincular(cliente, escenario, sid_a, f)
        actual = await detalle(cliente, escenario, f)
        assert {k: v for k, v in actual.items() if k != "cuenta"} == {
            k: v for k, v in antes.items() if k != "cuenta"
        }
        assert actual["cuenta"]["nombre_usuario"] == "solicitante"
        resueltas = await solicitudes(cliente, escenario)
        assert resueltas["actual@example.test"]["estado"] == "rechazada"
        assert "ficha_vinculada" not in resueltas["actual@example.test"]
        assert resueltas["solicitante@example.test"]["ficha_vinculada"]["id"] == f
        assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_b)).status_code == 404
        assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_a)).status_code == 200
    assert [t["id"] for t in await historial(cliente, escenario, f)] == [turno]


async def test_ficha_inactiva_se_reactiva_y_vincula_sin_perder_turnos(recuperacion, sesiones):
    escenario, cliente, mensajes = recuperacion
    f = escenario.pacientes[1]
    turno = await crear_turno(cliente, escenario, f)
    # SU-47: la carga inactiva viene de fuera de la aplicación, sin ruta de baja.
    async with sesiones() as sesion:
        await sesion.execute(update(PacienteModel).where(PacienteModel.id == f).values(activo=False))
        await sesion.commit()
    antes = await detalle(cliente, escenario, f)
    headers = await registrar_y_verificar(cliente, mensajes, "inactiva", "12345671")
    sid = (await solicitudes(cliente, escenario))["inactiva@example.test"]["id"]
    conflicto = await cliente.post(f"/api/v1/solicitudes-vinculacion/{sid}/vincular",
                                  json={"paciente_id": f}, headers=escenario.headers())
    assert conflicto.status_code == 409
    reactivar = await cliente.post(f"/api/v1/pacientes/{f}/reactivar", headers=escenario.headers())
    assert reactivar.status_code == 200
    await vincular(cliente, escenario, sid, f)
    despues = await detalle(cliente, escenario, f)
    assert despues["activo"] is True
    assert despues["cuenta"]["nombre_usuario"] == "inactiva"
    assert {k: v for k, v in despues.items() if k not in {"activo", "cuenta"}} == {
        k: v for k, v in antes.items() if k not in {"activo", "cuenta"}
    }
    assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers)).status_code == 200
    assert [t["id"] for t in await historial(cliente, escenario, f)] == [turno]


async def test_tercero_con_dni_nuevo_se_desvincula_y_cancela_antes_de_corregir(recuperacion):
    escenario, cliente, mensajes = recuperacion
    headers_tercero = await registrar_y_verificar(cliente, mensajes, "tercero", "87654321")
    propias = await cliente.get("/api/v1/pacientes", headers=headers_tercero)
    f = propias.json()["items"][0]["id"]
    assert "tercero@example.test" not in await solicitudes(cliente, escenario)
    turno = await crear_turno(cliente, escenario, f)
    headers_correctos = await registrar_y_verificar(cliente, mensajes, "correcta", "87654321")
    sid = (await solicitudes(cliente, escenario))["correcta@example.test"]["id"]
    assert (await detalle(cliente, escenario, f))["cuenta"]["nombre_usuario"] == "tercero"

    await desvincular(cliente, escenario, f)
    sin_titular = await detalle(cliente, escenario, f)
    assert sin_titular["cuenta"] is None
    assert sin_titular["email"] == "tercero@example.test"
    assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_tercero)).status_code == 404
    # Flujo 1: cancelar manualmente antes de cambiar el destinatario de la ficha.
    antes_cancelar = await historial(cliente, escenario, f)
    assert [(t["id"], t["estado"]) for t in antes_cancelar] == [(turno, "pendiente")]
    cancelacion = await cliente.post(f"/api/v1/turnos/{turno}/cancelar",
                                     json={"motivo": "Reserva de cuenta equivocada"},
                                     headers=escenario.headers())
    assert cancelacion.status_code == 200 and cancelacion.json()["estado"] == "cancelado"
    assert (await detalle(cliente, escenario, f))["email"] == "tercero@example.test"
    despues_cancelar = await historial(cliente, escenario, f)

    correccion = await cliente.patch(f"/api/v1/pacientes/{f}", headers=escenario.headers(), json={
        "nombre": "Persona", "apellido": "Correcta", "telefono": "1166667777",
        "email": "correcta@example.test",
    })
    assert correccion.status_code == 200
    await vincular(cliente, escenario, sid, f)
    final = await detalle(cliente, escenario, f)
    assert final["dni"] == "87654321"
    assert (final["nombre"], final["apellido"], final["email"], final["telefono"]) == (
        "Persona", "Correcta", "correcta@example.test", "1166667777"
    )
    assert final["cuenta"]["nombre_usuario"] == "correcta"
    assert final["cuenta"]["email_verificado"] is True
    estado_final = await solicitudes(cliente, escenario)
    assert estado_final["tercero@example.test"]["estado"] == "rechazada"
    assert "ficha_vinculada" not in estado_final["tercero@example.test"]
    assert estado_final["correcta@example.test"]["ficha_vinculada"]["id"] == f
    assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_tercero)).status_code == 404
    assert (await cliente.get(f"/api/v1/pacientes/{f}", headers=headers_correctos)).status_code == 200
    despues = await historial(cliente, escenario, f)
    assert [(t["id"], t["estado"]) for t in despues] == [(turno, "cancelado")]
    # Sólo cambia el nombre proyectado al corregir la ficha, no el turno conservado.
    assert [{k: v for k, v in t.items() if k not in {"paciente_nombre", "paciente_apellido"}}
            for t in despues] == [
        {k: v for k, v in t.items() if k not in {"paciente_nombre", "paciente_apellido"}}
        for t in despues_cancelar
    ]
