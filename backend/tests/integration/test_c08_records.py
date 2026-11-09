"""RN-47/RN-50: fichas scoped con PostgreSQL y API reales."""
import httpx
import pytest
from sqlalchemy import select

from app.infrastructure.db.models import PacienteModel, UsuarioModel
from tests.integration.test_c07_agenda import registrar_turno
from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration

DATOS = {"nombre": "Eva", "apellido": "Sol", "telefono": "1155556666",
         "email": "eva@example.test", "dni": "87654321", "obra_social": None, "notas": None}


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


@pytest.fixture
async def cliente(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        yield client


async def test_repositorio_crea_y_recupera_ficha_scoped(sesiones, escenario):
    from app.infrastructure.db.pacientes import RepositorioPacientesSQL

    async with sesiones() as sesion:
        repo = RepositorioPacientesSQL(sesion)
        creada = await repo.crear(1, DATOS, AHORA)
        pid = creada.id
        await sesion.commit()
    async with sesiones() as sesion:
        repo = RepositorioPacientesSQL(sesion)
        propia = await repo.obtener(1, pid)
        assert propia.nombre == "Eva" and propia.dni == "87654321"
        assert propia.usuario_id is None and propia.activo is True
        assert propia.creado_en == AHORA and propia.actualizado_en == AHORA
        assert await repo.obtener(2, pid) is None


async def test_recepcion_crea_ficha_recuperable_sin_cuenta(cliente, escenario, sesiones):
    respuesta = await cliente.post("/api/v1/pacientes", json=DATOS, headers=escenario.headers())
    assert respuesta.status_code == 201
    pid = respuesta.json()["id"]
    detalle = await cliente.get(f"/api/v1/pacientes/{pid}", headers=escenario.headers())
    assert detalle.status_code == 200
    assert detalle.json()["nombre"] == "Eva"
    assert detalle.json()["cuenta"] is None
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        assert ficha.usuario_id is None and ficha.consultorio_id == 1


@pytest.mark.parametrize("rol", ["profesional", "paciente", "administrativo"])
async def test_alta_denegada_a_roles_no_habilitados(cliente, escenario, sesiones, rol):
    respuesta = await cliente.post("/api/v1/pacientes", json=DATOS, headers=escenario.headers(rol))
    assert respuesta.status_code == 403
    async with sesiones() as sesion:
        assert await sesion.scalar(select(PacienteModel.id).where(PacienteModel.dni == DATOS["dni"])) is None


@pytest.mark.parametrize("campo,valor", [("activo", False), ("usuario_id", 1), ("consultorio_id", 2)])
async def test_alta_rechaza_campos_del_servidor(cliente, escenario, campo, valor):
    respuesta = await cliente.post("/api/v1/pacientes", json={**DATOS, campo: valor}, headers=escenario.headers())
    assert respuesta.status_code == 422


async def test_dni_duplicado_mismo_consultorio_conflicto_y_otro_consultorio_permitido(cliente, escenario, sesiones):
    primera = await cliente.post("/api/v1/pacientes", json=DATOS, headers=escenario.headers())
    duplicada = await cliente.post("/api/v1/pacientes", json=DATOS, headers=escenario.headers())
    otro = await cliente.post("/api/v1/pacientes", json=DATOS, headers=escenario.headers(consultorio=2))
    assert primera.status_code == 201
    assert duplicada.status_code == 409
    assert otro.status_code == 201
    assert "87654321" not in duplicada.text
    async with sesiones() as sesion:
        fichas = (await sesion.scalars(select(PacienteModel).where(PacienteModel.dni == DATOS["dni"]))).all()
        assert sorted(f.consultorio_id for f in fichas) == [1, 2]


@pytest.mark.parametrize("rol", ["recepcion", "administrador", "profesional", "paciente"])
async def test_detalle_proyecta_cuenta_solo_a_personal(cliente, escenario, sesiones, rol):
    pid = escenario.pacientes[1]
    uid = escenario.usuarios[1, "paciente"]
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        ficha.usuario_id = uid
        await sesion.commit()
    await registrar_turno(sesiones, escenario, paciente_id=pid)
    respuesta = await cliente.get(f"/api/v1/pacientes/{pid}", headers=escenario.headers(rol))
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert "usuario_id" not in datos and "password_hash" not in str(datos)
    assert datos["telefono"] is None and datos["email"] is None  # legado válido
    if rol in ("recepcion", "administrador"):
        assert datos["cuenta"] == {"id": uid, "nombre_usuario": "paciente1",
                                  "email": "paciente1@example.test", "email_verificado": False}
    else:
        assert "cuenta" not in datos


@pytest.mark.parametrize("rol,objetivo,codigo", [
    ("recepcion", "ajeno", 404), ("administrador", "ajeno", 404),
    ("profesional", "propio", 404), ("paciente", "propio", 404),
    ("administrativo", "propio", 403), ("recepcion", "inexistente", 404),
])
async def test_detalle_oculta_fichas_fuera_de_alcance(cliente, escenario, rol, objetivo, codigo):
    pid = escenario.pacientes[2 if objetivo == "ajeno" else 1] if objetivo != "inexistente" else 99999
    respuesta = await cliente.get(f"/api/v1/pacientes/{pid}", headers=escenario.headers(rol))
    assert respuesta.status_code == codigo
    assert "Ana" not in respuesta.text and "1234567" not in respuesta.text


async def test_busqueda_paginada_solo_cuenta_fichas_del_consultorio(cliente, escenario):
    respuesta = await cliente.get("/api/v1/pacientes", headers=escenario.headers())
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 1 and datos["limit"] == 20 and datos["offset"] == 0
    assert datos["items"] == [{"id": escenario.pacientes[1], "nombre": "Ana", "apellido": "Prueba",
                               "telefono": None, "activo": True}]


async def sembrar_busqueda(sesiones):
    from app.infrastructure.db.pacientes import RepositorioPacientesSQL

    async with sesiones() as sesion:
        repo = RepositorioPacientesSQL(sesion)
        eva = await repo.crear(1, DATOS, AHORA)
        luz = await repo.crear(1, {**DATOS, "nombre": "Luz", "dni": "23456789", "telefono": "1166667777"}, AHORA)
        ari = await repo.crear(1, {**DATOS, "nombre": "Ari", "apellido": "100%Real", "dni": "34567890", "telefono": "12_34"}, AHORA)
        await repo.crear(2, DATOS, AHORA)
        await sesion.commit()
        return {"Eva": eva.id, "Luz": luz.id, "Ari": ari.id}


@pytest.mark.parametrize("filtros,nombres", [
    ({"apellido": "sOL"}, ["Eva", "Luz"]),
    ({"dni": " 87654321 "}, ["Eva"]),
    ({"telefono": "5555"}, ["Eva"]),
    ({"apellido": "Sol", "telefono": "7777"}, ["Luz"]),
    ({"apellido": "%"}, ["Ari"]),
    ({"telefono": "_"}, ["Ari"]),
    ({"dni": "00000000"}, []),
])
async def test_busqueda_combina_criterios_y_trata_comodines_literalmente(cliente, escenario, sesiones, filtros, nombres):
    await sembrar_busqueda(sesiones)
    respuesta = await cliente.get("/api/v1/pacientes", params=filtros, headers=escenario.headers())
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert [f["nombre"] for f in datos["items"]] == nombres
    assert datos["total"] == len(nombres)


async def test_paginacion_estable_total_sin_datos_extranos(cliente, escenario, sesiones):
    await sembrar_busqueda(sesiones)
    primera = (await cliente.get("/api/v1/pacientes", params={"limit": 2}, headers=escenario.headers())).json()
    segunda = (await cliente.get("/api/v1/pacientes", params={"limit": 2, "offset": 2}, headers=escenario.headers())).json()
    vacia = (await cliente.get("/api/v1/pacientes", params={"offset": 99}, headers=escenario.headers())).json()
    assert [f["nombre"] for f in primera["items"] + segunda["items"]] == ["Ari", "Ana", "Eva", "Luz"]
    assert primera["total"] == segunda["total"] == vacia["total"] == 4
    assert vacia["items"] == []
    assert not ({f["id"] for f in primera["items"]} & {f["id"] for f in segunda["items"]})


@pytest.mark.parametrize("rol,vinculada,nombres", [
    ("profesional", False, ["Ana"]), ("paciente", False, []), ("paciente", True, ["Ana"]),
])
async def test_busqueda_aplica_alcance_antes_del_total(cliente, escenario, sesiones, rol, vinculada, nombres):
    await sembrar_busqueda(sesiones)
    await registrar_turno(sesiones, escenario)
    if vinculada:
        async with sesiones() as sesion:
            ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
            ficha.usuario_id = escenario.usuarios[1, "paciente"]
            await sesion.commit()
    respuesta = await cliente.get("/api/v1/pacientes", headers=escenario.headers(rol))
    assert respuesta.status_code == 200
    assert [f["nombre"] for f in respuesta.json()["items"]] == nombres
    assert respuesta.json()["total"] == len(nombres)
    filtrada = await cliente.get("/api/v1/pacientes", params={"apellido": "Sol"}, headers=escenario.headers(rol))
    assert filtrada.json()["items"] == [] and filtrada.json()["total"] == 0


@pytest.mark.parametrize("parametros", [{"limit": 0}, {"limit": 101}, {"offset": -1},
                                       {"dni": "12.345"}, {"consultorio_id": 2}])
async def test_busqueda_rechaza_parametros_invalidos(cliente, escenario, parametros):
    respuesta = await cliente.get("/api/v1/pacientes", params=parametros, headers=escenario.headers())
    assert respuesta.status_code == 422


async def test_personal_edita_solo_campos_enviados(cliente, escenario, sesiones):
    pid = escenario.pacientes[1]
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}",
                                    json={"apellido": " Otra ", "obra_social": " Obra ", "notas": None},
                                    headers=escenario.headers())
    assert respuesta.status_code == 200 and respuesta.json()["id"] == pid
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        assert ficha.nombre == "Ana" and ficha.apellido == "Otra"
        assert ficha.obra_social == "Obra" and ficha.notas is None
        assert ficha.telefono is None and ficha.usuario_id is None and ficha.activo is True
        assert ficha.dni == "12345671" and ficha.creado_en == AHORA and ficha.actualizado_en == AHORA


