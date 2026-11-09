from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.infrastructure.db.account_models import NotificacionModel
from tests.integration.c07_support import AHORA, preparar_escenario

pytestmark = pytest.mark.integration


async def test_account_notifications_preserve_nullable_cycle_and_multiple_nulls(sesiones):
    from tests.integration.test_notificaciones import preparar

    first = await preparar(sesiones, ciclo=None)
    second = await preparar(sesiones, ciclo=None)
    async with sesiones() as session:
        rows = (await session.scalars(select(NotificacionModel).order_by(NotificacionModel.id))).all()
    assert [row.id for row in rows] == [first, second]
    assert [row.ciclo for row in rows] == [None, None]


async def turno_de_ejemplo(sesiones, url_base):
    escenario = await preparar_escenario(sesiones, url_base)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=escenario.app), base_url="http://test") as client:
        response = await client.post("/api/v1/turnos", headers=escenario.headers(), json=escenario.payload())
    assert response.status_code == 201
    return response.json()["id"]


def aviso(turno_id, **cambios):
    values = dict(consultorio_id=1, turno_id=turno_id, ciclo=1,
                  tipo="cancelacion_por_personal", canal="email", estado="programada",
                  destinatario="persona@example.test", mensaje="Cancelado", programada_para=AHORA, intentos=0)
    return NotificacionModel(**(values | cambios))


async def test_notification_unique_key_rejects_same_turn_type_channel_cycle(sesiones, url_base):
    turno_id = await turno_de_ejemplo(sesiones, url_base)
    async with sesiones() as session:
        session.add(aviso(turno_id))
        await session.commit()
    async with sesiones() as session:
        session.add(aviso(turno_id))
        with pytest.raises(IntegrityError) as error:
            await session.commit()
        assert "uq_notificacion_turno_tipo_canal_ciclo" in str(error.value)


@pytest.mark.parametrize("cambios", [{"ciclo": 2}, {"tipo": "reprogramacion_por_personal"}, {"canal": "whatsapp"}])
async def test_other_cycle_type_or_channel_is_a_distinct_notification(sesiones, url_base, cambios):
    tid = await turno_de_ejemplo(sesiones, url_base)
    async with sesiones() as session:
        session.add_all([aviso(tid), aviso(tid, **cambios)])
        await session.commit()
        assert len((await session.scalars(select(NotificacionModel))).all()) == 2


async def test_sweep_state_persists_uuid_and_empty_counters_per_clinic(sesiones):
    from app.infrastructure.db.account_models import BarridoEstadoModel
    from tests.integration.test_core_models import crear_consultorio_ejemplo
    run_id = uuid4()
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.flush()
        session.add(BarridoEstadoModel(consultorio_id=1, ejecucion_id=run_id,
                    iniciado_en=AHORA, estado="en_curso"))
        await session.commit()
    async with sesiones() as session:
        row = await session.get(BarridoEstadoModel, 1)
        assert row.ejecucion_id == run_id
        assert row.finalizado_en is None
        assert (row.reclamadas, row.enviadas, row.reintentadas, row.omitidas, row.fallidas) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize("cambio", [
    {"estado": "desconocido"}, {"reclamadas": -1}, {"enviadas": -1},
    {"reintentadas": -1}, {"omitidas": -1}, {"fallidas": -1},
    {"estado": "exitoso"}, {"estado": "error"},
    {"finalizado_en": AHORA + timedelta(seconds=1)},
    {"estado": "exitoso", "finalizado_en": AHORA - timedelta(seconds=1)},
])
async def test_sweep_state_rejects_invalid_state_dates_or_counters(sesiones, cambio):
    from app.infrastructure.db.account_models import BarridoEstadoModel
    from tests.integration.test_core_models import crear_consultorio_ejemplo
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.commit()
    async with sesiones() as session:
        values = dict(consultorio_id=1, ejecucion_id=uuid4(), iniciado_en=AHORA, estado="en_curso") | cambio
        session.add(BarridoEstadoModel(**values))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize("estado", ["exitoso", "error"])
