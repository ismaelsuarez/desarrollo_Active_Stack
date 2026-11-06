import asyncio
import httpx
import pytest
from datetime import timedelta
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.integration.c07_support import INICIO, preparar_escenario
from app.infrastructure.db.sobreturnos import RepositorioSobreturnosSQL
from app.infrastructure.db.historial import RepositorioHistorialSQL
from app.application.services.hitos import ProgramadorHitos
from app.application.ports.avisos_turno import ProgramadorAvisosStaff

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


@pytest.mark.parametrize("rol", ["recepcion", "administrador"])
async def test_personal_crea_sobreturno_autorizado_en_intervalo_ocupado(escenario, sesiones, rol):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert regular.status_code == 201
        respuesta = await client.post("/api/v1/sobreturnos", headers=escenario.headers(rol),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
    assert respuesta.status_code == 201, respuesta.text
    assert respuesta.json()["es_sobreturno"] is True
    async with sesiones() as sesion:
        fila = (await sesion.execute(text("SELECT motivo, autorizado_por_id FROM autorizacion_sobreturno WHERE turno_id=:id"),
                                     {"id": respuesta.json()["id"]})).one()
        assert fila == ("Urgencia", escenario.usuarios[1, rol])
        accion = await sesion.scalar(text("SELECT accion FROM turno_historial WHERE turno_id=:id"), {"id": respuesta.json()["id"]})
        assert accion == "sobreturno"


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_roles_no_autorizados_no_crean_sobreturnos(escenario, sesiones, rol):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/sobreturnos", headers=escenario.headers(rol),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
    assert respuesta.status_code == 403
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0


@pytest.mark.parametrize("cambio", [{"autorizado": False}, {"motivo": "  "}, {"motivo": ""}, {"autorizado": None}])
async def test_solicitud_requiere_autorizacion_y_motivo(escenario, sesiones, cambio):
    datos = {"autorizado": True, "motivo": "Urgencia"} | cambio
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/sobreturnos", headers=escenario.headers(), json=escenario.payload(**datos))
    assert respuesta.status_code == 422
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 0


@pytest.mark.parametrize("caso", ["libre", "contiguo", "cancelado", "liberado", "fuera", "bloqueado", "grilla"])
async def test_rechaza_intervalos_que_no_cumplen_condiciones(escenario, sesiones, caso):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        if caso in ("contiguo", "cancelado", "liberado", "bloqueado", "grilla"):
            regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
            assert regular.status_code == 201
        if caso in ("cancelado", "liberado"):
            async with sesiones() as sesion:
                await sesion.execute(text("UPDATE turno SET estado=CAST(:estado AS estado_turno)"), {"estado": caso})
                await sesion.commit()
        if caso == "bloqueado":
            async with sesiones() as sesion:
                await sesion.execute(text("""
                    INSERT INTO bloqueo_agenda (consultorio_id, profesional_id,tipo,inicio,fin,creado_por_id,creado_en)
                    VALUES (1,:prof,'bloqueo',:inicio,:fin,:usuario,:ahora)
                """), {"prof": escenario.profesionales[1], "inicio": INICIO, "fin": INICIO + timedelta(minutes=30),
                        "usuario": escenario.usuarios[1, "recepcion"], "ahora": escenario.reloj.ahora()})
                await sesion.commit()
        inicio = INICIO + timedelta(minutes=30) if caso == "contiguo" else INICIO.replace(hour=23) if caso == "fuera" else INICIO + timedelta(minutes=7) if caso == "grilla" else INICIO
        respuesta = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(inicio=inicio, autorizado=True, motivo="Urgencia"))
    assert respuesta.status_code == 422, respuesta.text
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM autorizacion_sobreturno")) == 0