@pytest.mark.parametrize("datos,codigo", [
    ({"activo": False}, 422), ({"usuario_id": 4}, 422), ({"consultorio_id": 2}, 422),
    ({"nombre": None}, 422), ({"telefono": None}, 422), ({}, 422),
    ({"dni": "12.345"}, 422), ({"dni": "87654321"}, 409),
])
async def test_patch_personal_invalido_no_deja_cambios(cliente, escenario, sesiones, datos, codigo):
    await sembrar_busqueda(sesiones)
    pid = escenario.pacientes[1]
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}", json=datos, headers=escenario.headers())
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        assert ficha.nombre == "Ana" and ficha.dni == "12345671" and ficha.activo is True
        assert ficha.usuario_id is None and ficha.telefono is None


async def test_editar_contacto_de_ficha_no_cambia_login_y_conserva_turnos(cliente, escenario, sesiones):
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        ficha.usuario_id = uid
        user = await sesion.get(UsuarioModel, uid)
        user.email_verificado = True
        await sesion.commit()
    tid = await registrar_turno(sesiones, escenario)
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"email": " FICHA@EXAMPLE.TEST ", "telefono": " 1111222233 "}, headers=escenario.headers("administrador"))
    assert respuesta.status_code == 200
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        user = await sesion.get(UsuarioModel, uid)
        assert ficha.email == "ficha@example.test" and ficha.telefono == "1111222233"
        assert ficha.usuario_id == uid and user.email == "paciente1@example.test" and user.email_verificado is True
    turnos = await cliente.get(f"/api/v1/pacientes/{pid}/turnos", headers=escenario.headers())
    assert [t["id"] for t in turnos.json()] == [tid]


