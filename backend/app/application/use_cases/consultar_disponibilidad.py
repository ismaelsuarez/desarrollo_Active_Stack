from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.application.errors_turnos import RechazoDeTurno
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo
from app.domain.ports.reloj import Reloj
from app.domain.services.disponibilidad import calcular_disponibilidad
from app.domain.value_objects.intervalo import Intervalo


class ConsultarDisponibilidad:
    def __init__(self, unidades: FabricaDeUnidadesDeTrabajo, reloj: Reloj) -> None:
        self._unidades, self._reloj = unidades, reloj

    async def consultar(self, consultorio_id: int, profesional_id: int,
                        prestacion_id: int, fecha: date) -> list[Intervalo]:
        async with self._unidades() as unidad:
            config = await unidad.agenda.obtener_configuracion(consultorio_id)
            profesional = await unidad.profesionales.obtener(consultorio_id, profesional_id)
            prestacion = await unidad.prestaciones.obtener(consultorio_id, prestacion_id)
            if any(recurso is None for recurso in (config, profesional, prestacion)):
                raise RechazoDeTurno(404, 'Recurso no encontrado')
            zona = ZoneInfo(config.zona_horaria)
            hoy = self._reloj.ahora().astimezone(zona).date()
            if (fecha - hoy).days > config.dias_anticipacion_maxima:
                return []
            desde = datetime.combine(fecha, time.min, tzinfo=zona)
            hasta = desde + timedelta(days=1)
            bloques = await unidad.agenda.bloques(consultorio_id, profesional_id, fecha.isoweekday())
            bloqueos = await unidad.agenda.bloqueos(consultorio_id, profesional_id, desde=desde, hasta=hasta)
            turnos = await unidad.agenda.ocupacion(consultorio_id, profesional_id, desde, hasta)
            return calcular_disponibilidad(fecha=fecha, bloques=bloques, bloqueos=bloqueos,
                turnos=turnos, duracion_min=prestacion.duracion_min,
                granularidad=config.minutos_granularidad, zona=config.zona_horaria,
                ahora=self._reloj.ahora(), dias_anticipacion_maxima=config.dias_anticipacion_maxima)

    async def alternativas(self, consultorio_id: int, profesional_id: int,
                            prestacion_id: int, inicio: datetime, *,
                            duracion_min: int | None = None,
                            excluir_id: int | None = None) -> list[Intervalo]:
        """Lectura independiente: invocar después de terminar rollback de la escritura."""
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            config = await unidad.agenda.obtener_configuracion(consultorio_id)
            profesional = await unidad.profesionales.obtener(consultorio_id, profesional_id)
            prestacion = await unidad.prestaciones.obtener(consultorio_id, prestacion_id,
                incluir_inactivos=duracion_min is not None)
            if any(recurso is None for recurso in (config, profesional, prestacion)):
                return []
            zona = ZoneInfo(config.zona_horaria)
            fecha = max(inicio.astimezone(zona).date(), ahora.astimezone(zona).date())
            ultima = ahora.astimezone(zona).date() + timedelta(days=config.dias_anticipacion_maxima)
            if fecha > ultima:
                return []
            desde = datetime.combine(fecha, time.min, tzinfo=zona)
            hasta = datetime.combine(ultima + timedelta(days=1), time.min, tzinfo=zona)
            turnos = [t for t in await unidad.agenda.ocupacion(consultorio_id, profesional_id, desde, hasta)
                      if t.id != excluir_id]
            bloqueos = await unidad.agenda.bloqueos(consultorio_id, profesional_id, desde=desde, hasta=hasta)
            semanales = {}
            resultado = []
            while fecha <= ultima:
                dia = fecha.isoweekday()
                if dia not in semanales:
                    semanales[dia] = await unidad.agenda.bloques(consultorio_id, profesional_id, dia)
                intervalos = calcular_disponibilidad(fecha=fecha, bloques=semanales[dia], bloqueos=bloqueos,
                    turnos=turnos, duracion_min=duracion_min if duracion_min is not None else prestacion.duracion_min,
                    granularidad=config.minutos_granularidad, zona=config.zona_horaria,
                    ahora=ahora, dias_anticipacion_maxima=config.dias_anticipacion_maxima)
                resultado.extend(intervalo for intervalo in intervalos if intervalo.inicio >= inicio)
                if len(resultado) >= 3:
                    return resultado[:3]
                fecha += timedelta(days=1)
            return resultado
