from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.infrastructure.db.agenda_turnos import RepositorioAgendaTurnosSQL
from tests.integration.c07_support import INICIO, preparar_escenario

pytestmark = pytest.mark.integration


@pytest.fixture
async def escenario(sesiones, url_base):
    return await preparar_escenario(sesiones, url_base)


async def test_public_configuration_projects_actual_limits_and_scopes(escenario, sesiones):
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE consultorio SET telefono='1198765432', dias_anticipacion_maxima=17, max_turnos_activos_paciente=4 WHERE id=1"))
        await sesion.commit()
        config = await RepositorioAgendaTurnosSQL(sesion).obtener_configuracion(1)
        assert (config.telefono, config.dias_anticipacion_maxima, config.max_turnos_activos_paciente) == ('1198765432', 17, 4)
        otro = await RepositorioAgendaTurnosSQL(sesion).obtener_configuracion(2)
        assert (otro.telefono, otro.dias_anticipacion_maxima, otro.max_turnos_activos_paciente) == ('1122334455', 60, 2)
        assert await RepositorioAgendaTurnosSQL(sesion).obtener_configuracion(99999) is None


async def test_public_catalogues_are_minimal_without_session_and_scoped(escenario):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        consultorio = await client.get('/api/v1/publico/consultorio')
        assert consultorio.status_code == 200
        assert consultorio.json() == {'nombre': 'Consultorio Centro', 'direccion': 'Av. Corrientes 1234',
                                      'telefono': '1122334455', 'zona_horaria': 'America/Argentina/Buenos_Aires'}
        prestaciones = await client.get('/api/v1/publico/prestaciones')
        assert prestaciones.status_code == 200
        assert prestaciones.json() == [{'id': escenario.prestaciones[1], 'nombre': 'Consulta', 'duracion_min': 30}]
        profesionales = await client.get('/api/v1/publico/profesionales')
        assert profesionales.status_code == 200
        assert profesionales.json() == [{'id': escenario.profesionales[1], 'nombre': 'Patricia Dental'}]


@pytest.mark.parametrize('ruta', ['consultorio', 'prestaciones', 'profesionales'])
async def test_public_catalogues_reject_tenant_query_and_hide_inactive(escenario, sesiones, ruta):
    async with sesiones() as sesion:
        await sesion.execute(text('UPDATE prestacion SET activa=false WHERE consultorio_id=1'))
        await sesion.execute(text('UPDATE profesional SET activo=false WHERE consultorio_id=1'))
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        rejected = await client.get(f'/api/v1/publico/{ruta}?consultorio_id=2')
        assert rejected.status_code == 422
        result = await client.get(f'/api/v1/publico/{ruta}')
        assert result.status_code == 200
        if ruta != 'consultorio':
            assert result.json() == []


def consulta_disponibilidad(escenario, **extras):
    return {'profesional_id': escenario.profesionales[1], 'prestacion_id': escenario.prestaciones[1],
            'fecha': INICIO.date().isoformat(), **extras}


async def test_availability_excludes_real_booking_and_global_block_and_has_minimal_intervals(escenario, sesiones):
    async with sesiones() as sesion:
        await sesion.execute(text("INSERT INTO bloqueo_agenda (consultorio_id,profesional_id,tipo,inicio,fin,motivo,creado_por_id,creado_en) VALUES(1,NULL,'feriado',:inicio,:fin,'feriado',:usuario,:inicio)"),
                             {'inicio': INICIO + timedelta(hours=1), 'fin': INICIO + timedelta(hours=1, minutes=30),
                              'usuario': escenario.usuarios[1, 'recepcion']})
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        assert (await client.post('/api/v1/turnos', headers=escenario.headers(), json=escenario.payload())).status_code == 201
        response = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario))
    assert response.status_code == 200, response.text
    intervalos = response.json()
    assert {'inicio': '2026-11-09T09:00:00-03:00', 'fin': '2026-11-09T09:30:00-03:00'} in intervalos
    assert {'inicio': '2026-11-09T10:30:00-03:00', 'fin': '2026-11-09T11:00:00-03:00'} in intervalos
    assert not any(i['inicio'] in ['2026-11-09T09:45:00-03:00', '2026-11-09T10:00:00-03:00',
                                  '2026-11-09T10:45:00-03:00', '2026-11-09T11:00:00-03:00'] for i in intervalos)
    assert all(set(i) == {'inicio', 'fin'} for i in intervalos)


