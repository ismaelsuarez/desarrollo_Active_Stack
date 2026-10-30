from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.models import ConsultorioModel
from app.infrastructure.db.sesion import crear_engine
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

pytestmark = pytest.mark.integration

RELOJ = RelojSimulado(datetime(2026, 10, 30, 12, 0, 0, tzinfo=timezone.utc))


async def test_crear_engine_configura_prepared_statement_cache_size(url_base: str):
    engine = crear_engine(url_base)
    async with engine.connect() as conn:
        raw_conn = await conn.get_raw_connection()
        # Verificar que el cache de sentencias preparadas está deshabilitado para PgBouncer/Neon
        assert raw_conn.dbapi_connection._prepared_statement_cache is None
    await engine.dispose()


async def test_unidad_de_trabajo_commit_exitoso(sesiones: async_sessionmaker[AsyncSession]):
    uow = UnidadDeTrabajoSQL(sesiones)
    async with uow:
        consultorio = ConsultorioModel(
            id=10,
            nombre="Consultorio UOW",
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
        uow._sesion.add(consultorio)

    async with sesiones() as sesion:
        resultado = await sesion.scalar(select(ConsultorioModel).where(ConsultorioModel.id == 10))
        assert resultado is not None
        assert resultado.nombre == "Consultorio UOW"


async def test_unidad_de_trabajo_rollback_ante_excepcion(sesiones: async_sessionmaker[AsyncSession]):
    uow = UnidadDeTrabajoSQL(sesiones)
    with pytest.raises(RuntimeError, match="Error simulado"):
        async with uow:
            consultorio = ConsultorioModel(
                id=20,
                nombre="Consultorio Rollback",
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
            uow._sesion.add(consultorio)
            raise RuntimeError("Error simulado")

    async with sesiones() as sesion:
        resultado = await sesion.scalar(select(ConsultorioModel).where(ConsultorioModel.id == 20))
        assert resultado is None
