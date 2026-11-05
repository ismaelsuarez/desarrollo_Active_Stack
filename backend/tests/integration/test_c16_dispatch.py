"""Hitos C16: ventanas, enlaces opacos y fechas de ciclo en PostgreSQL."""
from datetime import timedelta
import asyncio
import os
import httpx

import pytest
from sqlalchemy import select, update
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.services.notificaciones import DespacharNotificacion
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import PacienteModel, ProfesionalModel, TurnoModel, TokenUsuarioModel, ConsultorioModel
from app.domain.services.auth_crypto import calcular_token_hash
from tests.integration.c07_support import preparar_escenario, INICIO
from tests.integration.test_notificaciones import CorreoGrabado, configuracion

pytestmark = pytest.mark.integration


async def escenario_hito(sesiones, url_base, tipo='solicitud_confirmacion',
                         horas=24, estado='pendiente', vencida=False):
    caso = await preparar_escenario(sesiones, url_base)
    caso.reloj.fijar(INICIO - timedelta(hours=horas))
    ahora = caso.reloj.ahora()
    async with sesiones() as session, session.begin():
        profesional = await session.get(ProfesionalModel, caso.profesionales[1])
        paciente = await session.get(PacienteModel, caso.pacientes[1])
        paciente.email = 'paciente@example.test'
        turno = TurnoModel(consultorio_id=1, paciente_id=paciente.id,
            profesional_id=profesional.id, box_id=profesional.box_id,
            prestacion_id=caso.prestaciones[1], inicio=INICIO,
            fin=INICIO+timedelta(minutes=30), estado=estado,
            ciclo_confirmacion=1, creado_en=ahora)
        session.add(turno)
        await session.flush()
        aviso = NotificacionModel(consultorio_id=1, turno_id=turno.id,
            tipo=tipo, canal='email', ciclo=1, estado='enviando' if vencida else 'programada',
            reclamada_en=ahora-timedelta(seconds=121) if vencida else None,
            programada_para=INICIO-timedelta(hours=48 if tipo=='solicitud_confirmacion' else 24),
            destinatario=paciente.email, mensaje='Plantilla sin secretos', intentos=0)
        session.add(aviso)
        await session.flush()
        return caso, turno.id, aviso.id


async def test_solicitud_se_omite_al_alcanzar_siguiente_hito(sesiones, url_base):
    caso, tid, nid = await escenario_hito(sesiones, url_base)
    correo = CorreoGrabado()
    resultado = await DespacharNotificacion(sesiones, caso.reloj, correo, configuracion()).ejecutar_detallado(1, nid)
    assert resultado.estado == 'omitida'
    assert correo.mensajes == []


@pytest.mark.parametrize('tipo,horas,esperado', [
    ('solicitud_confirmacion', 49, None),
    ('solicitud_confirmacion', 48, 'enviada'),
    ('solicitud_confirmacion', 24+1/3600, 'enviada'),
    ('solicitud_confirmacion', 24, 'omitida'),
    ('recordatorio', 25, None),
    ('recordatorio', 24, 'enviada'),
    ('recordatorio', 12+1/3600, 'enviada'),
    ('recordatorio', 12, 'omitida'),
    ('recordatorio', 0, 'omitida'),
])
@pytest.mark.parametrize('vencida', [False, True])
async def test_ventanas_bordes_solicitud_y_recordatorio(sesiones, url_base, tipo, horas, esperado, vencida):
    caso, tid, nid = await escenario_hito(sesiones, url_base, tipo, horas, vencida=vencida)
    correo = CorreoGrabado()
    resultado = await DespacharNotificacion(sesiones, caso.reloj, correo, configuracion()).ejecutar_detallado(1, nid)
    assert resultado.estado == esperado
    assert len(correo.mensajes) == (esperado == 'enviada')
    async with sesiones() as session:
        row = await session.get(NotificacionModel, nid)
        if esperado == 'omitida':
            assert row.intentos == 0
            assert row.reclamada_en is None


