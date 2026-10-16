import os
import subprocess
import sys
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.infrastructure.db.sesion import crear_fabrica_de_sesiones

BACKEND = Path(__file__).resolve().parents[2]


def alembic(url: str, *argumentos: str) -> None:
    """Ejecuta Alembic como proceso aparte, igual que en un despliegue."""
    subprocess.run(
        [sys.executable, "-m", "alembic", *argumentos],
        cwd=BACKEND,
        env={**os.environ, "DATABASE_URL": url, "MIGRATIONS_DATABASE_URL": url},
        check=True,
        capture_output=True,
        text=True,
    )


def url_del_servidor() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.fail(
            "TEST_DATABASE_URL no está definida: las pruebas de integración "
            "necesitan un PostgreSQL real (ver README.md).",
            pytrace=False,
        )
    return url


@asynccontextmanager
async def base_temporal() -> AsyncIterator[str]:
    """Crea una base vacía propia y la elimina al terminar."""
    servidor = url_del_servidor()
    nombre = f"c00_{uuid.uuid4().hex}"
    administrador = create_async_engine(
        servidor, isolation_level="AUTOCOMMIT", poolclass=NullPool
    )
    async with administrador.connect() as conexion:
        await conexion.execute(text(f'CREATE DATABASE "{nombre}"'))
    try:
        yield make_url(servidor).set(database=nombre).render_as_string(
            hide_password=False
        )
    finally:
        async with administrador.connect() as conexion:
            await conexion.execute(text(f'DROP DATABASE "{nombre}" WITH (FORCE)'))
        await administrador.dispose()


@pytest.fixture(scope="session")
async def url_base() -> AsyncIterator[str]:
    """Base de la sesión de pruebas, con las migraciones aplicadas."""
    async with base_temporal() as url:
        alembic(url, "upgrade", "head")
        yield url


@pytest.fixture(scope="session")
async def engine(url_base: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(url_base)
    yield engine
    await engine.dispose()


@pytest.fixture(autouse=True)
async def base_limpia(engine: AsyncEngine) -> AsyncIterator[None]:
    """Las pruebas confirman sus transacciones: se limpia después de cada una."""
    yield
    async with engine.begin() as conexion:
        await conexion.execute(
            text("TRUNCATE turno, profesional, prestacion RESTART IDENTITY CASCADE")
        )


@pytest.fixture
def sesiones(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return crear_fabrica_de_sesiones(engine)
