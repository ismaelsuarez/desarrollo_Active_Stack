"""RN-60 con CAS, historial y avisos sobre PostgreSQL real."""
import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select, update, func, text

from app.application.use_cases.evaluar_hitos_turnos import EvaluarHitosTurnos
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import TurnoModel, TurnoHistorialModel, ConsultorioModel, ProfesionalModel
from tests.integration.test_c16_dispatch import escenario_hito

pytestmark = pytest.mark.integration


async def preparar_decision(sesiones, url_base, enviada=True, modo='automatico', horas=12):
    caso, tid, nid = await escenario_hito(sesiones, url_base, horas=horas)
    async with sesiones() as session, session.begin():
        await session.execute(update(ConsultorioModel).where(ConsultorioModel.id==1).values(modo_liberacion=modo))
        if enviada:
            await session.execute(update(NotificacionModel).where(NotificacionModel.id==nid).values(
                estado='enviada', enviada_en=caso.reloj.ahora()-timedelta(hours=24)))
    return caso, tid, nid


async def test_rn60_libera_y_confirma_historial_aviso_juntos(sesiones,url_base):
    caso, tid, nid = await preparar_decision(sesiones,url_base)
    await EvaluarHitosTurnos(sesiones,caso.reloj).ejecutar(1)
    async with sesiones() as session:
        turno = await session.get(TurnoModel,tid)
        assert turno.estado == 'liberado'
        assert turno.liberado_en == caso.reloj.ahora()
        historial = (await session.scalars(select(TurnoHistorialModel))).all()
        assert [(x.accion,x.usuario_id) for x in historial] == [('liberar',None)]
        aviso = await session.scalar(select(NotificacionModel).where(NotificacionModel.tipo=='liberacion'))
        assert aviso is not None and aviso.ciclo == 1


@pytest.mark.parametrize('modo,estado_solicitud,ciclo_solicitud', [
    ('manual','enviada',1), ('automatico','programada',1),
    ('automatico','enviando',1), ('automatico','fallida',1),
    ('automatico','omitida',1), ('automatico','enviada',2), ('automatico',None,1),
])
async def test_sin_prueba_envio_marca_una_vez_por_ciclo(sesiones,url_base,modo,estado_solicitud,ciclo_solicitud):
    caso,tid,nid=await preparar_decision(sesiones,url_base,False,modo)
    async with sesiones() as session,session.begin():
        if estado_solicitud is None:
            from sqlalchemy import delete
            await session.execute(delete(NotificacionModel).where(NotificacionModel.id==nid))
        else:
            await session.execute(update(NotificacionModel).where(NotificacionModel.id==nid).values(
                estado=estado_solicitud,ciclo=ciclo_solicitud,
                reclamada_en=caso.reloj.ahora() if estado_solicitud=='enviando' else None))
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    await evaluador.ejecutar(1)
    async with sesiones() as session:
        turno=await session.get(TurnoModel,tid)
        assert turno.estado=='pendiente' and turno.marcado_sin_confirmar_en==caso.reloj.ahora()
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==1
        assert await session.scalar(select(NotificacionModel.id).where(NotificacionModel.tipo=='liberacion')) is None
    # A late proof of delivery cannot reopen the automatic decision in this cycle.
    if estado_solicitud is not None:
        async with sesiones() as session,session.begin():
            await session.execute(update(NotificacionModel).where(NotificacionModel.id==nid).values(
                estado='enviada',reclamada_en=None,ciclo=1))
    await evaluador.ejecutar(1)
    assert await evaluador.seleccionar_candidatos(1)==[]
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==1


@pytest.mark.parametrize('enviada',[True,False])
async def test_dos_evaluaciones_bloqueadas_producen_un_solo_efecto(sesiones,url_base,enviada):
    caso,tid,nid=await preparar_decision(sesiones,url_base,enviada)
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    async with sesiones() as bloqueo:
        await bloqueo.scalar(select(TurnoModel).where(TurnoModel.id==tid).with_for_update())
        tareas=[asyncio.create_task(evaluador.evaluar(1,tid,1)) for _ in range(2)]
        try:
            async def esperando():
                for _ in range(150):
                    async with sesiones() as observador:
                        cantidad=await observador.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'UPDATE turno SET%'") )
                    if cantidad>=2:
                        return
                    await asyncio.sleep(.01)
                raise AssertionError('Las dos conexiones no alcanzaron la actualización concurrente')
            await esperando()
        finally:
            await bloqueo.rollback()
            resultados=await asyncio.gather(*tareas)
    assert sorted(resultados)==[False,True]
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==1
        assert await session.scalar(select(func.count()).select_from(NotificacionModel).where(NotificacionModel.tipo=='liberacion'))==int(enviada)


