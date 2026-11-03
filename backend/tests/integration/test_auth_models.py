from datetime import datetime, timezone
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import ConsultorioModel, IntentoIngresoModel

pytestmark = pytest.mark.integration

AHORA = datetime(2026, 10, 30, 14, 0, 0, tzinfo=timezone.utc)
RELOJ = RelojSimulado(AHORA)


def crear_consultorio_ejemplo(id: int = 1) -> ConsultorioModel:
    return ConsultorioModel(
        id=id,
        nombre="Consultorio Norte",
        telefono="1122334455",
        direccion="Av. Santa Fe 1234",
        zona_horaria="America/Argentina/Buenos_Aires",
        modo_liberacion="automatico",
        horas_confirmacion=48,
        horas_recordatorio=24,
        horas_liberacion=12,
        horas_limite_paciente=24,
        minutos_granularidad=15,
        dias_anticipacion_maxima=60,
        max_turnos_activos_paciente=2,
        activo=True,
        creado_en=RELOJ.ahora(),
        actualizado_en=RELOJ.ahora(),
    )


async def test_crear_intento_ingreso_con_origen_valido(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=10)
        sesion.add(consultorio)
        await sesion.flush()

        intento = IntentoIngresoModel(
            consultorio_id=consultorio.id,
            identificador_hash="hash-admin-123",
            origen_hash="hash-ip-192-168-1-1",
            creado_en=RELOJ.ahora(),
        )
        sesion.add(intento)
        await sesion.commit()

        recuperado = await sesion.scalar(
            select(IntentoIngresoModel).where(IntentoIngresoModel.id == intento.id)
        )
        assert recuperado is not None
        assert recuperado.consultorio_id == 10
        assert recuperado.identificador_hash == "hash-admin-123"
        assert recuperado.origen_hash == "hash-ip-192-168-1-1"
        assert recuperado.creado_en == AHORA


async def test_crear_intento_ingreso_con_origen_nulo(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        consultorio = crear_consultorio_ejemplo(id=11)
        sesion.add(consultorio)
        await sesion.flush()

        intento = IntentoIngresoModel(
            consultorio_id=consultorio.id,
            identificador_hash="hash-admin-anon",
            origen_hash=None,
            creado_en=RELOJ.ahora(),
        )
        sesion.add(intento)
        await sesion.commit()

        recuperado = await sesion.scalar(
            select(IntentoIngresoModel).where(IntentoIngresoModel.id == intento.id)
        )
        assert recuperado is not None
        assert recuperado.origen_hash is None


async def test_intento_ingreso_rechaza_consultorio_inexistente(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        intento = IntentoIngresoModel(
            consultorio_id=999999,
            identificador_hash="hash-admin-fk",
            origen_hash=None,
            creado_en=RELOJ.ahora(),
        )
        sesion.add(intento)
        with pytest.raises(IntegrityError):
            await sesion.commit()


async def test_intento_ingreso_indices_existentes(sesiones: async_sessionmaker[AsyncSession]):
    async with sesiones() as sesion:
        query = text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'intento_ingreso'
            """
        )
        resultado = (await sesion.scalars(query)).all()
        indices = set(resultado)
        assert "ix_intento_ingreso_par" in indices
        assert "ix_intento_ingreso_origen" in indices
        assert "ix_intento_ingreso_creado_en" in indices


async def test_migracion_0003_downgrade_y_upgrade_limpio():
    from tests.integration.conftest import alembic, base_temporal
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    async with base_temporal() as url:
        # Exercise revision 0003 itself, independently of later change heads.
        alembic(url, "upgrade", "0003_auth_core")
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                existe = await conn.scalar(
                    text("SELECT to_regclass('public.intento_ingreso') IS NOT NULL")
                )
                assert existe is True

            alembic(url, "downgrade", "0002_core_models")
            async with engine.connect() as conn:
                existe = await conn.scalar(
                    text("SELECT to_regclass('public.intento_ingreso') IS NOT NULL")
                )
                assert existe is False

            alembic(url, "upgrade", "0003_auth_core")
            async with engine.connect() as conn:
                existe = await conn.scalar(
                    text("SELECT to_regclass('public.intento_ingreso') IS NOT NULL")
                )
                assert existe is True
        finally:
            await engine.dispose()