@pytest.mark.parametrize('extras,codigo', [({'consultorio_id': 2}, 422), ({'fecha': 'no-fecha'}, 422),
    ({'profesional_id': 99999}, 404), ({'prestacion_id': 99999}, 404), ({'profesional_id': 0}, 422)])
async def test_availability_rejects_invalid_query_or_missing_references(escenario, extras, codigo):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        response = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario, **extras))
    assert response.status_code == codigo


async def test_four_routes_share_origin_quota_ignore_untrusted_forwarded_and_renew(escenario):
    from app.application.services.limite_publico import LimitePublico
    escenario.app.state.limite_publico = LimitePublico(cuota=3)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, client=('192.0.2.1', 1234)), base_url='http://test') as client:
        for ruta in ['consultorio', 'profesionales', 'prestaciones']:
            assert (await client.get(f'/api/v1/publico/{ruta}')).status_code == 200
        response = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario), headers={'X-Forwarded-For': '203.0.113.5'})
        assert response.status_code == 429
        assert response.headers['Retry-After'] == '60'
        escenario.reloj.avanzar(timedelta(seconds=60))
        assert (await client.get('/api/v1/publico/consultorio')).status_code == 200
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, client=('192.0.2.2', 1234)), base_url='http://test') as otro:
        assert (await otro.get('/api/v1/publico/consultorio')).status_code == 200


async def test_public_logs_and_responses_do_not_echo_private_query_or_account(escenario, caplog):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        for ruta in ['consultorio', 'profesionales', 'prestaciones', 'disponibilidad']:
            response = await client.get(f'/api/v1/publico/{ruta}', params={'consultorio_id': 'privado@example.test'})
            assert response.status_code == 422
            assert 'privado@example.test' not in response.text
    assert 'privado@example.test' not in caplog.text


@pytest.mark.parametrize('estado,ocupado', [('pendiente', True), ('confirmado', True), ('cancelado', False), ('liberado', False)])
async def test_availability_observes_overbooking_and_released_states(escenario, sesiones, estado, ocupado):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        creado = await client.post('/api/v1/turnos', headers=escenario.headers(), json=escenario.payload())
        assert creado.status_code == 201
        async with sesiones() as sesion:
            await sesion.execute(text('UPDATE turno SET estado=CAST(:estado AS estado_turno),es_sobreturno=true WHERE id=:id'),
                                 {'estado': estado, 'id': creado.json()['id']})
            await sesion.commit()
        response = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario))
    assert response.status_code == 200
    assert any(i['inicio'] == '2026-11-09T10:00:00-03:00' for i in response.json()) is not ocupado


@pytest.mark.parametrize('modo', ['ajeno', 'inactivo', 'sin_bloques', 'fuera_horizonte'])
async def test_public_reference_visibility_and_empty_days(escenario, sesiones, modo):
    query = consulta_disponibilidad(escenario)
    async with sesiones() as sesion:
        if modo == 'inactivo':
            await sesion.execute(text('UPDATE profesional SET activo=false WHERE id=:id'), {'id': escenario.profesionales[1]})
        elif modo == 'sin_bloques':
            await sesion.execute(text('DELETE FROM horario_semanal WHERE consultorio_id=1'))
        elif modo == 'ajeno':
            query['profesional_id'] = escenario.profesionales[2]
        else:
            query['fecha'] = (escenario.reloj.ahora().date() + timedelta(days=61)).isoformat()
        await sesion.commit()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        response = await client.get('/api/v1/publico/disponibilidad', params=query)
    assert response.status_code == (404 if modo in ['ajeno', 'inactivo'] else 200)
    if response.status_code == 200:
        assert response.json() == []