@pytest.mark.parametrize("punto", ["autorizacion", "historial", "hitos", "avisos"])
async def test_fallos_revierten_turno_y_autorizacion(escenario, sesiones, monkeypatch, punto):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url="http://test") as client:
        regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert regular.status_code == 201
        async def fallar(*args, **kwargs):
            raise RuntimeError("fallo sintético")
        objeto, metodo = {"autorizacion": (RepositorioSobreturnosSQL, "agregar"),
                          "historial": (RepositorioHistorialSQL, "agregar"),
                          "hitos": (ProgramadorHitos, "planificar"),
                          "avisos": (ProgramadorAvisosStaff, "programar")}[punto]
        monkeypatch.setattr(objeto, metodo, fallar)
        respuesta = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
    assert respuesta.status_code == 500
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM turno")) == 1
        assert await sesion.scalar(text("SELECT count(*) FROM turno_historial")) == 1
        assert await sesion.scalar(text("SELECT count(*) FROM autorizacion_sobreturno")) == 0


async def test_sobreturno_conserva_exclusion_regular_y_programa_avisos(escenario, sesiones):
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE paciente SET email='sintetico@example.test' WHERE id=:id"), {"id": escenario.pacientes[1]})
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        sobreturno = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
        segundo_regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert (regular.status_code, sobreturno.status_code, segundo_regular.status_code) == (201, 201, 409)
    async with sesiones() as sesion:
        assert await sesion.scalar(text("SELECT count(*) FROM notificacion WHERE turno_id=:id"), {"id": sobreturno.json()["id"]}) >= 1
        with pytest.raises(IntegrityError) as error:
            await sesion.execute(text("""
                INSERT INTO turno (consultorio_id,paciente_id,profesional_id,box_id,prestacion_id,inicio,fin,creado_en)
                SELECT consultorio_id,paciente_id,profesional_id,box_id,prestacion_id,inicio,fin,creado_en
                FROM turno WHERE id=:id
            """), {"id": regular.json()["id"]})
        assert error.value.orig.sqlstate == "23P01"
        await sesion.rollback()


async def test_profesional_rechaza_sin_modificar_estado_del_turno(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        creado = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
        turno_id = creado.json()["id"]
        respuesta = await client.post(f"/api/v1/sobreturnos/{turno_id}/respuesta-profesional",
            headers=escenario.headers("profesional"), json={"respuesta": "rechazado", "comentario": "Agenda completa"})
    assert respuesta.status_code == 200, respuesta.text
    async with sesiones() as sesion:
        fila = (await sesion.execute(text("""
            SELECT t.estado, a.respuesta, a.respondido_por_id, a.respondido_en, a.comentario
            FROM turno t JOIN autorizacion_sobreturno a ON a.turno_id=t.id WHERE t.id=:id
        """), {"id": turno_id})).one()
        assert fila == (creado.json()["estado"], "rechazado", escenario.usuarios[1, "profesional"], escenario.reloj.ahora(), "Agenda completa")


async def test_dos_autorizaciones_concurrentes_quedan_trazadas(escenario, sesiones):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        regular = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        assert regular.status_code == 201
        async def autorizar(motivo):
            return await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
                json=escenario.payload(autorizado=True, motivo=motivo))
        respuestas = await asyncio.gather(autorizar("Urgencia A"), autorizar("Urgencia B"))
    assert [r.status_code for r in respuestas] == [201, 201]
    async with sesiones() as sesion:
        motivos = (await sesion.scalars(text("SELECT motivo FROM autorizacion_sobreturno ORDER BY motivo"))).all()
        assert motivos == ["Urgencia A", "Urgencia B"]


@pytest.mark.parametrize("caso,esperado", [("admin_propio", 200), ("admin_sin_agenda", 403),
    ("admin_otra_agenda", 403), ("profesional_ajeno", 403), ("otro_consultorio", 404),
    ("recepcion", 403), ("paciente", 403), ("administrativo", 403)])
