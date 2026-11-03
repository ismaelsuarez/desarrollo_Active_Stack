from datetime import timedelta
import pytest
from sqlalchemy import select, func

from app.core.config import Settings
from app.domain.ports.reloj import RelojSimulado
from app.infrastructure.db.account_models import IntentoRegistroModel
from tests.integration.test_core_models import crear_consultorio_ejemplo, AHORA

pytestmark = pytest.mark.integration


def config(**changes):
    return Settings(database_url='postgresql+asyncpg://postgres@localhost/test',
        jwt_secret_key='j' * 32, origin_hash_secret='o' * 32, app_env='test',
        consultorio_activo_id=1, **changes)


async def test_limite_registro_confirmado_y_excedido_no_inserta(sesiones):
    from app.infrastructure.db.limites_cuenta import LimitesCuentaPostgres, LimiteSolicitudes
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.commit()
        limite = LimitesCuentaPostgres(session, RelojSimulado(AHORA), config(registration_limit_per_origin=1))
        await limite.admitir_registro(1, '192.0.2.1', None)
        await session.rollback()  # A later failed registration cannot erase its attempt.
        with pytest.raises(LimiteSolicitudes):
            await limite.admitir_registro(1, '192.0.2.1', None)
    async with sesiones() as session:
        rows = (await session.scalars(select(IntentoRegistroModel))).all()
        assert len(rows) == 1
        assert len(rows[0].origen_hash) == 64
        assert '192.0.2.1' not in rows[0].origen_hash
        assert rows[0].creado_en == AHORA


@pytest.mark.parametrize('host,forwarded,hops', [
    ('192.0.2.1', '198.51.100.2, 203.0.113.3', 1),
    ('192.0.2.1', '203.0.113.3', 0),
    ('invalid', None, 0),
    ('192.0.2.1', 'invalid', 1),
    ('192.0.2.1', '203.0.113.3', 2),
])
async def test_origen_confiable_y_limite_global(sesiones, host, forwarded, hops):
    from app.infrastructure.db.limites_cuenta import LimitesCuentaPostgres, LimiteSolicitudes
    from app.domain.services.auth_crypto import calcular_origen_hash
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.commit()
        limite = LimitesCuentaPostgres(session, RelojSimulado(AHORA), config(
            trusted_proxy_hops=hops, registration_limit_per_origin=1,
            registration_limit_global=1))
        await limite.admitir_registro(1, host, forwarded)
        with pytest.raises(LimiteSolicitudes):
            await limite.admitir_registro(1, host, forwarded)
    async with sesiones() as session:
        value = await session.scalar(select(IntentoRegistroModel.origen_hash))
        expected = '203.0.113.3' if hops == 1 and forwarded.startswith('198') else '192.0.2.1' if hops == 0 and host != 'invalid' else None
        assert value == calcular_origen_hash(expected, 'o' * 32)


async def test_purga_y_aislamiento_consultorio(sesiones):
    from app.infrastructure.db.limites_cuenta import LimitesCuentaPostgres
    async with sesiones() as session:
        session.add_all([crear_consultorio_ejemplo(), crear_consultorio_ejemplo(2)])
        await session.flush()
        session.add_all([
            IntentoRegistroModel(consultorio_id=2, origen_hash=None, creado_en=AHORA),
            IntentoRegistroModel(consultorio_id=1, origen_hash=None, creado_en=AHORA-timedelta(hours=25)),
        ])
        await session.commit()
        limite = LimitesCuentaPostgres(session, RelojSimulado(AHORA), config(registration_limit_global=1))
        await limite.admitir_registro(1, None, None)
    async with sesiones() as session:
        rows = (await session.scalars(select(IntentoRegistroModel))).all()
        assert sorted(row.consultorio_id for row in rows) == [1, 2]
        assert all(row.creado_en == AHORA for row in rows)
