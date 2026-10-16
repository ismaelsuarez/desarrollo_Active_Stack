import os
import subprocess
import sys

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from tests.integration.conftest import BACKEND, alembic, base_temporal

pytestmark = pytest.mark.integration


def run_migration(environment, *arguments):
    env = {key: value for key, value in os.environ.items() if key not in {'APP_ENV', 'JWT_SECRET_KEY', 'DATABASE_URL', 'MIGRATIONS_DATABASE_URL'}}
    env.update(environment)
    return subprocess.run([sys.executable, '-m', 'alembic', *arguments], cwd=BACKEND, env=env, capture_output=True, text=True)


async def test_migration_reads_database_secret_file(tmp_path):
    async with base_temporal() as url:
        (tmp_path / 'database_url').write_text(url + '\n')
        result = run_migration({'SECRETS_DIR': str(tmp_path)}, 'upgrade', 'head')
        assert result.returncode == 0, result.stderr
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT version_num FROM alembic_version')) == '0001_turnos_sin_solapamiento'
        await engine.dispose()


async def test_migration_uses_direct_url_without_api_settings(tmp_path):
    async with base_temporal() as url:
        env = {'DATABASE_URL': 'postgresql+asyncpg://u:p@127.0.0.1:1/unreachable', 'MIGRATIONS_DATABASE_URL': url, 'SECRETS_DIR': str(tmp_path)}
        result = run_migration(env, 'upgrade', 'head')
        assert result.returncode == 0, result.stderr
        assert run_migration(env, 'upgrade', 'head').returncode == 0


async def test_shared_helper_does_not_follow_inherited_migration_url(monkeypatch):
    async with base_temporal() as url:
        monkeypatch.setenv('MIGRATIONS_DATABASE_URL', 'postgresql+asyncpg://u:p@127.0.0.1:1/unreachable')
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT version_num FROM alembic_version')) == '0001_turnos_sin_solapamiento'
        await engine.dispose()


async def test_existing_schema_data_and_constraint_survive_upgrade():
    from tests.integration.test_migracion import INSERTAR_TURNO, hora, profesional_y_prestacion
    async with base_temporal() as url:
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as connection:
            identifiers = await profesional_y_prestacion(connection)
            await connection.execute(INSERTAR_TURNO, {**identifiers, 'inicio': hora(10, 0), 'fin': hora(10, 30)})
        alembic(url, 'upgrade', 'head')
        async with engine.connect() as connection:
            assert await connection.scalar(text('SELECT count(*) FROM turno')) == 1
            assert await connection.scalar(text("SELECT count(*) FROM pg_constraint WHERE conname = 'turno_sin_solapamiento'")) == 1
        await engine.dispose()


async def test_preinstalled_extension_and_full_history_reversal():
    async with base_temporal() as url:
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as connection:
            await connection.execute(text('CREATE EXTENSION IF NOT EXISTS btree_gist'))
        alembic(url, 'upgrade', 'head')
        alembic(url, 'downgrade', 'base')
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='btree_gist'")) == 1
            assert await connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_name='turno'")) == 0
        alembic(url, 'upgrade', 'head')
        await engine.dispose()
