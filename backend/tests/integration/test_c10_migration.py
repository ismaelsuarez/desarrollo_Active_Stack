"""Contratos de persistencia de autorizaciones de sobreturno."""
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic, base_temporal
from tests.integration.test_c07_migration import AHORA, legado
from tests.integration.test_account_models import crear_cuenta
from tests.integration.fabricas import crear_profesional

pytestmark = pytest.mark.integration


async def test_autorizaciones_se_crean_y_eliminan_con_migracion():
    async with base_temporal() as url:
        alembic(url, "upgrade", "0010_confirmation_tokens")
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT to_regclass('autorizacion_sobreturno')")) is None
        alembic(url, "upgrade", "head")
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT to_regclass('autorizacion_sobreturno')")) == "autorizacion_sobreturno"
        alembic(url, "downgrade", "0010_confirmation_tokens")
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT to_regclass('autorizacion_sobreturno')")) is None
        await engine.dispose()


async def test_autorizacion_persiste_para_turno_y_actor_del_consultorio(engine, sesiones):
    usuario_id = await crear_cuenta(sesiones)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
        resultado = (await conexion.execute(text("""
            INSERT INTO autorizacion_sobreturno
                (consultorio_id, turno_id, autorizado_por_id, autorizado_en, motivo, avisado_en)
            VALUES (1, :turno, :usuario, :ahora, 'Urgencia', :ahora)
            RETURNING motivo, respuesta
        """), {"turno": turno_id, "usuario": usuario_id, "ahora": AHORA})).one()
        assert resultado == ("Urgencia", None)


@pytest.mark.parametrize("cambio", ["duplicado", "respuesta_invalida", "motivo_vacio", "actor_ajeno"])
async def test_autorizacion_rechaza_invariantes_invalidas(engine, sesiones, cambio):
    usuario_id = await crear_cuenta(sesiones)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
        if cambio == "duplicado":
            await conexion.execute(text("""
                INSERT INTO autorizacion_sobreturno
                    (consultorio_id, turno_id, autorizado_por_id, autorizado_en, motivo, avisado_en)
                VALUES (1, :turno, :usuario, :ahora, 'Urgencia', :ahora)
            """), {"turno": turno_id, "usuario": usuario_id, "ahora": AHORA})
    async with engine.begin() as conexion:
        with pytest.raises(IntegrityError):
            await conexion.execute(text("""
                INSERT INTO autorizacion_sobreturno
                    (consultorio_id, turno_id, autorizado_por_id, autorizado_en, motivo, avisado_en, respuesta)
                VALUES (1, :turno, :usuario, :ahora, :motivo, :ahora, :respuesta)
            """), {"turno": turno_id, "usuario": 999999 if cambio == "actor_ajeno" else usuario_id,
                    "ahora": AHORA, "motivo": "  " if cambio == "motivo_vacio" else "Urgencia",
                    "respuesta": "desconocida" if cambio == "respuesta_invalida" else None})


async def test_repositorio_aisla_autorizacion_por_consultorio(engine, sesiones):
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    usuario_id = await crear_cuenta(sesiones)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
        await conexion.execute(text("""
            INSERT INTO autorizacion_sobreturno
                (consultorio_id, turno_id, autorizado_por_id, autorizado_en, motivo, avisado_en)
            VALUES (1, :turno, :usuario, :ahora, 'Urgencia', :ahora)
        """), {"turno": turno_id, "usuario": usuario_id, "ahora": AHORA})
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        assert (await unidad.sobreturnos.obtener(1, turno_id)).motivo == "Urgencia"
        assert await unidad.sobreturnos.obtener(2, turno_id) is None


async def test_repositorio_guarda_autorizacion_en_transaccion(engine, sesiones):
    from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
    usuario_id = await crear_cuenta(sesiones)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        await unidad.sobreturnos.agregar(1, turno_id, usuario_id, AHORA, "Urgencia")
    async with UnidadDeTrabajoSQL(sesiones) as unidad:
        autorizacion = await unidad.sobreturnos.obtener(1, turno_id)
        assert autorizacion.autorizado_por_id == usuario_id
        assert autorizacion.avisado_en == AHORA


async def test_autorizacion_no_acepta_actor_de_otro_consultorio(engine, sesiones):
    await crear_cuenta(sesiones)
    await crear_profesional(engine, consultorio_id=2, box_id=2)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
        otro_actor = await conexion.scalar(text("""
            INSERT INTO usuario (consultorio_id,nombre_usuario,email,password_hash,rol,creado_en,actualizado_en)
            VALUES (2,'otro','otro@example.test','hash','recepcion',:ahora,:ahora) RETURNING id
        """), {"ahora": AHORA})
    async with engine.begin() as conexion:
        with pytest.raises(IntegrityError):
            await conexion.execute(text("""
                INSERT INTO autorizacion_sobreturno
                    (consultorio_id, turno_id, autorizado_por_id, autorizado_en, motivo, avisado_en)
                VALUES (1, :turno, :usuario, :ahora, 'Urgencia', :ahora)
            """), {"turno": turno_id, "usuario": otro_actor, "ahora": AHORA})