@pytest.mark.parametrize("rol,objetivo,codigo", [("profesional", "propio", 403),
                                               ("recepcion", "ajeno", 404), ("recepcion", "inexistente", 404)])
async def test_patch_personal_rechaza_rol_y_recurso_ajenos(cliente, escenario, rol, objetivo, codigo):
    pid = escenario.pacientes[2 if objetivo == "ajeno" else 1] if objetivo != "inexistente" else 99999
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"nombre": "Otra"}, headers=escenario.headers(rol))
    assert respuesta.status_code == codigo


async def vincular_titular(sesiones, escenario):
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.usuario_id = escenario.usuarios[1, "paciente"]
        usuario = await sesion.get(UsuarioModel, ficha.usuario_id)
        usuario.email_verificado = True
        await sesion.commit()


async def test_patch_propio_actualiza_telefono_vigente(cliente, escenario, sesiones):
    await vincular_titular(sesiones, escenario)
    pid = escenario.pacientes[1]
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"telefono": " 1122223333 "},
                                    headers=escenario.headers("paciente"))
    assert respuesta.status_code == 200 and respuesta.json() == {"id": pid}
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        usuario = await sesion.get(UsuarioModel, escenario.usuarios[1, "paciente"])
        assert ficha.telefono == "1122223333" and usuario.email_verificado is True
        assert ficha.nombre == "Ana" and ficha.dni == "12345671"


