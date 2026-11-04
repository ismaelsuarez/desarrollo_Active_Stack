"""Contratos de evolución C-07 comprobados en PostgreSQL descartable."""
from datetime import datetime, timezone

import pytest
import subprocess
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError

from tests.integration.conftest import alembic, base_temporal
from tests.integration.test_migracion import profesional_y_prestacion, hora

pytestmark = pytest.mark.integration
AHORA = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


async def legado(conexion, estado="pendiente"):
    ids = await profesional_y_prestacion(conexion)
    await conexion.execute(text("""
        INSERT INTO paciente (id, consultorio_id, nombre, apellido, dni,
            activo, creado_en, actualizado_en)
        VALUES (1, 1, 'Paciente', 'Sintetico', '30123456', true, :ahora, :ahora)
        ON CONFLICT (id) DO NOTHING
    """), {"ahora": AHORA})
    return await conexion.scalar(text("""
        INSERT INTO turno (consultorio_id, paciente_id, profesional_id, box_id,
            prestacion_id, inicio, fin, estado, creado_en)
        VALUES (1, 1, :profesional_id, 1, :prestacion_id, :inicio, :fin,
            CAST(:estado AS estado_turno), :ahora) RETURNING id
    """), {**ids, "inicio": hora(10, 0), "fin": hora(10, 30),
             "estado": estado, "ahora": AHORA})


@pytest.mark.parametrize("estado", ["pendiente", "confirmado"])
async def test_upgrade_preserva_turno_y_no_inventa_hechos_historicos(estado):
    async with base_temporal() as url:
        alembic(url, "upgrade", "0007_agenda_config")
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as conexion:
            turno_id = await legado(conexion, estado)
        alembic(url, "upgrade", "head")
        async with engine.connect() as conexion:
            turno = (await conexion.execute(text("SELECT * FROM turno WHERE id=:id"), {"id": turno_id})).mappings().one()
            assert turno["id"] == turno_id
            assert turno["inicio"] == hora(10, 0)
            assert turno["fin"] == hora(10, 30)
            assert turno["ciclo_confirmacion"] == 1
            assert turno["origen"] is None
            assert turno["creado_por_id"] is None
            assert turno["actualizado_en"] is None
            assert turno["creado_en"] == AHORA
            assert turno["estado"] == estado
            assert await conexion.scalar(text("""
                SELECT column_default FROM information_schema.columns
                WHERE table_name='turno' AND column_name='creado_en'
            """)) is None
        await engine.dispose()


async def test_turno_persiste_campos_operativos_y_fechas_suministradas(engine):
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
        await conexion.execute(text("""
            UPDATE turno SET origen='recepcion', ciclo_confirmacion=2,
                confirmado_en=:ahora, marcado_sin_confirmar_en=:ahora,
                liberado_en=:ahora, cancelado_en=:ahora,
                motivo_cancelacion='Motivo sintetico', reprogramado_de_inicio=:ahora,
                confirmacion_solicitada_en=:ahora, recordatorio_enviado_en=:ahora,
                notas='Nota sintetica', actualizado_en=:ahora
            WHERE id=:id
        """), {"id": turno_id, "ahora": AHORA})
    async with engine.connect() as conexion:
        turno = (await conexion.execute(text("SELECT * FROM turno WHERE id=:id"), {"id": turno_id})).mappings().one()
        assert turno["origen"] == "recepcion"
        assert turno["ciclo_confirmacion"] == 2
        assert turno["motivo_cancelacion"] == "Motivo sintetico"
        assert turno["notas"] == "Nota sintetica"
        for campo in ("confirmado_en", "marcado_sin_confirmar_en", "liberado_en", "cancelado_en",
                      "reprogramado_de_inicio", "confirmacion_solicitada_en", "recordatorio_enviado_en", "actualizado_en"):
            assert turno[campo] == AHORA


