"""Purga aislada por consultorio, fronteras exactas y FKs reales."""
from datetime import timedelta
import pytest
from sqlalchemy import select, update, text
from app.infrastructure.db.models import TokenUsuarioModel, RefreshTokenModel, IntentoIngresoModel
from app.infrastructure.db.account_models import IntentoRegistroModel
from tests.integration.c07_support import preparar_escenario, AHORA

pytestmark=pytest.mark.integration


async def test_tokens_expirados_y_retencion_por_consultorio(sesiones,url_base):
    from app.application.services.limpieza_barrido import LimpiarBarrido
    escenario=await preparar_escenario(sesiones,url_base)
    async with sesiones() as session,session.begin():
        for cid in (1,2):
            uid=escenario.usuarios[cid,'paciente']
            for delta in (-1,0,1):
                expiry=AHORA+timedelta(microseconds=delta)
                session.add(TokenUsuarioModel(consultorio_id=cid,usuario_id=uid,tipo='verificar_email',
                    token_hash=f't{cid}{delta}',creado_en=AHORA-timedelta(hours=1),expira_en=expiry))
                session.add(RefreshTokenModel(consultorio_id=cid,usuario_id=uid,token_hash=f'r{cid}{delta}',
                    creado_en=AHORA-timedelta(hours=1),expira_en=expiry))
                old=AHORA-timedelta(hours=24)+timedelta(microseconds=delta)
                session.add(IntentoRegistroModel(consultorio_id=cid,creado_en=old))
                session.add(IntentoIngresoModel(consultorio_id=cid,identificador_hash='h',creado_en=old))
    cleanup=LimpiarBarrido(sesiones,escenario.reloj)
    await cleanup.ejecutar(1)
    await cleanup.ejecutar(1)
    async with sesiones() as session:
        for model,own in ((TokenUsuarioModel,1),(RefreshTokenModel,1),(IntentoRegistroModel,2),(IntentoIngresoModel,2)):
            assert len((await session.scalars(select(model).where(model.consultorio_id==1))).all())==own
            assert len((await session.scalars(select(model).where(model.consultorio_id==2))).all())==3


async def test_refresh_expirado_referenciado_conserva_credencial_valida(sesiones,url_base):
    from app.application.services.limpieza_barrido import LimpiarBarrido
    escenario=await preparar_escenario(sesiones,url_base)
    async with sesiones() as session,session.begin():
        uid=escenario.usuarios[1,'paciente']
        expired=RefreshTokenModel(consultorio_id=1,usuario_id=uid,token_hash='old',creado_en=AHORA,expira_en=AHORA)
        session.add(expired)
        await session.flush()
        valid=RefreshTokenModel(consultorio_id=1,usuario_id=uid,token_hash='new',creado_en=AHORA,
            expira_en=AHORA+timedelta(days=1),reemplazado_por_id=expired.id)
        session.add(valid)
        await session.flush()
        valid_id=valid.id
    await LimpiarBarrido(sesiones,escenario.reloj).ejecutar(1)
    async with sesiones() as session:
        row=await session.get(RefreshTokenModel,valid_id)
        assert row is not None
        assert row.reemplazado_por_id is None


async def test_barrido_vacio_tambien_purga_y_error_se_observa(sesiones,url_base):
    from app.application.services.notificaciones import DespacharNotificacion
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    from app.infrastructure.db.account_models import BarridoEstadoModel
    from tests.integration.test_notificaciones import CorreoGrabado, configuracion
    escenario=await preparar_escenario(sesiones,url_base)
    async with sesiones() as session,session.begin():
        session.add(IntentoIngresoModel(consultorio_id=1,identificador_hash='x',creado_en=AHORA-timedelta(days=2)))
    settings=configuracion()
    sweep=EjecutarBarrido(sesiones,escenario.reloj,DespacharNotificacion(sesiones,escenario.reloj,CorreoGrabado(),settings),settings)
    result=await sweep.ejecutar(1)
    assert result.enviadas==0
    async with sesiones() as session:
        assert list((await session.scalars(select(IntentoIngresoModel))).all())==[]
    class Fallo:
        async def ejecutar(self,*args):
            raise RuntimeError('NO_LOG_DATOS')
    sweep.limpieza=Fallo()
    with pytest.raises(RuntimeError):
        await sweep.ejecutar(1)
    async with sesiones() as session:
        assert (await session.get(BarridoEstadoModel,1)).estado=='error'


async def test_fallo_real_purga_revierte_su_transaccion_y_conserva_dominio(sesiones,url_base):
    from app.application.services.limpieza_barrido import LimpiarBarrido
    escenario=await preparar_escenario(sesiones,url_base)
    async with sesiones() as session,session.begin():
        session.add(IntentoRegistroModel(consultorio_id=1,creado_en=AHORA-timedelta(days=2)))
        await session.execute(text("CREATE FUNCTION fallo_purga_c15() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'fallo sintetico'; END; $$"))
        await session.execute(text('CREATE TRIGGER fallo_purga_c15 BEFORE DELETE ON intento_registro FOR EACH ROW EXECUTE FUNCTION fallo_purga_c15()'))
    try:
        with pytest.raises(Exception):
            await LimpiarBarrido(sesiones,escenario.reloj).ejecutar(1)
        async with sesiones() as session:
            assert len((await session.scalars(select(IntentoRegistroModel))).all())==1
            assert await session.scalar(text('SELECT count(*) FROM paciente'))==2
            assert await session.scalar(text('SELECT count(*) FROM usuario'))==10
    finally:
        async with sesiones() as session,session.begin():
            await session.execute(text('DROP TRIGGER fallo_purga_c15 ON intento_registro'))
            await session.execute(text('DROP FUNCTION fallo_purga_c15()'))
