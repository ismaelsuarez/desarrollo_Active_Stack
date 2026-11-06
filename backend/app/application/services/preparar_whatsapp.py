"""Prepara notificaciones manuales pendientes sin enviar mensajes."""
from datetime import timedelta

from sqlalchemy import select

from app.domain.services.mensaje_whatsapp import construir_mensaje_whatsapp
from app.infrastructure.db.account_models import NotificacionModel
from app.infrastructure.db.models import ConsultorioModel, PacienteModel, ProfesionalModel, TurnoModel


class PrepararWhatsApp:
    def __init__(self, sesiones, reloj):
        self.sesiones = sesiones
        self.reloj = reloj

    async def ejecutar(self, consultorio_id: int) -> None:
        ahora = self.reloj.ahora()
        async with self.sesiones() as sesion:
            candidatos = (await sesion.execute(select(NotificacionModel.id, NotificacionModel.turno_id).where(
                NotificacionModel.consultorio_id == consultorio_id,
                NotificacionModel.canal == 'whatsapp', NotificacionModel.estado == 'programada',
                NotificacionModel.programada_para <= ahora,
            ).order_by(NotificacionModel.programada_para, NotificacionModel.id).limit(100))).all()
        for identificador, turno_id in candidatos:
            async with self.sesiones() as sesion, sesion.begin():
                turno = await sesion.scalar(select(TurnoModel).where(
                    TurnoModel.id == turno_id, TurnoModel.consultorio_id == consultorio_id,
                ).with_for_update())
                aviso = await sesion.scalar(select(NotificacionModel).where(
                    NotificacionModel.id == identificador, NotificacionModel.consultorio_id == consultorio_id,
                    NotificacionModel.canal == 'whatsapp', NotificacionModel.estado == 'programada',
                    NotificacionModel.programada_para <= ahora,
                ).with_for_update(skip_locked=True))
                if aviso is None:
                    continue
                if aviso.tipo in ('solicitud_confirmacion', 'recordatorio'):
                    consultorio = await sesion.get(ConsultorioModel, consultorio_id)
                    estados = ('pendiente',) if aviso.tipo == 'solicitud_confirmacion' else ('pendiente', 'confirmado')
                    horas = consultorio.horas_recordatorio if aviso.tipo == 'solicitud_confirmacion' else consultorio.horas_liberacion
                    if (turno is None or turno.ciclo_confirmacion != aviso.ciclo or turno.estado not in estados
                            or ahora >= turno.inicio - timedelta(hours=horas)):
                        aviso.estado = 'omitida'
                        continue
                    paciente = await sesion.get(PacienteModel, turno.paciente_id)
                    profesional = await sesion.get(ProfesionalModel, turno.profesional_id)
                    advierte = False
                    if (aviso.tipo == 'recordatorio' and turno.estado == 'pendiente'
                            and consultorio.modo_liberacion == 'automatico'
                            and turno.marcado_sin_confirmar_en is None):
                        enviada = await sesion.scalar(select(NotificacionModel.id).where(
                            NotificacionModel.consultorio_id == consultorio_id,
                            NotificacionModel.turno_id == turno.id,
                            NotificacionModel.tipo == 'solicitud_confirmacion',
                            NotificacionModel.canal == 'email', NotificacionModel.ciclo == turno.ciclo_confirmacion,
                            NotificacionModel.estado == 'enviada'))
                        advierte = enviada is not None
                    aviso.mensaje, aviso.enlace_whatsapp = construir_mensaje_whatsapp(
                        telefono=aviso.destinatario, paciente=f'{paciente.nombre} {paciente.apellido}',
                        profesional=f'{profesional.nombre} {profesional.apellido}', consultorio=consultorio.nombre,
                        fecha_hora=turno.inicio, zona_horaria=consultorio.zona_horaria,
                        accion='confirmar' if aviso.tipo == 'solicitud_confirmacion' else 'recordar',
                        liberacion_automatica=advierte)
                aviso.estado = 'preparada'