@pytest.mark.parametrize('horas',[0,-1,12+1/3600])
async def test_iniciados_y_anterior_al_hito_no_se_seleccionan(sesiones,url_base,horas):
    caso,tid,nid=await preparar_decision(sesiones,url_base,True,horas=horas)
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    assert await evaluador.seleccionar_candidatos(1)==[]
    await evaluador.ejecutar(1)
    await evaluador.ejecutar(1)
    async with sesiones() as session:
        turno=await session.get(TurnoModel,tid)
        assert turno.estado=='pendiente' and turno.marcado_sin_confirmar_en is None
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==0


@pytest.mark.parametrize('enviada',[True,False])
async def test_inicio_entre_seleccion_y_decision_impide_efectos(sesiones,url_base,enviada):
    caso,tid,nid=await preparar_decision(sesiones,url_base,enviada)
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    assert await evaluador.seleccionar_candidatos(1)==[(tid,1)]
    caso.reloj.avanzar(timedelta(hours=12))
    assert await evaluador.evaluar(1,tid,1) is False
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==0


@pytest.mark.parametrize('cambio',[
    {'estado':'confirmado'}, {'estado':'cancelado'},
    {'ciclo_confirmacion':2}, {'marcado_sin_confirmar_en':'ahora'},
])
async def test_decision_obsoleta_no_toca_cambio_concurrente(sesiones,url_base,cambio):
    caso,tid,nid=await preparar_decision(sesiones,url_base)
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    assert await evaluador.seleccionar_candidatos(1)==[(tid,1)]
    valores={k:caso.reloj.ahora() if v=='ahora' else v for k,v in cambio.items()}
    async with sesiones() as session,session.begin():
        await session.execute(update(TurnoModel).where(TurnoModel.id==tid).values(**valores))
    assert await evaluador.evaluar(1,tid,1) is False
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==0


@pytest.mark.parametrize('destino',['turno_historial','notificacion'])
async def test_error_de_efectos_revierte_liberacion_completa(sesiones,url_base,destino):
    caso,tid,nid=await preparar_decision(sesiones,url_base)
    async with sesiones() as session,session.begin():
        await session.execute(text("CREATE FUNCTION c16_rechazar() RETURNS trigger LANGUAGE plpgsql AS 'BEGIN RAISE EXCEPTION ''fallo_controlado''; END'"))
        await session.execute(text(f'CREATE TRIGGER c16_fallo BEFORE INSERT ON {destino} FOR EACH ROW EXECUTE FUNCTION c16_rechazar()'))
    try:
        with pytest.raises(Exception,match='fallo_controlado'):
            await EvaluarHitosTurnos(sesiones,caso.reloj).ejecutar(1)
    finally:
        async with sesiones() as session,session.begin():
            await session.execute(text(f'DROP TRIGGER c16_fallo ON {destino}'))
            await session.execute(text('DROP FUNCTION c16_rechazar()'))
    async with sesiones() as session:
        turno=await session.get(TurnoModel,tid)
        assert turno.estado=='pendiente' and turno.liberado_en is None
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==0


async def test_barrido_tardio_marca_y_omite_hitos_antes_del_despacho(sesiones,url_base):
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    from app.application.services.notificaciones import DespacharNotificacion
    from tests.integration.test_notificaciones import CorreoGrabado,configuracion
    caso,tid,nid=await preparar_decision(sesiones,url_base,False)
    correo=CorreoGrabado()
    settings=configuracion()
    barrido=EjecutarBarrido(sesiones,caso.reloj,DespacharNotificacion(sesiones,caso.reloj,correo,settings),settings)
    resumen=await barrido.ejecutar(1)
    async with sesiones() as session:
        turno=await session.get(TurnoModel,tid)
        assert turno.estado=='pendiente' and turno.marcado_sin_confirmar_en==caso.reloj.ahora()
        assert (await session.get(NotificacionModel,nid)).estado=='omitida'
    assert (resumen.reclamadas,resumen.enviadas,resumen.omitidas)==(0,0,1)
    assert correo.mensajes==[]


async def test_seleccion_por_lotes_100_3_0_sin_reevaluar_resueltos(sesiones,url_base):
    caso,tid,nid=await preparar_decision(sesiones,url_base,False,modo='manual')
    async with sesiones() as session,session.begin():
        original=await session.get(TurnoModel,tid)
        valores={column.name:getattr(original,column.name) for column in TurnoModel.__table__.columns if column.name!='id'}
        valores['es_sobreturno']=True
        session.add_all(TurnoModel(**valores) for _ in range(102))
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    candidatos=await evaluador.seleccionar_candidatos(1)
    assert len(candidatos)==100
    assert candidatos==sorted(candidatos)
    await evaluador.ejecutar(1)
    assert len(await evaluador.seleccionar_candidatos(1))==3
    await evaluador.ejecutar(1)
    assert await evaluador.seleccionar_candidatos(1)==[]
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==103


