"""Disponibilidad de agenda, sin efectos ni acceso a persistencia."""

from collections.abc import Sequence
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.domain.entities.turno import Turno
from app.domain.value_objects.estado_turno import ESTADOS_ACTIVOS
from app.domain.value_objects.intervalo import Intervalo


def calcular_disponibilidad(
    *, fecha: date, bloques: Sequence[tuple[time, time]],
    bloqueos: Sequence[tuple[datetime, datetime]], turnos: Sequence[Turno],
    duracion_min: int, granularidad: int, zona: str, ahora: datetime,
    dias_anticipacion_maxima: int,
) -> list[Intervalo]:
    """Devuelve huecos futuros en grilla, dentro del horizonte local inclusivo.

    El llamador entrega bloques del día y excepciones globales/propias ya
    filtrados por consultorio/profesional. También excluye el turno original
    al reprogramar. No se redondea la duración ni se modifican las entradas.
    """
    zona_local = ZoneInfo(zona)
    ultimo_dia = ahora.astimezone(zona_local).date() + timedelta(days=dias_anticipacion_maxima)
    if fecha > ultimo_dia:
        return []
    obstaculos = [*bloqueos, *(
        (turno.inicio, turno.fin) for turno in turnos if turno.estado in ESTADOS_ACTIVOS
    )]
    duracion = timedelta(minutes=duracion_min)
    paso = timedelta(minutes=granularidad)
    disponibles: list[Intervalo] = []
    for desde, hasta in bloques:
        inicio = datetime.combine(fecha, desde, tzinfo=zona_local)
        limite = datetime.combine(fecha, hasta, tzinfo=zona_local)
        while inicio + duracion <= limite:
            fin = inicio + duracion
            ocupado = any(inicio < hasta and fin > desde for desde, hasta in obstaculos)
            if inicio > ahora and not ocupado:
                disponibles.append(Intervalo(inicio, fin))
            inicio += paso
    return sorted(disponibles, key=lambda intervalo: intervalo.inicio)