@pytest.mark.parametrize("campo,valor", [("nombre", "Privado"), ("dni", "87654321"),
                                        ("obra_social", None), ("notas", "Nota privada")])
async def test_patch_propio_rechaza_campos_ajenos_a_contacto(cliente, escenario, sesiones, campo, valor):
    await vincular_titular(sesiones, escenario)
    pid = escenario.pacientes[1]
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}",
                                    json={"telefono": "1199999999", campo: valor},
                                    headers=escenario.headers("paciente"))
    assert respuesta.status_code == 422
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        assert ficha.nombre == "Ana" and ficha.dni == "12345671" and ficha.telefono is None


async def test_patch_propio_correo_diferente_reverifica_y_despacha_tras_commit(cliente, escenario, sesiones):
    from app.api.v1.routers.cuentas import get_enviador_correo
    from app.infrastructure.db.account_models import NotificacionModel
    from app.infrastructure.db.models import TokenUsuarioModel

    await vincular_titular(sesiones, escenario)
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    async with sesiones() as sesion:
        sesion.add(TokenUsuarioModel(consultorio_id=1, usuario_id=uid, tipo="verificar_email",
                    token_hash="d" * 64, creado_en=AHORA, expira_en=AHORA.replace(year=2027)))
        await sesion.commit()
    enviados = []

    class Correo:
        async def enviar(self, destinatario, asunto, cuerpo):
            async with sesiones() as sesion:
                usuario = await sesion.get(UsuarioModel, uid)
                assert usuario.email == "nuevo@example.test" and usuario.email_verificado is False
                assert (await sesion.get(PacienteModel, pid)).email == usuario.email
            enviados.append(destinatario)

    escenario.app.dependency_overrides[get_enviador_correo] = Correo
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"email": " NUEVO@EXAMPLE.TEST "},
                                    headers=escenario.headers("paciente"))
    assert respuesta.status_code == 200 and respuesta.json() == {"id": pid}
    assert enviados == ["nuevo@example.test"]
    async with sesiones() as sesion:
        tokens = (await sesion.scalars(select(TokenUsuarioModel))).all()
        assert len(tokens) == 2
        assert next(t for t in tokens if t.token_hash == "d" * 64).usado_en == AHORA
        trabajos = (await sesion.scalars(select(NotificacionModel))).all()
        assert len(trabajos) == 1 and trabajos[0].estado == "enviada"


async def test_coleccion_y_rechazos_no_filtran_sentinelas_privados(cliente, escenario, sesiones, caplog):
    import logging

    privados = ["dni-privado-sentinel", "correo-privado-sentinel", "obra-privada-sentinel",
                "nota-privada-sentinel", "query-privada-sentinel"]
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, escenario.pacientes[1])
        ficha.notas, ficha.obra_social = privados[3], privados[2]
        await sesion.commit()
    caplog.set_level(logging.INFO, logger="tpi.api")
    lista = await cliente.get("/api/v1/pacientes", headers=escenario.headers())
    assert set(lista.json()["items"][0]) == {"id", "nombre", "apellido", "telefono", "activo"}
    invalida = await cliente.post("/api/v1/pacientes", json={**DATOS, "dni": privados[0], "email": privados[1]},
                                  headers=escenario.headers())
    assert invalida.status_code == 422
    ajena = await cliente.get(f"/api/v1/pacientes/{escenario.pacientes[1]}",
                              headers=escenario.headers("paciente"))
    assert ajena.status_code == 404
    busqueda = await cliente.get("/api/v1/pacientes", params={"apellido": privados[4]}, headers=escenario.headers())
    assert busqueda.status_code == 200 and busqueda.json()["items"] == []
    logs_api = " ".join(r.getMessage() for r in caplog.records if r.name == "tpi.api")
    assert logs_api
    for secreto in privados:
        assert secreto not in lista.text + invalida.text + ajena.text + logs_api


