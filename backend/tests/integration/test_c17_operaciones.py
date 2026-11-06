"""Bandeja operativa WhatsApp con control de acceso y mínima exposición."""
from datetime import timedelta
import asyncio

import pytest
import httpx
from sqlalchemy import text

from tests.integration.c07_support import AHORA
from tests.integration.test_c15_operations import contexto, get, agregar

pytestmark = pytest.mark.integration


async def test_filtra_whatsapp_preparado_por_urgencia_sin_exponer_contenido(contexto, sesiones):
    async with sesiones() as sesion:
        ids = []
        for cid, fecha in [(1, AHORA + timedelta(hours=2)), (1, AHORA), (2, AHORA)]:
            ids.append(await sesion.scalar(text("""INSERT INTO notificacion
                (consultorio_id,tipo,canal,estado,destinatario,programada_para,intentos,mensaje,enlace_whatsapp)
                VALUES (:cid,'solicitud_confirmacion','whatsapp','preparada','secreto',:fecha,0,'privado','secreto') RETURNING id"""),
                {'cid': cid, 'fecha': fecha}))
        await sesion.commit()
    await agregar(sesiones)
    respuesta = await get(contexto, '/api/v1/notificaciones?canal=whatsapp&estado=preparada')
    assert respuesta.status_code == 200, respuesta.text
    assert [n['id'] for n in respuesta.json()] == [ids[1], ids[0]]
    assert 'secreto' not in respuesta.text and 'privado' not in respuesta.text
    paginada = await get(contexto, '/api/v1/notificaciones?canal=whatsapp&estado=preparada&limit=1&offset=1')
    assert [n['id'] for n in paginada.json()] == [ids[0]]


@pytest.mark.parametrize(('rol', 'esperado'), [('recepcion', 200), ('administrador', 200),
    ('paciente', 403), ('profesional', 403), ('administrativo', 403), (None, 401)])
async def test_canal_respeta_roles(contexto, rol, esperado):
    respuesta = await get(contexto, '/api/v1/notificaciones?canal=whatsapp&estado=preparada', rol)
    assert respuesta.status_code == esperado


async def test_canal_invalido_es_rechazado_y_sin_filtro_conserva_orden(contexto, sesiones):
    primero = await agregar(sesiones)
    segundo = await agregar(sesiones)
    invalida = await get(contexto, '/api/v1/notificaciones?canal=otro')
    assert invalida.status_code == 422
    existente = await get(contexto, '/api/v1/notificaciones')
    assert [fila['id'] for fila in existente.json()] == [segundo, primero]


async def crear_whatsapp(sesiones, cid=1, canal='whatsapp', estado='preparada'):
    async with sesiones() as sesion:
        identificador = await sesion.scalar(text("""INSERT INTO notificacion
            (consultorio_id,tipo,canal,estado,destinatario,programada_para,intentos,mensaje,enlace_whatsapp)
            VALUES (:cid,'solicitud_confirmacion',:canal,:estado,'numero-privado',:fecha,0,'texto-privado','https://wa.me/123') RETURNING id"""),
            {'cid': cid, 'canal': canal, 'estado': estado, 'fecha': AHORA})
        await sesion.commit()
    return identificador


async def test_detalle_whatsapp_devuelve_solo_enlace(contexto, sesiones):
    identificador = await crear_whatsapp(sesiones)
    respuesta = await get(contexto, f'/api/v1/notificaciones/{identificador}/whatsapp')
    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {'id': identificador, 'enlace_whatsapp': 'https://wa.me/123'}
    assert 'texto-privado' not in respuesta.text and 'numero-privado' not in respuesta.text


@pytest.mark.parametrize(('rol', 'esperado'), [('recepcion', 200), ('administrador', 200),
    ('paciente', 403), ('profesional', 403), ('administrativo', 403), (None, 401)])
async def test_detalle_respeta_roles(contexto, sesiones, rol, esperado):
    identificador = await crear_whatsapp(sesiones)
    respuesta = await get(contexto, f'/api/v1/notificaciones/{identificador}/whatsapp', rol)
    assert respuesta.status_code == esperado


@pytest.mark.parametrize(('canal', 'estado'), [('email', 'preparada'), ('whatsapp', 'omitida'),
    ('whatsapp', 'enviada_manual'), ('whatsapp', 'programada')])
