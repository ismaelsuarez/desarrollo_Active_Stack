import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.integration.test_core_models import crear_consultorio_ejemplo, AHORA
from app.infrastructure.db.models import UsuarioModel

pytestmark = pytest.mark.integration


async def crear_cuenta(sesiones):
    async with sesiones() as session:
        session.add(crear_consultorio_ejemplo())
        await session.flush()
        user = UsuarioModel(consultorio_id=1, nombre_usuario='cuenta',
                            email='cuenta@example.test', password_hash='hash',
                            rol='paciente', aviso_privacidad_aceptado_en=AHORA,
                            aviso_privacidad_version='2026-10-borrador',
                            creado_en=AHORA, actualizado_en=AHORA)
        session.add(user)
        await session.commit()
        return user.id


async def test_solicitud_pendiente_preserva_identidad_y_fecha(sesiones):
    from app.infrastructure.db.account_models import SolicitudVinculacionModel
    uid = await crear_cuenta(sesiones)
    async with sesiones() as session:
        row = SolicitudVinculacionModel(consultorio_id=1, usuario_id=uid,
                                       dni_declarado='30123456', estado='pendiente',
                                       creada_en=AHORA)
        session.add(row)
        await session.commit()
        await session.refresh(row)
        assert row.id > 0
        assert row.estado == 'pendiente'
        assert row.paciente_id is None
        assert row.creada_en == AHORA


@pytest.mark.parametrize('second_state', ['pendiente', 'invalida'])
async def test_solicitud_rechaza_duplicado_de_cuenta_o_estado_invalido(sesiones, second_state):
    from app.infrastructure.db.account_models import SolicitudVinculacionModel
    uid = await crear_cuenta(sesiones)
    async with sesiones() as session:
        session.add(SolicitudVinculacionModel(consultorio_id=1, usuario_id=uid,
                    dni_declarado='30123456', estado='pendiente', creada_en=AHORA))
        await session.commit()
        session.add(SolicitudVinculacionModel(consultorio_id=1, usuario_id=uid,
                    dni_declarado='30123456', estado=second_state, creada_en=AHORA))
        with pytest.raises(IntegrityError):
            await session.commit()


@pytest.mark.parametrize('column', ['consultorio_id', 'usuario_id', 'paciente_id', 'resuelta_por_id'])
async def test_solicitud_rechaza_referencias_inexistentes(sesiones, column):
    from app.infrastructure.db.account_models import SolicitudVinculacionModel
    uid = await crear_cuenta(sesiones)
    values = dict(consultorio_id=1, usuario_id=uid, dni_declarado='30123456',
                  estado='pendiente', creada_en=AHORA)
    values[column] = 99999
    async with sesiones() as session:
        session.add(SolicitudVinculacionModel(**values))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_notificacion_admite_tipos_futuros_y_rechaza_tipo_desconocido(sesiones):
    from app.infrastructure.db.account_models import NotificacionModel, TIPOS_NOTIFICACION
    await crear_cuenta(sesiones)
    async with sesiones() as session:
        for kind in TIPOS_NOTIFICACION:
            session.add(NotificacionModel(consultorio_id=1, tipo=kind,
                canal='email', estado='programada', destinatario='test@example.test',
                programada_para=AHORA, intentos=0))
        await session.commit()
        assert await session.scalar(text('SELECT count(*) FROM notificacion')) == 10
        session.add(NotificacionModel(consultorio_id=1, tipo='inexistente',
                canal='email', estado='programada', destinatario='test@example.test',
                programada_para=AHORA, intentos=0))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_notificacion_reclamacion_y_limpieza(sesiones):
    from app.infrastructure.db.account_models import NotificacionModel
    uid = await crear_cuenta(sesiones)
    async with sesiones() as session:
        row = NotificacionModel(consultorio_id=1, usuario_id=uid,
                tipo='verificacion_email', canal='email', estado='enviando',
                destinatario='cuenta@example.test', programada_para=AHORA,
                reclamada_en=AHORA, intentos=1)
        session.add(row)
        await session.commit()
        row.estado = 'enviada'
        row.enviada_en = AHORA
        row.reclamada_en = None
        await session.commit()
        await session.refresh(row)
        assert row.enviada_en == AHORA
        assert row.intentos == 1
        assert row.reclamada_en is None


@pytest.mark.parametrize('state,claim', [('enviando', None), ('programada', AHORA)])
async def test_notificacion_rechaza_reclamacion_inconsistente(sesiones, state, claim):
    from app.infrastructure.db.account_models import NotificacionModel
    uid = await crear_cuenta(sesiones)
    async with sesiones() as session:
        session.add(NotificacionModel(consultorio_id=1, usuario_id=uid,
                tipo='verificacion_email', canal='email', estado=state,
                destinatario='cuenta@example.test', programada_para=AHORA,
                reclamada_en=claim, intentos=0))
        with pytest.raises(IntegrityError):
            await session.commit()


async def test_intento_registro_guarda_hash_o_origen_desconocido(sesiones):
    from app.infrastructure.db.account_models import IntentoRegistroModel
    await crear_cuenta(sesiones)
    async with sesiones() as session:
        for origin in ('a' * 64, None):
            session.add(IntentoRegistroModel(consultorio_id=1, origen_hash=origin,
                                            creado_en=AHORA))
        await session.commit()
        rows = (await session.execute(text('SELECT origen_hash, creado_en FROM intento_registro ORDER BY id'))).all()
        assert [row.origen_hash for row in rows] == ['a' * 64, None]
        assert all(row.creado_en == AHORA for row in rows)


async def test_migraciones_de_cuenta_reversibles_y_un_solo_head():
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool
    from tests.integration.conftest import BACKEND, alembic, base_temporal
    script = ScriptDirectory.from_config(Config(str(BACKEND / 'alembic.ini')))
    assert script.get_heads() == ['0007_agenda_config']
    async with base_temporal() as url:
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.connect() as connection:
            names = set((await connection.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))).scalars())
            assert {'solicitud_vinculacion', 'notificacion', 'intento_registro'} <= names
            assert not await connection.scalar(text("SELECT count(*) FROM information_schema.columns WHERE table_name='notificacion' AND column_name='ciclo'"))
            assert not await connection.scalar(text("SELECT count(*) FROM pg_constraint WHERE conrelid='notificacion'::regclass AND contype='f' AND confrelid='turno'::regclass"))
        alembic(url, 'downgrade', '0003_auth_core')
        async with engine.connect() as connection:
            assert not await connection.scalar(text("SELECT count(*) FROM information_schema.tables WHERE table_name IN ('notificacion','solicitud_vinculacion','intento_registro')"))
        alembic(url, 'upgrade', 'head')
        await engine.dispose()