async def test_historial_agrega_hechos_sin_modificar_el_anterior(engine, sesiones):
    from app.infrastructure.db.models import TurnoHistorialModel
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with sesiones() as sesion:
        primero = TurnoHistorialModel(consultorio_id=1, turno_id=turno_id, usuario_id=None,
            accion="crear", estado_anterior=None, estado_nuevo="pendiente",
            detalle={"motivo": "regla_temporal"}, ocurrido_en=AHORA)
        sesion.add(primero)
        await sesion.commit()
        primer_id = primero.id
        sesion.add(TurnoHistorialModel(consultorio_id=1, turno_id=turno_id, usuario_id=None,
            accion="confirmar", estado_anterior="pendiente", estado_nuevo="confirmado",
            detalle=None, ocurrido_en=AHORA))
        await sesion.commit()
    async with engine.connect() as conexion:
        hechos = (await conexion.execute(text("SELECT id, accion, estado_anterior, estado_nuevo, detalle FROM turno_historial ORDER BY id"))).mappings().all()
        assert len(hechos) == 2
        assert hechos[0] == {"id": primer_id, "accion": "crear", "estado_anterior": None,
                            "estado_nuevo": "pendiente", "detalle": {"motivo": "regla_temporal"}}
        assert hechos[1]["accion"] == "confirmar"


@pytest.mark.parametrize("cambio", [{"turno_id": 99999}, {"usuario_id": 99999},
    {"accion": "borrar"}, {"estado_nuevo": "desconocido"}, {"estado_anterior": "desconocido"}])
async def test_historial_rechaza_referencias_y_hechos_invalidos(engine, sesiones, cambio):
    from app.infrastructure.db.models import TurnoHistorialModel
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    valores = dict(consultorio_id=1, turno_id=turno_id, usuario_id=None, accion="confirmar",
        estado_anterior="pendiente", estado_nuevo="confirmado", detalle=None, ocurrido_en=AHORA)
    valores.update(cambio)
    async with sesiones() as sesion:
        sesion.add(TurnoHistorialModel(**valores))
        with pytest.raises(IntegrityError):
            await sesion.commit()


async def test_modelo_turno_escribe_y_lee_trazabilidad_operativa(engine, sesiones):
    from app.infrastructure.db.models import TurnoModel
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, turno_id)
        assert turno.ciclo_confirmacion == 1
        assert turno.confirmado_en is None
        turno.origen = "recepcion"
        turno.confirmado_en = AHORA
        turno.actualizado_en = AHORA
        await sesion.commit()
    async with sesiones() as sesion:
        turno = await sesion.get(TurnoModel, turno_id)
        assert turno.origen == "recepcion"
        assert turno.confirmado_en == AHORA
        assert turno.actualizado_en == AHORA


@pytest.mark.parametrize("tabla", ["token_usuario", "notificacion"])
async def test_referencia_turno_inexistente_se_rechaza_pero_null_se_admite(sesiones, tabla):
    from tests.integration.test_account_models import crear_cuenta
    from app.infrastructure.db.models import TokenUsuarioModel
    from app.infrastructure.db.account_models import NotificacionModel
    usuario_id = await crear_cuenta(sesiones)
    def fila(turno_id):
        if tabla == "token_usuario":
            return TokenUsuarioModel(consultorio_id=1, usuario_id=usuario_id,
                turno_id=turno_id, tipo="verificar_email", token_hash=f"token-{turno_id}",
                expira_en=AHORA, creado_en=AHORA)
        return NotificacionModel(consultorio_id=1, usuario_id=usuario_id, turno_id=turno_id,
            tipo="verificacion_email", canal="email", estado="programada",
            destinatario="sintetico@example.test", programada_para=AHORA, intentos=0)
    async with sesiones() as sesion:
        sesion.add(fila(None))
        await sesion.commit()
        sesion.add(fila(99999))
        with pytest.raises(IntegrityError):
            await sesion.commit()