async def test_detalle_incompatible_es_conflicto(contexto, sesiones, canal, estado):
    identificador = await crear_whatsapp(sesiones, canal=canal, estado=estado)
    respuesta = await get(contexto, f'/api/v1/notificaciones/{identificador}/whatsapp')
    assert respuesta.status_code == 409
    assert 'texto-privado' not in respuesta.text


async def test_detalle_ajeno_o_ausente_no_revela_datos(contexto, sesiones):
    identificador = await crear_whatsapp(sesiones, cid=2)
    ajeno = await get(contexto, f'/api/v1/notificaciones/{identificador}/whatsapp')
    ausente = await get(contexto, '/api/v1/notificaciones/999999/whatsapp')
    assert ajeno.status_code == ausente.status_code == 404
    assert 'texto-privado' not in ajeno.text and 'numero-privado' not in ajeno.text


async def test_marcar_enviada_registra_actor_y_rechaza_segundo_intento(contexto, sesiones):
    identificador = await crear_whatsapp(sesiones)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as cliente:
        url = f'/api/v1/notificaciones/{identificador}/marcar-enviada'
        primera = await cliente.post(url, headers=contexto.headers())
        segunda = await cliente.post(url, headers=contexto.headers())
    assert primera.status_code == 200, primera.text
    assert segunda.status_code == 409
    async with sesiones() as sesion:
        fila = (await sesion.execute(text('SELECT estado, marcada_enviada_por_id, enviada_en FROM notificacion WHERE id=:id'),
            {'id': identificador})).one()
        assert fila.estado == 'enviada_manual'
        assert fila.marcada_enviada_por_id == contexto.usuarios[1, 'recepcion']
        assert fila.enviada_en == contexto.reloj.ahora()


@pytest.mark.parametrize(('rol', 'esperado'), [('recepcion', 200), ('administrador', 200),
    ('paciente', 403), ('profesional', 403), ('administrativo', 403), (None, 401)])
async def test_marcar_enviada_respeta_roles(contexto, sesiones, rol, esperado):
    identificador = await crear_whatsapp(sesiones)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as cliente:
        respuesta = await cliente.post(f'/api/v1/notificaciones/{identificador}/marcar-enviada',
            headers=contexto.headers(rol) if rol else {})
    assert respuesta.status_code == esperado


@pytest.mark.parametrize(('canal', 'estado'), [('email', 'preparada'), ('whatsapp', 'omitida'),
    ('whatsapp', 'enviada_manual'), ('whatsapp', 'programada')])
async def test_marcar_incompatible_es_conflicto(contexto, sesiones, canal, estado):
    identificador = await crear_whatsapp(sesiones, canal=canal, estado=estado)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as cliente:
        respuesta = await cliente.post(f'/api/v1/notificaciones/{identificador}/marcar-enviada', headers=contexto.headers())
    assert respuesta.status_code == 409


async def test_marca_concurrente_solo_un_operador_gana(contexto, sesiones):
    identificador = await crear_whatsapp(sesiones)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as cliente:
        url = f'/api/v1/notificaciones/{identificador}/marcar-enviada'
        respuestas = await asyncio.gather(cliente.post(url, headers=contexto.headers('recepcion')),
            cliente.post(url, headers=contexto.headers('administrador')))
    assert sorted(respuesta.status_code for respuesta in respuestas) == [200, 409]
    async with sesiones() as sesion:
        fila = (await sesion.execute(text('SELECT marcada_enviada_por_id FROM notificacion WHERE id=:id'),
            {'id': identificador})).one()
        ganador = 'recepcion' if respuestas[0].status_code == 200 else 'administrador'
        assert fila.marcada_enviada_por_id == contexto.usuarios[1, ganador]


async def test_marca_ajena_o_ausente_es_404(contexto, sesiones):
    identificador = await crear_whatsapp(sesiones, cid=2)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=contexto.app), base_url='http://test') as cliente:
        ajena = await cliente.post(f'/api/v1/notificaciones/{identificador}/marcar-enviada', headers=contexto.headers())
        ausente = await cliente.post('/api/v1/notificaciones/999999/marcar-enviada', headers=contexto.headers())
    assert ajena.status_code == ausente.status_code == 404