async def test_sweep_state_isolated_by_clinic_and_finalized_state_is_valid(sesiones, estado):
    from app.infrastructure.db.account_models import BarridoEstadoModel
    from tests.integration.test_core_models import crear_consultorio_ejemplo
    first, second = uuid4(), uuid4()
    async with sesiones() as session:
        session.add_all([crear_consultorio_ejemplo(1), crear_consultorio_ejemplo(2)])
        await session.flush()
        session.add_all([
            BarridoEstadoModel(consultorio_id=1, ejecucion_id=first, iniciado_en=AHORA, estado="en_curso"),
            BarridoEstadoModel(consultorio_id=2, ejecucion_id=second, iniciado_en=AHORA, finalizado_en=AHORA, estado=estado, reclamadas=1),
        ])
        await session.commit()
    async with sesiones() as session:
        assert (await session.get(BarridoEstadoModel, 1)).ejecucion_id == first
        row = await session.get(BarridoEstadoModel, 2)
        assert (row.ejecucion_id, row.estado, row.reclamadas) == (second, estado, 1)
    allowed = {"consultorio_id", "ejecucion_id", "iniciado_en", "finalizado_en", "estado", "reclamadas", "enviadas", "reintentadas", "omitidas", "fallidas"}
    assert set(BarridoEstadoModel.__table__.columns.keys()) == allowed


async def test_legacy_upgrade_preserves_rows_without_inventing_cycles_and_disposable_downgrade():
    from tests.integration.conftest import alembic, base_temporal
    from tests.integration.test_c07_migration import legado
    async with base_temporal() as url:
        alembic(url, "upgrade", "0008_turnos_core")
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as connection:
            tid = await legado(connection)
            await connection.execute(text("""INSERT INTO notificacion
                (consultorio_id,turno_id,tipo,canal,estado,destinatario,programada_para,intentos,mensaje)
                VALUES (1,NULL,'verificacion_email','email','programada','cuenta@example.test',:ahora,0,'Cuenta'),
                       (1,:tid,'recordatorio','email','programada','persona@example.test',:ahora,1,'Legado')"""), {"ahora": AHORA, "tid": tid})
            original = (await connection.execute(text("SELECT row_to_json(n) FROM notificacion n ORDER BY id"))).scalars().all()
            previous_checks = set((await connection.execute(text("SELECT conname FROM pg_constraint WHERE conrelid='notificacion'::regclass"))).scalars().all())
            previous_indexes = set((await connection.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='notificacion'"))).scalars().all())
        alembic(url, "upgrade", "head")
        async with engine.connect() as connection:
            updated = (await connection.execute(text("SELECT row_to_json(n) FROM notificacion n ORDER BY id"))).scalars().all()
            assert updated == [row | {"ciclo": None} for row in original]
            constraints = (await connection.execute(text("SELECT conname FROM pg_constraint WHERE conrelid='notificacion'::regclass"))).scalars().all()
            assert "uq_notificacion_turno_tipo_canal_ciclo" in constraints
            assert "ck_notificacion_reclamacion_consistente" in constraints
            assert previous_checks <= set(constraints)
            indexes = set((await connection.execute(text("SELECT indexname FROM pg_indexes WHERE tablename='notificacion'"))).scalars().all())
            assert previous_indexes <= indexes
            assert await connection.scalar(text("SELECT count(*) FROM barrido_estado")) == 0
            assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == "0012_account_request_limit"
        alembic(url, "downgrade", "0008_turnos_core")
        async with engine.connect() as connection:
            restored = (await connection.execute(text("SELECT row_to_json(n) FROM notificacion n ORDER BY id"))).scalars().all()
            assert restored == original
            assert await connection.scalar(text("SELECT to_regclass('public.barrido_estado')")) is None
        alembic(url, "upgrade", "head")
        async with engine.connect() as connection:
            assert await connection.scalar(text("SELECT count(*) FROM notificacion WHERE ciclo IS NULL")) == 2
        await engine.dispose()