@pytest.mark.parametrize("rol", ["recepcion", "profesional"])
async def test_sin_borrado_ni_desactivacion_conserva_historial(cliente, escenario, sesiones, rol):
    pid = escenario.pacientes[1]
    tid = await registrar_turno(sesiones, escenario)
    antes = await cliente.get(f"/api/v1/pacientes/{pid}/turnos", headers=escenario.headers(rol))
    assert antes.status_code == 200 and [t["id"] for t in antes.json()] == [tid]
    borrar = await cliente.delete(f"/api/v1/pacientes/{pid}", headers=escenario.headers())
    desactivar = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"activo": False}, headers=escenario.headers())
    corregir = await cliente.patch(f"/api/v1/pacientes/{pid}", json={"apellido": "Corregido"}, headers=escenario.headers())
    assert borrar.status_code == 405 and desactivar.status_code == 422 and corregir.status_code == 200
    despues = await cliente.get(f"/api/v1/pacientes/{pid}/turnos", headers=escenario.headers(rol))
    assert despues.status_code == 200
    esperado = [{**turno, "paciente_apellido": "Corregido"} for turno in antes.json()]
    assert despues.json() == esperado
    async with sesiones() as sesion:
        ficha = await sesion.get(PacienteModel, pid)
        assert ficha.activo is True and ficha.apellido == "Corregido"


@pytest.mark.parametrize("fallo", ["flush", "commit"])
async def test_patch_personal_fallido_revierte_y_conserva_cuenta_y_turnos(engine, sesiones, escenario, fallo):
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    await vincular_titular(sesiones, escenario)
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    tid = await registrar_turno(sesiones, escenario)
    eventos = []

    class SesionFallida(AsyncSession):
        async def flush(self, *args, **kwargs):
            await super().flush(*args, **kwargs)
            if fallo == "flush":
                raise RuntimeError("flush controlado de ficha")

        async def commit(self):
            await self.flush()
            raise RuntimeError("commit controlado de ficha")

        async def rollback(self):
            eventos.append("rollback")
            await super().rollback()

    escenario.app.state.session_factory = async_sessionmaker(engine, class_=SesionFallida, expire_on_commit=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False),
                                base_url="http://test") as client:
        respuesta = await client.patch(f"/api/v1/pacientes/{pid}",
                                       json={"nombre": "No persistir", "email": "fallo@example.test"},
                                       headers=escenario.headers())
    assert respuesta.status_code == 500 and eventos == ["rollback"]
    async with sesiones() as sesion:
        ficha, usuario = await sesion.get(PacienteModel, pid), await sesion.get(UsuarioModel, uid)
        assert ficha.nombre == "Ana" and ficha.email is None and ficha.usuario_id == uid
        assert usuario.email == "paciente1@example.test" and usuario.email_verificado is True
        from app.infrastructure.db.models import TurnoModel
        assert (await sesion.get(TurnoModel, tid)).paciente_id == pid


@pytest.mark.parametrize("email,codigo", [(" PACIENTE1@EXAMPLE.TEST ", 200),
                                         ("recepcion1@example.test", 409)])
async def test_patch_propio_correo_equivalente_u_ocupado_no_programa_verificacion(
        cliente, escenario, sesiones, email, codigo):
    from app.infrastructure.db.account_models import NotificacionModel

    await vincular_titular(sesiones, escenario)
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}",
        json={"email": email, "telefono": "1188889999"}, headers=escenario.headers("paciente"))
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        usuario = await sesion.get(UsuarioModel, uid)
        ficha = await sesion.get(PacienteModel, pid)
        assert usuario.email == "paciente1@example.test" and usuario.email_verificado is True
        assert ficha.telefono == ("1188889999" if codigo == 200 else None)
        assert (await sesion.scalars(select(NotificacionModel))).all() == []