@pytest.mark.parametrize("columna", ["consultorio_id", "paciente_id", "box_id", "creado_por_id", "cancelado_por_id"])
async def test_turno_rechaza_referencias_obligatorias_y_actores_inexistentes(engine, columna):
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with engine.begin() as conexion:
        with pytest.raises(IntegrityError) as error:
            await conexion.execute(text(f"UPDATE turno SET {columna}=99999 WHERE id=:id"), {"id": turno_id})
        assert error.value.orig.sqlstate == "23503"


@pytest.mark.parametrize("columna,valor", [("origen", "desconocido"), ("ciclo_confirmacion", 0)])
async def test_turno_rechaza_origen_fuera_de_catalogo_y_ciclo_no_positivo(engine, columna, valor):
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with engine.begin() as conexion:
        with pytest.raises(IntegrityError) as error:
            await conexion.execute(text(f"UPDATE turno SET {columna}=:valor WHERE id=:id"), {"id": turno_id, "valor": valor})
        assert error.value.orig.sqlstate == "23514"


async def test_token_y_notificacion_admiten_referencia_a_turno_existente(engine, sesiones):
    from tests.integration.test_account_models import crear_cuenta
    from app.infrastructure.db.models import TokenUsuarioModel
    from app.infrastructure.db.account_models import NotificacionModel
    usuario_id = await crear_cuenta(sesiones)
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with sesiones() as sesion:
        token = TokenUsuarioModel(consultorio_id=1, usuario_id=usuario_id, turno_id=turno_id,
            tipo="confirmar_turno", token_hash="hash-valido", expira_en=AHORA, creado_en=AHORA)
        aviso = NotificacionModel(consultorio_id=1, usuario_id=usuario_id, turno_id=turno_id,
            tipo="recordatorio", canal="whatsapp", estado="preparada",
            destinatario="sintetico", programada_para=AHORA, intentos=0)
        sesion.add_all([token, aviso])
        await sesion.commit()
        await sesion.refresh(token)
        await sesion.refresh(aviso)
        assert token.turno_id == turno_id
        assert aviso.turno_id == turno_id


async def test_indices_de_agenda_e_historial_corresponden_a_las_consultas(engine):
    async with engine.connect() as conexion:
        indices = dict((await conexion.execute(text("""
            SELECT indexname, indexdef FROM pg_indexes
            WHERE tablename IN ('turno','turno_historial')
        """))).all())
    esperados = {
        "ix_turno_consultorio_profesional_inicio": "(consultorio_id, profesional_id, inicio)",
        "ix_turno_consultorio_paciente_inicio": "(consultorio_id, paciente_id, inicio)",
        "ix_turno_estado_inicio": "(estado, inicio)",
        "ix_turno_historial_turno_fecha": "(turno_id, ocurrido_en)",
        "ix_turno_historial_consultorio_fecha": "(consultorio_id, ocurrido_en)",
    }
    for nombre, columnas in esperados.items():
        assert columnas in indices[nombre]


async def test_exclusion_unica_preserva_rango_y_codigo_real_despues_de_upgrade(engine):
    async with engine.begin() as conexion:
        turno_id = await legado(conexion)
    async with engine.connect() as conexion:
        restricciones = (await conexion.execute(text("""
            SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint
            WHERE conrelid='turno'::regclass AND contype='x'
        """))).all()
        assert len(restricciones) == 1
        nombre, definicion = restricciones[0]
        assert nombre == "turno_sin_solapamiento"
        assert "tstzrange(inicio, fin, '[)'::text) WITH &&" in definicion
        assert "consultorio_id WITH =" in definicion
        assert "profesional_id WITH =" in definicion
        with pytest.raises(IntegrityError) as error:
            await conexion.execute(text("""
                INSERT INTO turno (consultorio_id,paciente_id,profesional_id,box_id,
                    prestacion_id,inicio,fin,creado_en)
                SELECT consultorio_id,paciente_id,profesional_id,box_id,prestacion_id,
                    inicio,fin,creado_en FROM turno WHERE id=:id
            """), {"id": turno_id})
        assert error.value.orig.sqlstate == "23P01"
        assert error.value.orig.__cause__.constraint_name == "turno_sin_solapamiento"
    async with engine.connect() as conexion:
        assert await conexion.scalar(text("SELECT count(*) FROM turno")) == 1


