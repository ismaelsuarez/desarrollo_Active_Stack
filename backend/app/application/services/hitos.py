"""Planificación sobre la misma unidad de trabajo del cambio del turno."""
from datetime import datetime

from app.application.ports.unidad_de_trabajo import UnidadDeTrabajo
from app.domain.entities.turno import Turno
from app.domain.policies.hitos import programacion_hitos


class ProgramadorHitos:
    async def planificar(self, unidad: UnidadDeTrabajo, turno: Turno,
                         accion: str, ahora: datetime) -> None:
        if accion in ("reprogramar", "cancelar", "liberar"):
            ciclo = turno.ciclo_confirmacion - 1 if accion == "reprogramar" else turno.ciclo_confirmacion
            await unidad.notificaciones.omitir_hitos(turno, ciclo)
        if accion in ("cancelar", "liberar"):
            return
        config = await unidad.agenda.obtener_configuracion(turno.consultorio_id)
        for tipo, para in programacion_hitos(
            turno.inicio, turno.estado, ahora,
            horas_confirmacion=config.horas_confirmacion,
            horas_recordatorio=config.horas_recordatorio,
        ):
            await unidad.notificaciones.programar_hito(turno, tipo, para)
