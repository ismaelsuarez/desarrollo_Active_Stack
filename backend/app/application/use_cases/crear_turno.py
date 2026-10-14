from app.application.dto.crear_turno import SolicitudDeTurno
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo
from app.domain.entities.turno import (
    NuevoTurno,
    Turno,
    calcular_fin,
    exigir_zona_horaria,
)
from app.domain.errors import PrestacionInexistente, ProfesionalInexistente


class CrearTurno:
    """Crea un turno de un paciente con un profesional.

    No consulta los turnos existentes: el solapamiento lo rechaza la base de
    datos al guardar (RN-17, DD-08), también entre reservas simultáneas.
    """

    def __init__(self, unidades_de_trabajo: FabricaDeUnidadesDeTrabajo) -> None:
        self._unidades_de_trabajo = unidades_de_trabajo

    async def ejecutar(self, solicitud: SolicitudDeTurno) -> Turno:
        exigir_zona_horaria(solicitud.inicio)

        async with self._unidades_de_trabajo() as unidad:
            profesional = await unidad.profesionales.obtener(
                solicitud.consultorio_id, solicitud.profesional_id
            )
            if profesional is None:
                raise ProfesionalInexistente()
            prestacion = await unidad.prestaciones.obtener(
                solicitud.consultorio_id, solicitud.prestacion_id
            )
            if prestacion is None:
                raise PrestacionInexistente()
            return await unidad.turnos.guardar(
                NuevoTurno(
                    consultorio_id=solicitud.consultorio_id,
                    paciente_id=solicitud.paciente_id,
                    profesional_id=profesional.id,
                    box_id=profesional.box_id,
                    prestacion_id=prestacion.id,
                    inicio=solicitud.inicio,
                    fin=calcular_fin(solicitud.inicio, prestacion.duracion_min),
                )
            )
