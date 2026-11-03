import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration.conftest import alembic, base_temporal

pytestmark = pytest.mark.integration


async def test_agenda_config_migration_adds_tenant_scoped_models_and_constraints():
    async with base_temporal() as url:
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            consultorio_id = await connection.scalar(text("""
                INSERT INTO consultorio (nombre, zona_horaria, modo_liberacion,
                  horas_confirmacion, horas_recordatorio, horas_liberacion,
                  horas_limite_paciente, minutos_granularidad, dias_anticipacion_maxima,
                  max_turnos_activos_paciente, activo, creado_en, actualizado_en)
                VALUES ('C06', 'America/Argentina/Buenos_Aires', 'automatico',
                  48, 24, 12, 24, 15, 60, 2, true, now(), now()) RETURNING id
            """))
            box_id = await connection.scalar(text("""
                INSERT INTO box (consultorio_id, nombre, activo)
                VALUES (:cid, 'Box 1', true) RETURNING id
            """), {'cid': consultorio_id})
            user_id = await connection.scalar(text("""
                INSERT INTO usuario (consultorio_id, nombre_usuario, email, password_hash,
                  rol, activo, creado_en, actualizado_en)
                VALUES (:cid, 'prof', 'prof@example.test', 'hash', 'profesional', true, now(), now())
                RETURNING id
            """), {'cid': consultorio_id})
            professional_id = await connection.scalar(text("""
                INSERT INTO profesional (consultorio_id, usuario_id, box_id, nombre, apellido, activo)
                VALUES (:cid, :uid, :bid, 'Ada', 'Odontóloga', true) RETURNING id
            """), {'cid': consultorio_id, 'uid': user_id, 'bid': box_id})
            await connection.execute(text("""
                INSERT INTO horario_semanal (consultorio_id, profesional_id, dia_semana,
                  hora_inicio, hora_fin) VALUES (:cid, :pid, 1, '09:00', '12:00')
            """), {'cid': consultorio_id, 'pid': professional_id})
            await connection.execute(text("""
                INSERT INTO bloqueo_agenda (consultorio_id, profesional_id, tipo, inicio, fin,
                  creado_por_id, creado_en)
                VALUES (:cid, NULL, 'feriado', '2026-12-25 00:00-03',
                  '2026-12-26 00:00-03', :uid, now())
            """), {'cid': consultorio_id, 'uid': user_id})
            await connection.execute(text("""
                INSERT INTO prestacion (consultorio_id, nombre, duracion_min, activa, sugerida)
                VALUES (:cid, 'Consulta', 30, true, true)
            """), {'cid': consultorio_id})
            with pytest.raises(Exception):
                await connection.execute(text("""
                    INSERT INTO horario_semanal (consultorio_id, profesional_id, dia_semana,
                      hora_inicio, hora_fin) VALUES (:cid, :pid, 8, '12:00', '09:00')
                """), {'cid': consultorio_id, 'pid': professional_id})
        await engine.dispose()


async def test_agenda_config_migration_is_reversible_and_keeps_one_head():
    async with base_temporal() as url:
        alembic(url, 'upgrade', 'head')
        alembic(url, 'downgrade', '0006_intento_registro')
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url)
        async with engine.connect() as connection:
            assert await connection.scalar(text("""
                SELECT count(*) FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name IN
                  ('box', 'profesional', 'horario_semanal', 'bloqueo_agenda')
            """)) == 4
        await engine.dispose()

async def test_agenda_config_constraints_reject_invalid_values_and_cross_tenant_links():
    from sqlalchemy.exc import IntegrityError

    async with base_temporal() as url:
        alembic(url, 'upgrade', 'head')
        engine = create_async_engine(url)
        async with engine.begin() as connection:
            clinic_ids = []
            for name in ('C06-A', 'C06-B'):
                clinic_ids.append(await connection.scalar(text("""
                    INSERT INTO consultorio (nombre, zona_horaria, modo_liberacion,
                      horas_confirmacion, horas_recordatorio, horas_liberacion,
                      horas_limite_paciente, minutos_granularidad, dias_anticipacion_maxima,
                      max_turnos_activos_paciente, activo, creado_en, actualizado_en)
                    VALUES (:name, 'America/Argentina/Buenos_Aires', 'automatico',
                      48, 24, 12, 24, 15, 60, 2, true, now(), now()) RETURNING id
                """), {'name': name}))
            box_id = await connection.scalar(text("""
                INSERT INTO box (consultorio_id, nombre) VALUES (:cid, 'Box 1') RETURNING id
            """), {'cid': clinic_ids[0]})
            user_id = await connection.scalar(text("""
                INSERT INTO usuario (consultorio_id, nombre_usuario, email, password_hash,
                  rol, activo, creado_en, actualizado_en)
                VALUES (:cid, 'prof', 'prof@example.test', 'hash', 'profesional', true, now(), now())
                RETURNING id
            """), {'cid': clinic_ids[0]})
            professional_id = await connection.scalar(text("""
                INSERT INTO profesional (consultorio_id, usuario_id, box_id, nombre, apellido)
                VALUES (:cid, :uid, :bid, 'Ada', 'Lovelace') RETURNING id
            """), {'cid': clinic_ids[0], 'uid': user_id, 'bid': box_id})
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(text("""
                        INSERT INTO horario_semanal (consultorio_id, profesional_id, dia_semana,
                          hora_inicio, hora_fin) VALUES (:cid, :pid, 8, '12:00', '09:00')
                    """), {'cid': clinic_ids[0], 'pid': professional_id})
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(text("""
                        INSERT INTO prestacion (consultorio_id, nombre, duracion_min)
                        VALUES (:cid, 'Inválida', 0)
                    """), {'cid': clinic_ids[0]})
            with pytest.raises(IntegrityError):
                async with connection.begin_nested():
                    await connection.execute(text("""
                        INSERT INTO profesional (consultorio_id, usuario_id, box_id, nombre, apellido)
                        VALUES (:cid, NULL, :bid, 'Cruzado', 'Tenant')
                    """), {'cid': clinic_ids[1], 'bid': box_id})
        await engine.dispose()