@pytest.mark.parametrize("estado,codigo", [("40P01", 409), ("40001", 409), ("23503", 500)])
async def test_patch_propio_error_postgres_revierte_contacto_y_verificacion(
        escenario, sesiones, monkeypatch, estado, codigo):
    from sqlalchemy import text
    from app.infrastructure.db.cuentas import RepositorioCuentas
    from app.infrastructure.db.account_models import NotificacionModel
    from app.infrastructure.db.models import TokenUsuarioModel

    await vincular_titular(sesiones, escenario)
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    original = RepositorioCuentas.programar_token

    async def fallar_despues_de_escribir(repo, *args, **kwargs):
        await original(repo, *args, **kwargs)
        await repo.sesion.execute(text(
            f"DO $$ BEGIN RAISE EXCEPTION 'Fallo controlado' USING ERRCODE = '{estado}'; END $$"))

    monkeypatch.setattr(RepositorioCuentas, "programar_token", fallar_despues_de_escribir)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False),
                                base_url="http://test") as cliente:
        respuesta = await cliente.patch(f"/api/v1/pacientes/{pid}",
            json={"telefono": "1188889999", "email": "no-persistir@example.test"},
            headers=escenario.headers("paciente"))
    assert respuesta.status_code == codigo
    async with sesiones() as sesion:
        usuario, ficha = await sesion.get(UsuarioModel, uid), await sesion.get(PacienteModel, pid)
        assert usuario.email == "paciente1@example.test" and usuario.email_verificado is True
        assert ficha.email is None and ficha.telefono is None and ficha.usuario_id == uid
        assert (await sesion.scalars(select(NotificacionModel))).all() == []
        assert (await sesion.scalars(select(TokenUsuarioModel))).all() == []


async def test_patch_propio_recarga_vinculo_cambiado_entre_lectura_y_escritura(
        cliente, escenario, sesiones, monkeypatch):
    import asyncio
    from contextvars import ContextVar
    from app.infrastructure.db.cuentas import RepositorioCuentas

    await vincular_titular(sesiones, escenario)
    pid, uid = escenario.pacientes[1], escenario.usuarios[1, "paciente"]
    leido, continuar = asyncio.Event(), asyncio.Event()
    operacion = ContextVar("operacion_c08", default=None)
    original = RepositorioCuentas.usuario_por_id

    async def esperar_tras_lectura(repo, cid, usuario_id):
        if operacion.get() == "contacto-c08":
            leido.set()
            await asyncio.wait_for(continuar.wait(), 10)
        return await original(repo, cid, usuario_id)

    monkeypatch.setattr(RepositorioCuentas, "usuario_por_id", esperar_tras_lectura)
    async def actualizar_contacto():
        token = operacion.set("contacto-c08")
        try:
            return await cliente.patch(f"/api/v1/pacientes/{pid}",
                json={"telefono": "1188889999"}, headers=escenario.headers("paciente"))
        finally:
            operacion.reset(token)

    tarea = asyncio.create_task(actualizar_contacto())
    await asyncio.wait_for(leido.wait(), 10)
    try:
        desvinculada = await cliente.post(f"/api/v1/pacientes/{pid}/desvincular",
            json={"motivo": "Corrección"}, headers=escenario.headers())
        assert desvinculada.status_code == 200
        async with sesiones() as sesion:
            nueva = PacienteModel(consultorio_id=1, nombre="Nueva", apellido="Ficha", dni="99000000",
                usuario_id=uid, telefono="1100000000", creado_en=AHORA, actualizado_en=AHORA)
            sesion.add(nueva)
            await sesion.commit()
            nuevo_id = nueva.id
    finally:
        continuar.set()
    respuesta = await asyncio.wait_for(tarea, 10)
    assert respuesta.status_code == 404
    async with sesiones() as sesion:
        assert (await sesion.get(PacienteModel, pid)).telefono is None
        assert (await sesion.get(PacienteModel, nuevo_id)).telefono == "1100000000"


