"""Reglas puras de reserva por el personal (RN-14 y RN-64)."""

from collections.abc import Sequence
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.domain.value_objects.estado_turno import EstadoTurno


def estado_inicial(
    inicio: datetime, ahora: datetime, horas_confirmacion: int, confirmar: bool = False,
) -> EstadoTurno:
    """Estado al crear o reprogramar según RN-23 y RN-29."""
    if confirmar or (inicio - ahora).total_seconds() < horas_confirmacion * 3600:
        return EstadoTurno.CONFIRMADO
    return EstadoTurno.PENDIENTE


def duracion_turno(catalogo: int, ajustada: int | None, granularidad: int) -> int:
    """Conserva la duración de catálogo salvo ajuste del personal (RN-64)."""
    if ajustada is None:
        return catalogo
    if ajustada <= 0 or ajustada % granularidad:
        raise ValueError("La duración ajustada debe ser positiva y múltiplo de la grilla")
    return ajustada


def validar_intervalo(
    inicio: datetime,
    fin: datetime,
    bloques: Sequence[tuple[time, time]],
    bloqueos: Sequence[tuple[datetime, datetime]],
    granularidad: int,
    zona: str,
) -> None:
    """Comprueba el intervalo completo contra los bloques del día y excepciones."""
    if inicio.utcoffset() is None or fin.utcoffset() is None:
        raise ValueError("El intervalo debe indicar zona horaria")
    if fin <= inicio:
        raise ValueError("El fin debe ser posterior al inicio")
    zona_local = ZoneInfo(zona)
    inicio_local = inicio.astimezone(zona_local)
    fin_local = fin.astimezone(zona_local)
    if inicio_local.date() != fin_local.date():
        raise ValueError("El intervalo debe caber en un bloque del día")
    for desde, hasta in bloques:
        ancla = datetime.combine(inicio_local.date(), desde, tzinfo=zona_local)
        limite = datetime.combine(inicio_local.date(), hasta, tzinfo=zona_local)
        if ancla <= inicio_local < fin_local <= limite:
            if (inicio_local - ancla).total_seconds() % (granularidad * 60):
                raise ValueError("El inicio debe pertenecer a la grilla del bloque")
            break
    else:
        raise ValueError("El intervalo debe caber en un bloque del día")
    if any(inicio < hasta and fin > desde for desde, hasta in bloqueos):
        raise ValueError("El intervalo intersecta un bloqueo")