async def test_downgrade_upgrade_preserva_fila_pero_descarta_historial_nuevo():
    async with base_temporal() as url:
        alembic(url, "upgrade", "head")
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as conexion:
            turno_id = await legado(conexion)
            await conexion.execute(text("""
                INSERT INTO turno_historial (consultorio_id,turno_id,accion,
                    estado_nuevo,ocurrido_en) VALUES (1,:id,'crear','pendiente',:ahora)
            """), {"id": turno_id, "ahora": AHORA})
        try:
            alembic(url, "downgrade", "0007_agenda_config")
        except subprocess.CalledProcessError as error:
            pytest.fail(error.stderr)
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT count(*) FROM turno WHERE id=:id"), {"id": turno_id}) == 1
            assert await conexion.scalar(text("SELECT to_regclass('turno_historial')")) is None
        alembic(url, "upgrade", "head")
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT ciclo_confirmacion FROM turno WHERE id=:id"), {"id": turno_id}) == 1
            assert await conexion.scalar(text("SELECT count(*) FROM turno_historial")) == 0
        await engine.dispose()


@pytest.mark.parametrize("tipo", ["paciente", "token_usuario", "notificacion"])
async def test_upgrade_aborta_ante_huerfanos_sin_borrar_ni_inventar_datos(tipo):
    async with base_temporal() as url:
        alembic(url, "upgrade", "0007_agenda_config")
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as conexion:
            turno_id = await legado(conexion)
            if tipo == "paciente":
                await conexion.execute(text("DELETE FROM paciente WHERE id=1"))
            elif tipo == "notificacion":
                await conexion.execute(text("""
                    INSERT INTO notificacion (consultorio_id,turno_id,tipo,canal,estado,
                        destinatario,programada_para,intentos)
                    VALUES (1,99999,'recordatorio','email','programada','sintetico',:ahora,0)
                """), {"ahora": AHORA})
            else:
                usuario_id = await conexion.scalar(text("""
                    INSERT INTO usuario (consultorio_id,nombre_usuario,email,password_hash,
                        rol,creado_en,actualizado_en) VALUES
                        (1,'sintetico','sintetico@example.test','hash','recepcion',:ahora,:ahora)
                    RETURNING id
                """), {"ahora": AHORA})
                await conexion.execute(text("""
                    INSERT INTO token_usuario (consultorio_id,usuario_id,turno_id,tipo,
                        token_hash,expira_en,creado_en)
                    VALUES (1,:uid,99999,'confirmar_turno','huerfano',:ahora,:ahora)
                """), {"uid": usuario_id, "ahora": AHORA})
        with pytest.raises(subprocess.CalledProcessError) as error:
            alembic(url, "upgrade", "head")
        assert "referencias huerfanas" in error.value.stderr
        async with engine.connect() as conexion:
            assert await conexion.scalar(text("SELECT version_num FROM alembic_version")) == "0007_agenda_config"
            assert await conexion.scalar(text("SELECT count(*) FROM turno WHERE id=:id"), {"id": turno_id}) == 1
            assert not await conexion.scalar(text("""
                SELECT count(*) FROM information_schema.columns
                WHERE table_name='turno' AND column_name='ciclo_confirmacion'
            """))
            if tipo == "paciente":
                assert await conexion.scalar(text("SELECT count(*) FROM paciente")) == 0
            else:
                assert await conexion.scalar(text(f"SELECT count(*) FROM {tipo} WHERE turno_id=99999")) == 1
        await engine.dispose()