@pytest.mark.parametrize('con_cuenta',[False,True])
async def test_solicitud_emite_enlace_en_memoria_y_guarda_solo_hash(sesiones, url_base,con_cuenta):
    caso, tid, nid = await escenario_hito(sesiones, url_base, horas=48)
    usuario=caso.usuarios[1,'paciente'] if con_cuenta else None
    if con_cuenta:
        async with sesiones() as session,session.begin():
            await session.execute(update(PacienteModel).where(PacienteModel.id==caso.pacientes[1]).values(usuario_id=usuario))
    correo = CorreoGrabado()
    resultado = await DespacharNotificacion(sesiones, caso.reloj, correo, configuracion()).ejecutar_detallado(1, nid)
    assert resultado.estado == 'enviada'
    assert '/confirmar-turno#token=' in correo.mensajes[0][2]
    raw = correo.mensajes[0][2].split('#token=')[1]
    async with sesiones() as session:
        token = await session.scalar(select(TokenUsuarioModel))
        assert token.token_hash == calcular_token_hash(raw)
        assert (token.turno_id, token.ciclo, token.usuario_id) == (tid, 1, usuario)
        assert token.expira_en == INICIO
        row = await session.get(NotificacionModel, nid)
        assert raw not in row.mensaje


@pytest.mark.parametrize('tipo,horas,campo', [
    ('solicitud_confirmacion', 48, 'confirmacion_solicitada_en'),
    ('recordatorio', 24, 'recordatorio_enviado_en'),
])
async def test_registra_fecha_operativa_del_ciclo_enviado(sesiones, url_base, tipo, horas, campo):
    caso, tid, nid = await escenario_hito(sesiones, url_base, tipo, horas)
    resultado = await DespacharNotificacion(sesiones, caso.reloj, CorreoGrabado(), configuracion()).ejecutar_detallado(1, nid)
    assert resultado.estado == 'enviada'
    async with sesiones() as session:
        turno = await session.get(TurnoModel, tid)
        assert getattr(turno, campo) == caso.reloj.ahora()


@pytest.mark.parametrize('modo,estado_solicitud,marcado,estado,advierte', [
    ('automatico', 'enviada', False, 'pendiente', True),
    ('manual', 'enviada', False, 'pendiente', False),
    ('automatico', None, False, 'pendiente', False),
    ('automatico', 'fallida', False, 'pendiente', False),
    ('automatico', 'programada', False, 'pendiente', False),
    ('automatico', 'enviando', False, 'pendiente', False),
    ('automatico', 'omitida', False, 'pendiente', False),
    ('automatico', 'enviada', True, 'pendiente', False),
    ('automatico', 'enviada', False, 'confirmado', False),
    ('automatico', 'otro_ciclo', False, 'pendiente', False),
])
async def test_recordatorio_solo_advierte_si_rn60_permite(sesiones, url_base, modo, estado_solicitud, marcado, estado, advierte):
    caso, tid, nid = await escenario_hito(sesiones, url_base, 'recordatorio', 24, estado)
    async with sesiones() as session, session.begin():
        await session.execute(update(ConsultorioModel).where(ConsultorioModel.id==1).values(modo_liberacion=modo))
        if marcado:
            await session.execute(update(TurnoModel).where(TurnoModel.id==tid).values(marcado_sin_confirmar_en=caso.reloj.ahora()))
        if estado_solicitud:
            session.add(NotificacionModel(consultorio_id=1, turno_id=tid, tipo='solicitud_confirmacion', canal='email',
                ciclo=2 if estado_solicitud=='otro_ciclo' else 1,
                estado='enviada' if estado_solicitud=='otro_ciclo' else estado_solicitud,
                programada_para=INICIO-timedelta(hours=48),
                reclamada_en=caso.reloj.ahora() if estado_solicitud=='enviando' else None,
                enviada_en=caso.reloj.ahora()-timedelta(hours=1) if estado_solicitud=='enviada' else None,
                destinatario='test@example.test', intentos=1))
    correo = CorreoGrabado()
    assert await DespacharNotificacion(sesiones, caso.reloj, correo, configuracion()).ejecutar(1,nid)
    texto = correo.mensajes[0][2]
    assert ('liberado' in texto) is advierte
    assert ('Confirmá' in texto) is (estado=='pendiente')


