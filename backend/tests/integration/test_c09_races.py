"""Concurrencia real: cada solicitud mantiene su propia conexión PostgreSQL."""
import asyncio
from datetime import timedelta

import httpx
import pytest
from sqlalchemy import text

from app.application.services.token_service import AuthTokenService
from app.domain.entities.auth import Principal, RolUsuario
from app.infrastructure.db.cuentas import RepositorioCuentas
from app.infrastructure.db.models import PacienteModel
from app.infrastructure.db.repositorios import RepositorioTurnosSQL
from app.infrastructure.db.vinculacion import RepositorioVinculacionSQL
from tests.integration.c07_support import INICIO
from tests.integration.test_c09_patient_booking import escenario, online

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('desplazamiento', [0, 15])
async def test_two_accounts_compete_for_one_slot_with_real_connections(escenario, sesiones, monkeypatch, desplazamiento):
    uid = escenario.usuarios[1, 'administrativo']
    async with sesiones() as sesion:
        await sesion.execute(text("UPDATE usuario SET rol='paciente',email_verificado=true,aviso_privacidad_aceptado_en=:ahora,aviso_privacidad_version='prueba' WHERE id=:id"), {'id': uid, 'ahora': escenario.reloj.ahora()})
        sesion.add(PacienteModel(consultorio_id=1, usuario_id=uid, nombre='Segunda', apellido='Sintética',
            dni='87654321', creado_en=escenario.reloj.ahora(), actualizado_en=escenario.reloj.ahora()))
        await sesion.commit()
    token = AuthTokenService(escenario.reloj, 'j' * 32).emitir_access_token(Principal(uid, 1, RolUsuario.PACIENTE))
    barrera = asyncio.Barrier(2)
    pids = set()
    original = RepositorioTurnosSQL.guardar

    async def guardar(repo, nuevo):
        pids.add(await repo._sesion.scalar(text('SELECT pg_backend_pid()')))
        await barrera.wait()
        return await original(repo, nuevo)

    monkeypatch.setattr(RepositorioTurnosSQL, 'guardar', guardar)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        respuestas = await asyncio.wait_for(asyncio.gather(
            client.post('/api/v1/turnos', headers=escenario.headers('paciente'), json=online(escenario)),
            client.post('/api/v1/turnos', headers={'Authorization': f'Bearer {token}'},
                        json=online(escenario, INICIO + timedelta(minutes=desplazamiento)))), 15)
    assert len(pids) == 2
    assert sorted(r.status_code for r in respuestas) == [201, 409]
    ganador = next(r.json() for r in respuestas if r.status_code == 201)
    perdedor = next(r.json()['detail'] for r in respuestas if r.status_code == 409)
    from datetime import datetime
    inicio, fin = (datetime.fromisoformat(ganador[k]) for k in ['inicio', 'fin'])
    assert len(perdedor['alternativas']) == 3
    for alternativa in perdedor['alternativas']:
        assert set(alternativa) == {'inicio', 'fin'}
        assert datetime.fromisoformat(alternativa['inicio']) >= fin or datetime.fromisoformat(alternativa['fin']) <= inicio
    async with sesiones() as sesion:
        assert await sesion.scalar(text('SELECT count(*) FROM turno')) == 1
        assert await sesion.scalar(text('SELECT count(*) FROM turno_historial')) == 1


async def esperar_lock_real(sesiones, esperado, bloqueador):
    async with asyncio.timeout(8):
        async with sesiones() as observador:
            while True:
                bloqueadores = await observador.scalar(text('SELECT pg_blocking_pids(:pid)'), {'pid': esperado})
                if bloqueador in bloqueadores:
                    return


@pytest.mark.parametrize('primera', ['reserva', 'desvinculacion'])
async def test_online_booking_and_unlink_serialize_on_patient_row(escenario, sesiones, monkeypatch, primera):
    bloqueo, continuar, segundo_intenta = asyncio.Event(), asyncio.Event(), asyncio.Event()
    conexiones = {}
    obtener = RepositorioCuentas.ficha_de_usuario
    ficha = RepositorioVinculacionSQL.bloquear_ficha

    async def instrumentar(nombre, repo, original, *args):
        conexiones[nombre] = await repo.sesion.scalar(text('SELECT pg_backend_pid()'))
        if nombre != primera:
            segundo_intenta.set()
        resultado = await original(repo, *args)
        if nombre == primera:
            bloqueo.set()
            await continuar.wait()
        return resultado

    async def reserva(repo, *args):
        return await instrumentar('reserva', repo, obtener, *args)

    async def desvinculacion(repo, *args):
        return await instrumentar('desvinculacion', repo, ficha, *args)

    monkeypatch.setattr(RepositorioCuentas, 'ficha_de_usuario', reserva)
    monkeypatch.setattr(RepositorioVinculacionSQL, 'bloquear_ficha', desvinculacion)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url='http://test') as client:
        async def ejecutar(nombre):
            if nombre == 'reserva':
                return await client.post('/api/v1/turnos', headers=escenario.headers('paciente'), json=online(escenario))
            return await client.post(f'/api/v1/pacientes/{escenario.pacientes[1]}/desvincular',
                headers=escenario.headers(), json={'motivo': 'Verificación sintética'})

        segunda = 'desvinculacion' if primera == 'reserva' else 'reserva'
        una = asyncio.create_task(ejecutar(primera))
        await asyncio.wait_for(bloqueo.wait(), 8)
        dos = asyncio.create_task(ejecutar(segunda))
        try:
            await asyncio.wait_for(segundo_intenta.wait(), 8)
            assert conexiones[primera] != conexiones[segunda]
            await esperar_lock_real(sesiones, conexiones[segunda], conexiones[primera])
        finally:
            continuar.set()
        resultados = dict(zip([primera, segunda], await asyncio.wait_for(asyncio.gather(una, dos), 15)))
        assert resultados['desvinculacion'].status_code == 200
        assert resultados['reserva'].status_code == (201 if primera == 'reserva' else 403)
        # Un JWT anterior no recupera autoridad al terminar la desvinculación.
        respuesta = await client.get('/api/v1/turnos', headers=escenario.headers('paciente'))
        assert respuesta.status_code == 200
        assert respuesta.json() == []
    async with sesiones() as sesion:
        assert await sesion.scalar(text('SELECT usuario_id FROM paciente WHERE id=:id'), {'id': escenario.pacientes[1]}) is None
        assert await sesion.scalar(text('SELECT count(*) FROM turno')) == (1 if primera == 'reserva' else 0)
        assert await sesion.scalar(text('SELECT count(*) FROM turno_historial')) == (1 if primera == 'reserva' else 0)