async def test_respuesta_solo_de_la_agenda_propia(escenario, sesiones, caso, esperado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        creado = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
        turno_id = creado.json()["id"]
        if caso == "admin_propio":
            async with sesiones() as sesion:
                await sesion.execute(text("UPDATE profesional SET usuario_id=:uid WHERE id=:pid"),
                    {"uid": escenario.usuarios[1, "administrador"], "pid": escenario.profesionales[1]})
                await sesion.commit()
        if caso in ("admin_otra_agenda", "profesional_ajeno"):
            async with sesiones() as sesion:
                if caso == "profesional_ajeno":
                    await sesion.execute(text("UPDATE profesional SET usuario_id=NULL WHERE id=:pid"), {"pid": escenario.profesionales[1]})
                box_id = await sesion.scalar(text("INSERT INTO box (consultorio_id,nombre) VALUES (1,'Otro') RETURNING id"))
                rol = "administrador" if caso == "admin_otra_agenda" else "profesional"
                await sesion.execute(text("INSERT INTO profesional (consultorio_id,usuario_id,box_id,nombre,apellido) VALUES (1,:uid,:box,'Otro','Profesional')"),
                    {"uid": escenario.usuarios[1, rol], "box": box_id})
                await sesion.commit()
        rol = "administrador" if caso.startswith("admin") else "profesional" if caso in ("profesional_ajeno", "otro_consultorio") else caso
        respuesta = await client.post(f"/api/v1/sobreturnos/{turno_id}/respuesta-profesional",
            headers=escenario.headers(rol, consultorio=2 if caso == "otro_consultorio" else 1),
            json={"respuesta": "aprobado"})
    assert respuesta.status_code == esperado, respuesta.text
    async with sesiones() as sesion:
        valor = await sesion.scalar(text("SELECT respuesta FROM autorizacion_sobreturno WHERE turno_id=:id"), {"id": turno_id})
        assert valor == ("aprobado" if esperado == 200 else None)


async def test_lecturas_muestran_aviso_al_personal_y_no_al_paciente(escenario, sesiones):
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE paciente SET usuario_id=:uid WHERE id=:pid"),
            {"uid": escenario.usuarios[1, "paciente"], "pid": escenario.pacientes[1]})
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
        creado = await client.post("/api/v1/sobreturnos", headers=escenario.headers(),
            json=escenario.payload(autorizado=True, motivo="Urgencia"))
        turno_id = creado.json()["id"]
        await client.post(f"/api/v1/sobreturnos/{turno_id}/respuesta-profesional",
            headers=escenario.headers("profesional"), json={"respuesta": "rechazado", "comentario": "Agenda completa"})
        detalle = await client.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers())
        agenda = await client.get("/api/v1/agenda", headers=escenario.headers("profesional"),
            params={"profesional_id": escenario.profesionales[1], "fecha": INICIO.date().isoformat()})
        paciente = await client.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("paciente"))
        lista_paciente = await client.get("/api/v1/turnos", headers=escenario.headers("paciente"))
        lista_staff = await client.get("/api/v1/turnos", headers=escenario.headers())
        ajeno = await client.get(f"/api/v1/turnos/{turno_id}", headers=escenario.headers("profesional", 2))
    assert detalle.status_code == agenda.status_code == paciente.status_code == lista_paciente.status_code == lista_staff.status_code == 200
    assert ajeno.status_code == 404
    aviso = detalle.json()["autorizacion_sobreturno"]
    assert (aviso["motivo"], aviso["respuesta"], aviso["comentario"]) == ("Urgencia", "rechazado", "Agenda completa")
    assert next(t for t in agenda.json() if t["id"] == turno_id)["autorizacion_sobreturno"] == aviso
    assert "autorizacion_sobreturno" not in paciente.json()
    assert all("autorizacion_sobreturno" not in turno for turno in lista_paciente.json())
    assert next(t for t in lista_staff.json() if t["id"] == turno_id)["autorizacion_sobreturno"] == aviso
    assert "Urgencia" not in paciente.text and "Agenda completa" not in paciente.text