@pytest.mark.parametrize('duracion', [30, 45])
async def test_alternatives_order_limit_duration_and_current_turn_exclusion(escenario, sesiones, duracion):
    from app.application.use_cases.consultar_disponibilidad import ConsultarDisponibilidad
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    servicio = ConsultarDisponibilidad(lambda: UnidadDeTrabajoSQL(sesiones), escenario.reloj)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        creado = await client.post('/api/v1/turnos', headers=escenario.headers(), json=escenario.payload())
        assert creado.status_code == 201
    alternativas = await servicio.alternativas(1, escenario.profesionales[1], escenario.prestaciones[1], INICIO,
                                              duracion_min=duracion)
    assert [i.inicio for i in alternativas] == [INICIO + timedelta(minutes=m) for m in (30, 45, 60)]
    assert all(i.fin - i.inicio == timedelta(minutes=duracion) for i in alternativas)
    propias = await servicio.alternativas(1, escenario.profesionales[1], escenario.prestaciones[1], INICIO,
                                         duracion_min=duracion, excluir_id=creado.json()['id'])
    assert propias[0].inicio == INICIO


async def test_alternatives_empty_at_horizon_or_no_open_blocks(escenario, sesiones):
    from app.application.use_cases.consultar_disponibilidad import ConsultarDisponibilidad
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    servicio = ConsultarDisponibilidad(lambda: UnidadDeTrabajoSQL(sesiones), escenario.reloj)
    assert await servicio.alternativas(1, escenario.profesionales[1], escenario.prestaciones[1], INICIO + timedelta(days=100)) == []
    async with sesiones() as sesion:
        await sesion.execute(text('DELETE FROM horario_semanal WHERE consultorio_id=1'))
        await sesion.commit()
    assert await servicio.alternativas(1, escenario.profesionales[1], escenario.prestaciones[1], INICIO) == []


async def test_agenda_interval_queries_include_partial_overlaps_and_exclude_outside(escenario, sesiones):
    from app.infrastructure.db.models import BloqueoAgendaModel
    async with sesiones() as sesion:
        for cid, pid, delta in [(1, None, -15), (1, escenario.profesionales[1], 15),
                                (1, None, 90), (2, None, 0)]:
            sesion.add(BloqueoAgendaModel(consultorio_id=cid, profesional_id=pid, tipo='bloqueo',
                inicio=INICIO + timedelta(minutes=delta), fin=INICIO + timedelta(minutes=delta + 30),
                creado_por_id=escenario.usuarios[cid, 'recepcion'], creado_en=escenario.reloj.ahora()))
        await sesion.commit()
        repo = RepositorioAgendaTurnosSQL(sesion)
        assert await repo.bloqueos(1, escenario.profesionales[1], desde=INICIO, hasta=INICIO + timedelta(minutes=30)) == [
            (INICIO - timedelta(minutes=15), INICIO + timedelta(minutes=15)),
            (INICIO + timedelta(minutes=15), INICIO + timedelta(minutes=45)),
        ]
        assert await repo.bloqueos(1, escenario.profesionales[1], desde=INICIO + timedelta(hours=4), hasta=INICIO + timedelta(hours=5)) == []


async def test_availability_does_not_query_database_for_each_candidate(escenario, sesiones, engine):
    from sqlalchemy import event
    consultas = []

    def registrar(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith('SELECT'):
            consultas.append(statement)

    cantidades, intervalos = [], []
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        for grilla in (15, 5):
            async with sesiones() as sesion:
                await sesion.execute(text('UPDATE consultorio SET minutos_granularidad=:grilla WHERE id=1'), {'grilla': grilla})
                await sesion.commit()
            consultas.clear()
            event.listen(engine.sync_engine, 'before_cursor_execute', registrar)
            try:
                response = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario))
            finally:
                event.remove(engine.sync_engine, 'before_cursor_execute', registrar)
            assert response.status_code == 200
            cantidades.append(len(consultas))
            intervalos.append(len(response.json()))
    assert intervalos[1] > intervalos[0] > 0
    assert cantidades[0] == cantidades[1]
    assert cantidades[0] <= 8


@pytest.mark.parametrize('fecha', ['9999-12-31', '2027-01-06'])
async def test_valid_query_date_beyond_horizon_returns_empty_without_overflow(escenario, fecha):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app, raise_app_exceptions=False), base_url='http://test') as client:
        respuesta = await client.get('/api/v1/publico/disponibilidad', params=consulta_disponibilidad(escenario, fecha=fecha))
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == []
