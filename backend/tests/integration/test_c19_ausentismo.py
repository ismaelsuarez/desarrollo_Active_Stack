import httpx
import pytest
from datetime import datetime, timedelta

from tests.integration.c07_support import AHORA, preparar_escenario
from tests.integration.test_c07_agenda import registrar_turno, otro_profesional

pytestmark = pytest.mark.integration


@pytest.fixture
async def contexto(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


async def consultar(contexto, query='desde=2026-11-01&hasta=2026-11-30', rol='administrador', cid=1):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as client:
        return await client.get('/api/v1/indicadores/ausentismo?' + query, headers=contexto.headers(rol, cid) if rol else {})


async def test_periodo_sin_casos_devuelve_tasa_nula(contexto):
    response = await consultar(contexto)
    assert response.status_code == 200
    assert response.json()['resumen'] == {'ausentes': 0, 'atendidos': 0, 'cancelados': 0, 'liberados': 0, 'sin_cierre': 0, 'tasa': None}


async def test_agregados_filtran_estado_fecha_profesional_y_consultorio(contexto, sesiones):
    for i, estado in enumerate(['ausente', 'atendido', 'atendido', 'atendido', 'cancelado', 'liberado', 'pendiente', 'confirmado']):
        await registrar_turno(sesiones, contexto, estado=estado, inicio=AHORA - timedelta(hours=i + 1), historial=False)
    await registrar_turno(sesiones, contexto, estado='ausente', inicio=AHORA + timedelta(hours=1), historial=False)
    await registrar_turno(sesiones, contexto, cid=2, estado='ausente', inicio=AHORA - timedelta(days=1), historial=False)
    otro = await otro_profesional(sesiones)
    await registrar_turno(sesiones, contexto, profesional_id=otro, estado='ausente', inicio=AHORA - timedelta(days=1), historial=False)
    r = await consultar(contexto, f'desde=2026-11-01&hasta=2026-11-06&profesional_id={contexto.profesionales[1]}')
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['resumen'] == {'ausentes': 1, 'atendidos': 3, 'cancelados': 1, 'liberados': 1, 'sin_cierre': 2, 'tasa': 0.25}
    assert data['evolucion'][0]['mes'] == '2026-11'
    assert data['profesionales'][0]['profesional_id'] == contexto.profesionales[1]
    assert 'Ana Prueba' not in r.text


@pytest.mark.parametrize('rol,codigo', [('administrador', 200), ('recepcion', 403), ('profesional', 403), ('paciente', 403), ('administrativo', 403), (None, 401)])
async def test_permisos(contexto, rol, codigo):
    assert (await consultar(contexto, rol=rol)).status_code == codigo


@pytest.mark.parametrize('query', ['desde=2026-12-01&hasta=2026-11-01', 'desde=no&hasta=2026-11-01', 'desde=2026-11-01&hasta=2026-11-30&consultorio_id=2', 'desde=2026-11-01&hasta=2026-11-30&profesional_id=0'])
async def test_filtros_invalidos(contexto, query):
    assert (await consultar(contexto, query)).status_code == 422


async def test_limites_locales_evolucion_y_profesional_ajeno(contexto, sesiones):
    zona = AHORA.tzinfo
    for fecha, estado in [(datetime(2026, 10, 31, 23, 30, tzinfo=zona), 'ausente'),
                          (datetime(2026, 11, 1, 0, 0, tzinfo=zona), 'atendido'),
                          (AHORA, 'ausente')]:
        await registrar_turno(sesiones, contexto, inicio=fecha, estado=estado, historial=False)
    r = await consultar(contexto, 'desde=2026-10-31&hasta=2026-11-06')
    assert r.status_code == 200
    assert [(m['mes'], m['ausentes'], m['atendidos']) for m in r.json()['evolucion']] == [('2026-10', 1, 0), ('2026-11', 1, 1)]
    r = await consultar(contexto, 'desde=2026-11-01&hasta=2026-11-06')
    assert r.json()['resumen']['tasa'] == 0.5
    ajeno = await consultar(contexto, f'desde=2026-10-31&hasta=2026-11-06&profesional_id={contexto.profesionales[2]}')
    assert ajeno.status_code == 200
    assert ajeno.json()['resumen']['tasa'] is None
    assert ajeno.json()['profesionales'] == []
