"""Bandeja y salud operativa con minimización y aislamiento real en PostgreSQL."""
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import text

from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def contexto(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


async def agregar(sesiones, *, cid=1, estado="fallida", programada=None, reclamada=None,
                  enviada=None, tipo="verificacion_email"):
    async with sesiones() as s:
        id_ = await s.scalar(text("""INSERT INTO notificacion
            (consultorio_id,tipo,canal,estado,destinatario,programada_para,reclamada_en,enviada_en,intentos,mensaje,ultimo_error)
            VALUES (:cid,:tipo,'email',:estado,'private-email.test',:p,:r,:e,1,'private-token','private-error') RETURNING id"""),
            {"cid": cid, "tipo": tipo, "estado": estado, "p": programada or AHORA,
             "r": reclamada, "e": enviada})
        await s.commit()
    return id_


async def get(e, path, rol="recepcion", cid=1):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=e.app), base_url="http://test") as c:
        return await c.get(path, headers=e.headers(rol, cid) if rol else {})


async def test_failed_inbox_has_minimal_projection_order_filter_and_pagination(contexto, sesiones):
    one = await agregar(sesiones)
    two = await agregar(sesiones)
    await agregar(sesiones, cid=2)
    await agregar(sesiones, estado="programada")
    response = await get(contexto, "/api/v1/notificaciones?estado=fallida&limit=1&offset=1")
    assert response.status_code == 200, response.text
    assert len(response.json()) == 1
    assert response.json()[0]["id"] == one < two
    assert set(response.json()[0]) == {"id", "turno_id", "tipo", "canal", "estado", "intentos",
                                     "programada_para", "reclamada_en", "enviada_en"}
    assert "private" not in response.text


@pytest.mark.parametrize("rol,codigo", [("administrador",200), ("recepcion",200),
    ("profesional",403), ("paciente",403), ("administrativo",403), (None,401)])
@pytest.mark.parametrize("path", ["/api/v1/notificaciones", "/api/v1/notificaciones/indicadores"])
async def test_operations_role_matrix(contexto, rol, codigo, path):
    response = await get(contexto, path, rol)
    assert response.status_code == codigo, response.text


@pytest.mark.parametrize("query", ["estado=no-existe", "limit=0", "limit=101", "offset=-1", "consultorio_id=2"])
async def test_inbox_invalid_queries_are_rejected(contexto, query):
    response = await get(contexto, "/api/v1/notificaciones?"+query)
    assert response.status_code == 422


async def test_inbox_empty_and_other_consultorio_are_independent(contexto, sesiones):
    await agregar(sesiones, cid=1)
    response = await get(contexto, "/api/v1/notificaciones", "administrador", 2)
    assert response.status_code == 200
    assert response.json() == []


async def test_empty_metrics_do_not_invent_an_execution(contexto):
    response = await get(contexto, "/api/v1/notificaciones/indicadores")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result == {"fallidas": 0, "programada_mas_antigua_segundos": None,
                      "enviando": 0, "enviando_mas_antigua_segundos": None,
                      "correos_del_dia": 0, "limite_diario": 500, "limite_cuenta": 150,
                      "alerta": False, "ultimo_barrido": None}


async def test_metrics_use_local_day_live_claims_and_separate_age_state(contexto, sesiones):
    await agregar(sesiones, estado="enviada", enviada=AHORA.replace(hour=0)-timedelta(microseconds=1))
    await agregar(sesiones, estado="enviada", enviada=AHORA.replace(hour=0))
    await agregar(sesiones, estado="enviando", reclamada=AHORA-timedelta(seconds=120))
    await agregar(sesiones, estado="enviando", reclamada=AHORA-timedelta(seconds=121))
    await agregar(sesiones, estado="programada", programada=AHORA-timedelta(seconds=25))
    await agregar(sesiones, estado="programada", programada=AHORA+timedelta(days=1))
    await agregar(sesiones)
    await agregar(sesiones, cid=2)
    response = await get(contexto, "/api/v1/notificaciones/indicadores")
    assert response.status_code == 200
    result = response.json()
    assert result["fallidas"] == 1
    assert result["programada_mas_antigua_segundos"] == 25
    assert result["enviando"] == 2
    assert result["enviando_mas_antigua_segundos"] == 121
    assert result["correos_del_dia"] == 2


@pytest.mark.parametrize("uso,alerta", [(399,False),(400,True)])
async def test_metrics_alert_exact_eighty_percent_and_future_ages(contexto, sesiones, uso, alerta):
    async with sesiones() as s:
        await s.execute(text("""INSERT INTO notificacion
            (consultorio_id,tipo,canal,estado,destinatario,programada_para,enviada_en,intentos)
            SELECT 1,'verificacion_email','email','enviada','test',:ahora,:ahora,1 FROM generate_series(1,:n)"""),
            {"ahora": AHORA, "n": uso})
        await s.commit()
    await agregar(sesiones, estado="programada", programada=AHORA+timedelta(days=1))
    response = await get(contexto, "/api/v1/notificaciones/indicadores")
    assert response.status_code == 200
    assert response.json()["alerta"] is alerta
    assert response.json()["programada_mas_antigua_segundos"] == 0


@pytest.mark.parametrize("estado", ["en_curso", "exitoso", "error"])
async def test_latest_execution_is_durable_and_scoped(contexto, sesiones, estado):
    execution = uuid4()
    async with sesiones() as s:
        await s.execute(text("""INSERT INTO barrido_estado
            (consultorio_id,ejecucion_id,iniciado_en,finalizado_en,estado,reclamadas,enviadas,reintentadas,omitidas,fallidas)
            VALUES (1,:id,:inicio,:fin,:estado,3,1,1,0,1)"""),
            {"id": execution, "inicio": AHORA-timedelta(seconds=10),
             "fin": None if estado=="en_curso" else AHORA, "estado":estado})
        await s.commit()
    # A fresh HTTP composition still reads PostgreSQL state.
    response = await get(contexto, "/api/v1/notificaciones/indicadores")
    assert response.status_code == 200, response.text
    last = response.json()["ultimo_barrido"]
    assert last["ejecucion_id"] == str(execution)
    assert last["estado"] == estado and last["reclamadas"] == 3
    assert "private" not in response.text
    foreign = await get(contexto, "/api/v1/notificaciones/indicadores", "administrador", 2)
    assert foreign.json()["ultimo_barrido"] is None