async def test_solicitud_vieja_no_emite_token_del_ciclo_nuevo_entre_lecturas(sesiones,url_base):
    caso,tid,nid=await escenario_hito(sesiones,url_base,horas=48)
    intercalado=False
    class SesionIntercalada(AsyncSession):
        async def scalar(self, statement, *args, **kwargs):
            nonlocal intercalado
            valor=await super().scalar(statement,*args,**kwargs)
            if not intercalado and 'FROM turno' in str(statement):
                intercalado=True
                async with sesiones() as concurrente,concurrente.begin():
                    await concurrente.execute(update(TurnoModel).where(TurnoModel.id==tid).values(
                        ciclo_confirmacion=2,inicio=INICIO+timedelta(days=1),fin=INICIO+timedelta(days=1,minutes=30)))
            return valor
    fabrica=async_sessionmaker(sesiones.kw['bind'],class_=SesionIntercalada,expire_on_commit=False)
    correo=CorreoGrabado()
    await DespacharNotificacion(fabrica,caso.reloj,correo,configuracion()).ejecutar(1,nid)
    async with sesiones() as session:
        tokens=(await session.scalars(select(TokenUsuarioModel))).all()
        assert len(tokens)==1
        assert all(token.ciclo==1 for token in tokens)
        assert (await session.get(TurnoModel,tid)).ciclo_confirmacion==2


@pytest.mark.parametrize('tipo,horas,campo',[('solicitud_confirmacion',48,'confirmacion_solicitada_en'),('recordatorio',24,'recordatorio_enviado_en')])
@pytest.mark.parametrize('carrera',['ciclo','reclamacion'])
async def test_resultado_tardio_no_contamina_fechas_nuevas(sesiones,url_base,tipo,horas,campo,carrera):
    caso,tid,nid=await escenario_hito(sesiones,url_base,tipo,horas)
    class Intercalado(CorreoGrabado):
        async def enviar(self,*args):
            async with sesiones() as concurrente,concurrente.begin():
                if carrera=='ciclo':
                    await concurrente.execute(update(TurnoModel).where(TurnoModel.id==tid).values(ciclo_confirmacion=2))
                else:
                    await concurrente.execute(update(NotificacionModel).where(NotificacionModel.id==nid).values(
                        reclamada_en=caso.reloj.ahora()+timedelta(seconds=1)))
            await super().enviar(*args)
    resultado=await DespacharNotificacion(sesiones,caso.reloj,Intercalado(),configuracion()).ejecutar_detallado(1,nid)
    assert resultado.motivo==('reclamacion_perdida' if carrera=='reclamacion' else 'entregada')
    async with sesiones() as session:
        turno=await session.get(TurnoModel,tid)
        assert getattr(turno,campo) is None
        if carrera=='reclamacion':
            aviso=await session.get(NotificacionModel,nid)
            assert aviso.estado=='enviando' and aviso.reclamada_en==caso.reloj.ahora()+timedelta(seconds=1)


async def test_reintento_emite_dos_tokens_del_mismo_ciclo_sin_invalidar(sesiones,url_base):
    caso,tid,nid=await escenario_hito(sesiones,url_base,horas=48)
    class CaidaTrasEntrega(CorreoGrabado):
        async def enviar(self,*args):
            await super().enviar(*args)
            if len(self.mensajes)==1:
                raise ConnectionError('transporte_no_registrado')
    correo=CaidaTrasEntrega()
    despacho=DespacharNotificacion(sesiones,caso.reloj,correo,configuracion())
    assert (await despacho.ejecutar_detallado(1,nid)).estado=='programada'
    caso.reloj.avanzar(timedelta(seconds=121))
    assert await despacho.ejecutar(1,nid)
    enlaces=[mensaje[2].split('#token=')[1] for mensaje in correo.mensajes]
    assert len(set(enlaces))==2
    async with sesiones() as session:
        tokens=(await session.scalars(select(TokenUsuarioModel).order_by(TokenUsuarioModel.id))).all()
        assert len(tokens)==2
        assert [t.token_hash for t in tokens]==[calcular_token_hash(raw) for raw in enlaces]
        assert [(t.ciclo,t.expira_en,t.usado_en) for t in tokens]==[(1,INICIO,None),(1,INICIO,None)]


