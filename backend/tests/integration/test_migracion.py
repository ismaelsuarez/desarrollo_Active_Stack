from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.conftest import BACKEND, alembic, base_temporal

pytestmark = pytest.mark.integration

BUENOS_AIRES = ZoneInfo("America/Argentina/Buenos_Aires")


def hora(horas: int, minutos: int) -> datetime:
    return datetime(2026, 11, 2, horas, minutos, tzinfo=BUENOS_AIRES)


async def columnas(engine: AsyncEngine, tabla: str) -> dict[str, str]:
    async with engine.connect() as conexion:
        filas = await conexion.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :tabla"
            ),
            {"tabla": tabla},
        )
        return {nombre: tipo for nombre, tipo in filas}


async def test_la_migracion_crea_la_extension_btree_gist(engine: AsyncEngine):
    async with engine.connect() as conexion:
        extension = await conexion.scalar(
            text("SELECT extname FROM pg_extension WHERE extname = 'btree_gist'")
        )

    assert extension == "btree_gist"


async def test_la_migracion_crea_el_estado_del_turno_con_seis_valores(
    engine: AsyncEngine,
):
    async with engine.connect() as conexion:
        valores = await conexion.scalars(
            text(
                "SELECT e.enumlabel FROM pg_enum e "
                "JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'estado_turno' ORDER BY e.enumsortorder"
            )
        )

        assert list(valores) == [
            "pendiente",
            "confirmado",
            "ausente",
            "atendido",
            "cancelado",
            "liberado",
        ]


async def test_la_migracion_crea_las_tablas_del_turno(engine: AsyncEngine):
    assert await columnas(engine, "profesional") == {
        "id": "bigint",
        "consultorio_id": "bigint",
        "box_id": "bigint",
        "nombre": "text",
        "apellido": "text",
    }
    assert await columnas(engine, "prestacion") == {
        "id": "bigint",
        "consultorio_id": "bigint",
        "nombre": "text",
        "duracion_min": "integer",
    }
    assert await columnas(engine, "turno") == {
        "id": "bigint",
        "consultorio_id": "bigint",
        "paciente_id": "bigint",
        "profesional_id": "bigint",
        "box_id": "bigint",
        "prestacion_id": "bigint",
        "inicio": "timestamp with time zone",
        "fin": "timestamp with time zone",
        "estado": "USER-DEFINED",
        "es_sobreturno": "boolean",
        "creado_en": "timestamp with time zone",
    }


def test_alembic_tiene_un_unico_head():
    scripts = ScriptDirectory.from_config(Config(str(BACKEND / "alembic.ini")))

    assert scripts.get_heads() == ["0001_turnos_sin_solapamiento"]


INSERTAR_TURNO = text(
    "INSERT INTO turno (consultorio_id, paciente_id, profesional_id, box_id, "
    "prestacion_id, inicio, fin) "
    "VALUES (1, 1, :profesional_id, 1, :prestacion_id, :inicio, :fin)"
)


async def profesional_y_prestacion(conexion) -> dict[str, int]:
    profesional_id = await conexion.scalar(
        text(
            "INSERT INTO profesional (consultorio_id, box_id, nombre, apellido) "
            "VALUES (1, 1, 'Ana', 'Paz') RETURNING id"
        )
    )
    prestacion_id = await conexion.scalar(
        text(
            "INSERT INTO prestacion (consultorio_id, nombre, duracion_min) "
            "VALUES (1, 'Consulta', 30) RETURNING id"
        )
    )
    return {"profesional_id": profesional_id, "prestacion_id": prestacion_id}


async def test_la_base_rechaza_dos_turnos_solapados_del_mismo_profesional(
    engine: AsyncEngine,
):
    async with engine.connect() as conexion:
        ids = await profesional_y_prestacion(conexion)
        await conexion.execute(
            INSERTAR_TURNO,
            {**ids, "inicio": hora(10, 0), "fin": hora(10, 30)},
        )

        with pytest.raises(IntegrityError) as error:
            await conexion.execute(
                INSERTAR_TURNO,
                {**ids, "inicio": hora(10, 15), "fin": hora(10, 45)},
            )

        assert error.value.orig.sqlstate == "23P01"
        assert "turno_sin_solapamiento" in str(error.value.orig)
        await conexion.rollback()


async def test_la_base_acepta_dos_turnos_contiguos(engine: AsyncEngine):
    async with engine.connect() as conexion:
        ids = await profesional_y_prestacion(conexion)
        await conexion.execute(
            INSERTAR_TURNO, {**ids, "inicio": hora(10, 0), "fin": hora(10, 30)}
        )
        await conexion.execute(
            INSERTAR_TURNO, {**ids, "inicio": hora(10, 30), "fin": hora(11, 0)}
        )

        cantidad = await conexion.scalar(text("SELECT count(*) FROM turno"))

        assert cantidad == 2
        await conexion.rollback()


async def test_la_base_rechaza_un_turno_que_termina_antes_de_empezar(
    engine: AsyncEngine,
):
    async with engine.connect() as conexion:
        ids = await profesional_y_prestacion(conexion)

        with pytest.raises(IntegrityError) as error:
            await conexion.execute(
                INSERTAR_TURNO, {**ids, "inicio": hora(10, 30), "fin": hora(10, 0)}
            )

        assert "turno_inicio_antes_de_fin" in str(error.value.orig)
        await conexion.rollback()


async def test_la_base_rechaza_una_prestacion_sin_duracion(engine: AsyncEngine):
    async with engine.connect() as conexion:
        with pytest.raises(IntegrityError) as error:
            await conexion.execute(
                text(
                    "INSERT INTO prestacion (consultorio_id, nombre, duracion_min) "
                    "VALUES (1, 'Sin duración', 0)"
                )
            )

        assert "prestacion_duracion_positiva" in str(error.value.orig)
        await conexion.rollback()


async def test_el_downgrade_elimina_el_esquema_y_conserva_la_extension():
    async with base_temporal() as url:
        alembic(url, "upgrade", "head")

        alembic(url, "downgrade", "base")

        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.connect() as conexion:
            tablas = await conexion.scalars(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name <> 'alembic_version'"
                )
            )
            tipo = await conexion.scalar(
                text("SELECT typname FROM pg_type WHERE typname = 'estado_turno'")
            )
            extension = await conexion.scalar(
                text("SELECT extname FROM pg_extension WHERE extname = 'btree_gist'")
            )
        await engine.dispose()

        assert list(tablas) == []
        assert tipo is None
        assert extension == "btree_gist"

        alembic(url, "upgrade", "head")
