"""Tokens de confirmación sin cuenta: contrato PostgreSQL de C-16."""
import subprocess

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.db.models import TokenUsuarioModel
from tests.integration.c07_support import AHORA, INICIO, preparar_escenario
from tests.integration.conftest import alembic, base_temporal
from tests.integration.test_c07_migration import legado

pytestmark = pytest.mark.integration


async def turno_para_token(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        respuesta = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert respuesta.status_code == 201, respuesta.text
    return escenario, respuesta.json()["id"]


def token(tid, **cambios):
    return TokenUsuarioModel(**(dict(
        consultorio_id=1, usuario_id=None, turno_id=tid, ciclo=1,
        tipo="confirmar_turno", token_hash="hash-confirmacion", expira_en=INICIO,
        creado_en=AHORA,
    ) | cambios))


async def test_confirmation_token_without_account_keeps_turn_and_cycle(sesiones, url_base):
    _, turno_id = await turno_para_token(sesiones, url_base)
    async with sesiones() as sesion:
        sesion.add(token(turno_id))
        await sesion.commit()
    async with sesiones() as sesion:
        guardado = await sesion.scalar(select(TokenUsuarioModel))
        assert (guardado.usuario_id, guardado.turno_id, guardado.ciclo) == (None, turno_id, 1)
        assert guardado.expira_en == INICIO


@pytest.mark.parametrize("cambios", [
    {"turno_id": None}, {"ciclo": None}, {"ciclo": 0}, {"ciclo": -1},
    {"tipo": "verificar_email"}, {"tipo": "recuperar_password"},
])
async def test_confirmation_token_requires_a_turn(sesiones, url_base, cambios):
    _, tid = await turno_para_token(sesiones, url_base)
    async with sesiones() as sesion:
        sesion.add(token(tid, **cambios))
        with pytest.raises(IntegrityError) as error:
            await sesion.commit()
        assert error.value.orig.sqlstate == "23514"


@pytest.mark.parametrize("tipo", ["verificar_email", "recuperar_password", "confirmar_turno"])
async def test_token_with_account_preserves_its_purpose(sesiones, url_base, tipo):
    escenario, tid = await turno_para_token(sesiones, url_base)
    async with sesiones() as sesion:
        sesion.add(token(tid if tipo == "confirmar_turno" else None, tipo=tipo,
            usuario_id=escenario.usuarios[1, "paciente"], ciclo=1 if tipo == "confirmar_turno" else None))
        await sesion.commit()
    async with sesiones() as sesion:
        guardado = await sesion.scalar(select(TokenUsuarioModel))
        assert (guardado.tipo, guardado.usuario_id) == (tipo, escenario.usuarios[1, "paciente"])


async def test_confirmation_token_keeps_fk_and_hash_uniqueness(sesiones, url_base):
    _, tid = await turno_para_token(sesiones, url_base)
    async with sesiones() as sesion:
        sesion.add(token(tid))
        await sesion.commit()
    for cambios, sqlstate in [({"turno_id": 999999, "token_hash": "otro"}, "23503"), ({}, "23505")]:
        async with sesiones() as sesion:
            sesion.add(token(tid, **cambios))
            with pytest.raises(IntegrityError) as error:
                await sesion.commit()
            assert error.value.orig.sqlstate == sqlstate


async def test_migration_downgrade_preflight_keeps_accountless_token_and_schema():
    async with base_temporal() as url:
        alembic(url, "upgrade", "head")
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.begin() as conexion:
                tid = await legado(conexion)
                await conexion.execute(text("""INSERT INTO token_usuario
                    (consultorio_id,usuario_id,turno_id,ciclo,tipo,token_hash,expira_en,creado_en)
                    VALUES (1,NULL,:tid,1,'confirmar_turno','sin-cuenta',:inicio,:ahora)"""),
                    {"tid": tid, "inicio": INICIO, "ahora": AHORA})
            with pytest.raises(subprocess.CalledProcessError) as error:
                alembic(url, "downgrade", "0009_notifications_outbox_sweep")
            assert "tokens de confirmación sin cuenta" in error.value.stderr
            async with engine.connect() as conexion:
                assert await conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0010_confirmation_tokens"
                assert await conexion.scalar(text("SELECT token_hash FROM token_usuario")) == "sin-cuenta"
                assert await conexion.scalar(text("SELECT is_nullable FROM information_schema.columns WHERE table_name='token_usuario' AND column_name='usuario_id'")) == "YES"
                assert await conexion.scalar(text("SELECT count(*) FROM pg_constraint WHERE conname='ck_token_usuario_proposito_coherente'")) == 1
        finally:
            await engine.dispose()


async def insertar_usuario_migracion(conexion):
    return await conexion.scalar(text("""INSERT INTO usuario
        (consultorio_id,nombre_usuario,email,password_hash,rol,creado_en,actualizado_en)
        VALUES (1,'migracion','migracion@example.test','hash','recepcion',:ahora,:ahora) RETURNING id"""), {"ahora": AHORA})


async def test_upgrade_preflight_rejects_incomplete_legacy_confirmation_without_mutation():
    async with base_temporal() as url:
        alembic(url, "upgrade", "0009_notifications_outbox_sweep")
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.begin() as conexion:
                tid = await legado(conexion)
                uid = await insertar_usuario_migracion(conexion)
                await conexion.execute(text("""INSERT INTO token_usuario
                    (consultorio_id,usuario_id,turno_id,tipo,token_hash,expira_en,creado_en)
                    VALUES (1,:uid,:tid,'confirmar_turno','legado-incompleto',:inicio,:ahora)"""),
                    {"uid": uid, "tid": tid, "inicio": INICIO, "ahora": AHORA})
            with pytest.raises(subprocess.CalledProcessError) as error:
                alembic(url, "upgrade", "head")
            assert "tokens de confirmación históricos incompatibles" in error.value.stderr
            async with engine.connect() as conexion:
                assert await conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0009_notifications_outbox_sweep"
                assert await conexion.scalar(text("SELECT ciclo FROM token_usuario")) is None
                assert await conexion.scalar(text("SELECT token_hash FROM token_usuario")) == "legado-incompleto"
                assert await conexion.scalar(text("SELECT is_nullable FROM information_schema.columns WHERE table_name='token_usuario' AND column_name='usuario_id'")) == "NO"
        finally:
            await engine.dispose()


async def test_migration_round_trip_preserves_account_tokens_and_turn_constraints():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from tests.integration.conftest import BACKEND
    from app.infrastructure.db.models import RESTRICCION_SIN_SOLAPAMIENTO

    assert ScriptDirectory.from_config(Config(BACKEND / "alembic.ini")).get_heads() == ["0010_confirmation_tokens"]
    async with base_temporal() as url:
        alembic(url, "upgrade", "0009_notifications_outbox_sweep")
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.begin() as conexion:
                tid = await legado(conexion)
                uid = await insertar_usuario_migracion(conexion)
                await conexion.execute(text("""INSERT INTO token_usuario
                    (consultorio_id,usuario_id,turno_id,ciclo,tipo,token_hash,expira_en,creado_en)
                    VALUES (1,:uid,NULL,NULL,'verificar_email','cuenta-hash',:inicio,:ahora),
                           (1,:uid,:tid,1,'confirmar_turno','turno-hash',:inicio,:ahora)"""),
                    {"uid": uid, "tid": tid, "inicio": INICIO, "ahora": AHORA})
                anterior = (await conexion.execute(text("SELECT row_to_json(t) FROM token_usuario t ORDER BY id"))).scalars().all()
            for direccion, destino in [("upgrade", "head"), ("downgrade", "0009_notifications_outbox_sweep"), ("upgrade", "head")]:
                alembic(url, direccion, destino)
                async with engine.connect() as conexion:
                    assert (await conexion.execute(text("SELECT row_to_json(t) FROM token_usuario t ORDER BY id"))).scalars().all() == anterior
                    assert await conexion.scalar(text("SELECT count(*) FROM pg_constraint WHERE conrelid='turno'::regclass AND conname=:nombre"), {"nombre": RESTRICCION_SIN_SOLAPAMIENTO}) == 1
        finally:
            await engine.dispose()