@pytest.mark.parametrize('vencida',[False,True])
async def test_vencimiento_se_resuelve_antes_de_cupos_e_intentos(sesiones,url_base,vencida):
    caso,tid,nid=await escenario_hito(sesiones,url_base,horas=24,vencida=vencida)
    async with sesiones() as session,session.begin():
        await session.execute(update(NotificacionModel).where(NotificacionModel.id==nid).values(intentos=3))
        session.add_all(NotificacionModel(consultorio_id=1,tipo='verificacion_email',canal='email',estado='enviada',
            programada_para=caso.reloj.ahora(),enviada_en=caso.reloj.ahora(),destinatario='test@example.test',intentos=1) for _ in range(2))
    correo=CorreoGrabado()
    resultado=await DespacharNotificacion(sesiones,caso.reloj,correo,configuracion(email_daily_limit=2,email_daily_limit_account=1)).ejecutar_detallado(1,nid)
    assert resultado.estado=='omitida' and correo.mensajes==[]
    async with sesiones() as session:
        row=await session.get(NotificacionModel,nid)
        assert row.intentos==3 and row.reclamada_en is None


@pytest.mark.parametrize('tipo,horas',[('solicitud_confirmacion',48),('recordatorio',24)])
async def test_mailpit_fecha_local_contenido_minimo_y_no_secretos_persistidos(sesiones,url_base,caplog,tipo,horas):
    from app.infrastructure.correo.smtp import EnviadorSMTP
    caso,tid,nid=await escenario_hito(sesiones,url_base,tipo,horas)
    async with sesiones() as session,session.begin():
        await session.execute(update(PacienteModel).where(PacienteModel.id==caso.pacientes[1]).values(
            dni='99123456',obra_social='OS_NO_CORREO',notas='NOTAS_NO_CORREO'))
        await session.execute(update(TurnoModel).where(TurnoModel.id==tid).values(notas='TURNO_PRIVADO'))
    settings=configuracion(smtp_host=os.environ['SMTP_TEST_HOST'],smtp_port=int(os.environ['SMTP_TEST_PORT']),smtp_starttls=False)
    async with httpx.AsyncClient(base_url=os.environ['MAILPIT_API_URL'],trust_env=False) as mailbox:
        await mailbox.delete('/api/v1/messages')
        assert await DespacharNotificacion(sesiones,caso.reloj,EnviadorSMTP(settings),settings).ejecutar(1,nid)
        messages=(await mailbox.get('/api/v1/messages')).json()['messages']
        assert len(messages)==1
        mensaje=(await mailbox.get('/api/v1/message/'+messages[0]['ID'])).json()['Text']
    assert '09/11/2026 10:00' in mensaje
    for privado in ('99123456','OS_NO_CORREO','NOTAS_NO_CORREO','TURNO_PRIVADO'):
        assert privado not in mensaje and privado not in caplog.text
    if tipo=='solicitud_confirmacion':
        raw=mensaje.split('#token=')[1].strip()
        assert raw not in caplog.text
        async with sesiones() as session:
            assert raw not in (await session.get(NotificacionModel,nid)).mensaje


@pytest.mark.parametrize('tipo,horas',[('solicitud_confirmacion',48),('recordatorio',24)])
async def test_resultado_smtp_y_omision_en_vuelo_no_interbloquean(sesiones,url_base,tipo,horas):
    from app.infrastructure.db.avisos_turno import RepositorioAvisosDeTurnoSQL
    from app.infrastructure.db.repositorios import RepositorioTurnosSQL
    caso,tid,nid=await escenario_hito(sesiones,url_base,tipo,horas)
    enviado=asyncio.Event()
    class CorreoInmediato(CorreoGrabado):
        async def enviar(self,*args):
            await super().enviar(*args)
            enviado.set()
    async with sesiones() as cancelacion:
        await cancelacion.execute(update(TurnoModel).where(TurnoModel.id==tid).values(estado='cancelado'))
        entrega=asyncio.create_task(DespacharNotificacion(sesiones,caso.reloj,CorreoInmediato(),configuracion()).ejecutar_detallado(1,nid))
        try:
            await asyncio.wait_for(enviado.wait(),5)
            for _ in range(150):
                async with sesiones() as observador:
                    esperando=await observador.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND wait_event_type='Lock' AND query LIKE 'UPDATE turno SET%'"))
                if esperando:
                    break
                await asyncio.sleep(.01)
            else:
                raise AssertionError('El resultado no alcanzó el registro de fecha en espera')
            turno=await cancelacion.get(TurnoModel,tid)
            await asyncio.wait_for(RepositorioAvisosDeTurnoSQL(cancelacion).omitir_hitos(RepositorioTurnosSQL._entidad(turno),1),3)
        finally:
            await cancelacion.commit()
            resultado=await asyncio.wait_for(entrega,5)
    assert resultado.estado=='enviada'
