"""RN-21/RN-37: rollback and resource closure at the transaction boundary."""
import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.db.models import ConsultorioModel
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from tests.integration.test_core_models import crear_consultorio_ejemplo

pytestmark = pytest.mark.integration


async def test_commit_failure_rolls_back_before_closing_session(engine):
    events = []

    class CommitFallido(AsyncSession):
        async def commit(self):
            await self.flush()
            raise RuntimeError("commit controlado")

        async def rollback(self):
            events.append("rollback")
            await super().rollback()

        async def close(self):
            events.append("close")
            await super().close()

    sesiones = async_sessionmaker(engine, class_=CommitFallido, expire_on_commit=False)
    with pytest.raises(RuntimeError, match="commit controlado"):
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            unidad._sesion.add(crear_consultorio_ejemplo(15))

    assert events == ["rollback", "close"]
    async with AsyncSession(engine) as sesion:
        assert await sesion.scalar(select(ConsultorioModel.id).where(ConsultorioModel.id == 15)) is None


@pytest.mark.parametrize("failure", ["body", "flush", None])
async def test_transaction_closes_resources_and_keeps_only_successful_data(engine, failure):
    events = []
    instances = []

    class SesionRegistrada(AsyncSession):
        async def rollback(self):
            events.append("rollback")
            await super().rollback()

        async def close(self):
            events.append("close")
            await super().close()

    sesiones = async_sessionmaker(engine, class_=SesionRegistrada, expire_on_commit=False)

    async def operate():
        async with UnidadDeTrabajoSQL(sesiones) as unidad:
            instances.append(unidad._sesion)
            fila = crear_consultorio_ejemplo(16)
            if failure == "flush":
                fila.horas_confirmacion = 1
            unidad._sesion.add(fila)
            await unidad._sesion.flush()
            if failure == "body":
                raise RuntimeError("cuerpo controlado")

    if failure:
        with pytest.raises(IntegrityError if failure == "flush" else RuntimeError):
            await operate()
        assert events == ["rollback", "close"]
    else:
        await operate()
        assert events == ["close"]
    async with UnidadDeTrabajoSQL(sesiones) as nueva:
        assert nueva._sesion is not instances[0]
        assert nueva._sesion.sync_session.expire_on_commit is False
    async with AsyncSession(engine) as sesion:
        identificador = await sesion.scalar(select(ConsultorioModel.id).where(ConsultorioModel.id == 16))
        assert identificador == (16 if failure is None else None)