@pytest.mark.parametrize('cambio',[{'estado':'confirmado'},{'estado':'cancelado'},{'ciclo_confirmacion':2}])
async def test_update_esperando_cambio_concurrente_pierde_sin_historial(sesiones,url_base,cambio):
    caso,tid,nid=await preparar_decision(sesiones,url_base)
    async with sesiones() as propietario:
        await propietario.execute(update(TurnoModel).where(TurnoModel.id==tid).values(**cambio))
        tarea=asyncio.create_task(EvaluarHitosTurnos(sesiones,caso.reloj).evaluar(1,tid,1))
        try:
            for _ in range(150):
                async with sesiones() as observador:
                    bloqueados=await observador.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'UPDATE turno SET%'"))
                if bloqueados>=1:
                    break
                await asyncio.sleep(.01)
            else:
                raise AssertionError('No alcanzó UPDATE en espera del cambio concurrente')
        finally:
            await propietario.commit()
            resultado=await tarea
    assert resultado is False
    async with sesiones() as session:
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel))==0


async def test_cupo_agotado_no_frena_liberacion_y_aviso_queda_durable(sesiones,url_base):
    from app.application.use_cases.ejecutar_barrido import EjecutarBarrido
    from app.application.services.notificaciones import DespacharNotificacion
    from tests.integration.test_notificaciones import CorreoGrabado,configuracion
    caso,tid,nid=await preparar_decision(sesiones,url_base)
    settings=configuracion(email_daily_limit=2,email_daily_limit_account=1)
    async with sesiones() as session,session.begin():
        session.add_all(NotificacionModel(consultorio_id=1,tipo='verificacion_email',canal='email',
            estado='enviada',programada_para=caso.reloj.ahora(),enviada_en=caso.reloj.ahora(),
            destinatario='cuenta@example.test',intentos=1) for _ in range(2))
    correo=CorreoGrabado()
    resumen=await EjecutarBarrido(sesiones,caso.reloj,DespacharNotificacion(sesiones,caso.reloj,correo,settings),settings).ejecutar(1)
    async with sesiones() as session:
        assert (await session.get(TurnoModel,tid)).estado=='liberado'
        aviso=await session.scalar(select(NotificacionModel).where(NotificacionModel.tipo=='liberacion'))
        assert aviso.estado=='programada'
    assert resumen.enviadas==0 and correo.mensajes==[]


async def test_seleccion_excluye_ajenos_confirmados_y_marcados_con_orden_real(sesiones,url_base):
    caso,tid,nid=await preparar_decision(sesiones,url_base,False)
    async with sesiones() as session,session.begin():
        original=await session.get(TurnoModel,tid)
        datos={col.name:getattr(original,col.name) for col in TurnoModel.__table__.columns if col.name!='id'}
        datos['es_sobreturno']=True
        elegible=TurnoModel(**{**datos,'inicio':original.inicio-timedelta(hours=2),'fin':original.fin-timedelta(hours=2)})
        confirmado=TurnoModel(**{**datos,'estado':'confirmado'})
        marcado=TurnoModel(**{**datos,'marcado_sin_confirmar_en':caso.reloj.ahora()})
        profesional=await session.get(ProfesionalModel,caso.profesionales[2])
        ajeno=TurnoModel(**{**datos,'consultorio_id':2,'paciente_id':caso.pacientes[2],
            'profesional_id':profesional.id,'box_id':profesional.box_id,'prestacion_id':caso.prestaciones[2]})
        session.add_all([elegible,confirmado,marcado,ajeno])
        await session.flush()
        temprano,otro=elegible.id,ajeno.id
    evaluador=EvaluarHitosTurnos(sesiones,caso.reloj)
    assert await evaluador.seleccionar_candidatos(1)==[(temprano,1),(tid,1)]
    assert await evaluador.seleccionar_candidatos(2)==[(otro,1)]
    await evaluador.ejecutar(1)
    async with sesiones() as session:
        ajeno=await session.get(TurnoModel,otro)
        assert ajeno.estado=='pendiente' and ajeno.marcado_sin_confirmar_en is None
        assert await session.scalar(select(func.count()).select_from(TurnoHistorialModel).where(TurnoHistorialModel.consultorio_id==2))==0