@pytest.mark.parametrize("primero", ["contacto", "desvincular"])
async def test_contacto_y_desvinculacion_concurrentes_conservan_orden_serial(
        cliente, escenario, sesiones, monkeypatch, primero):
    import asyncio
    from contextvars import ContextVar
    from sqlalchemy import func
    from app.infrastructure.db.cuentas import RepositorioCuentas
    from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL

    await vincular_titular(sesiones, escenario)
    pid = escenario.pacientes[1]
    bloqueado, intentando, liberar = asyncio.Event(), asyncio.Event(), asyncio.Event()
    conexiones = set()
    operacion = ContextVar("operacion_c08", default=None)
    ficha_original = RepositorioCuentas.ficha_de_usuario
    usuario_original = RepositorioCuentas.usuario_por_id
    bloqueo_original = RepositorioVinculacionSQL.bloquear_ficha

    async def usuario(repo, *args):
        nombre = operacion.get()
        conexiones.add(await repo.sesion.scalar(select(func.pg_backend_pid())))
        if nombre == "contacto" and primero == "desvincular":
            intentando.set()
        resultado = await usuario_original(repo, *args)
        if nombre == "desvincular" and primero == "desvincular":
            bloqueado.set()
            await asyncio.wait_for(liberar.wait(), 10)
        return resultado

    async def ficha(repo, *args):
        resultado = await ficha_original(repo, *args)
        if primero == "contacto":
            bloqueado.set()
            await asyncio.wait_for(liberar.wait(), 10)
        return resultado

    async def bloquear(repo, *args):
        conexiones.add(await repo.sesion.scalar(select(func.pg_backend_pid())))
        if primero == "contacto":
            intentando.set()
        return await bloqueo_original(repo, *args)

    monkeypatch.setattr(RepositorioCuentas, "usuario_por_id", usuario)
    monkeypatch.setattr(RepositorioCuentas, "ficha_de_usuario", ficha)
    monkeypatch.setattr(RepositorioVinculacionSQL, "bloquear_ficha", bloquear)

    async def ejecutar(nombre):
        token = operacion.set(nombre)
        try:
            if nombre == "contacto":
                return await cliente.patch(f"/api/v1/pacientes/{pid}", json={"telefono": "1188889999"},
                                           headers=escenario.headers("paciente"))
            return await cliente.post(f"/api/v1/pacientes/{pid}/desvincular", json={"motivo": "Corrección"},
                                      headers=escenario.headers())
        finally:
            operacion.reset(token)

    otra = "desvincular" if primero == "contacto" else "contacto"
    inicial = asyncio.create_task(ejecutar(primero), name=primero)
    await asyncio.wait_for(bloqueado.wait(), 10)
    segunda = asyncio.create_task(ejecutar(otra), name=otra)
    try:
        await asyncio.wait_for(intentando.wait(), 10)
    finally:
        liberar.set()
    respuestas = await asyncio.wait_for(asyncio.gather(inicial, segunda), 15)
    assert [r.status_code for r in respuestas] == ([200, 200] if primero == "contacto" else [200, 404])
    assert len(conexiones) == 2
    async with sesiones() as sesion:
        ficha_final = await sesion.get(PacienteModel, pid)
        assert ficha_final.usuario_id is None
        assert ficha_final.telefono == ("1188889999" if primero == "contacto" else None)


async def test_profesional_lee_ficha_con_unico_turno_historico(cliente, escenario, sesiones):
    from datetime import timedelta

    await registrar_turno(sesiones, escenario, inicio=AHORA - timedelta(days=30), estado="atendido")
    detalle = await cliente.get(f"/api/v1/pacientes/{escenario.pacientes[1]}",
                                headers=escenario.headers("profesional"))
    lista = await cliente.get("/api/v1/pacientes", headers=escenario.headers("profesional"))
    assert detalle.status_code == 200 and "cuenta" not in detalle.json()
    assert lista.status_code == 200 and lista.json()["total"] == 1
    assert [p["id"] for p in lista.json()["items"]] == [escenario.pacientes[1]]
