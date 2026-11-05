"""Calendario de comunicaciones desde el inicio, sin reloj global ni efectos."""
from datetime import datetime, timedelta

from app.domain.value_objects.estado_turno import EstadoTurno


def programacion_hitos(inicio: datetime, estado: EstadoTurno, ahora: datetime, *,
                       horas_confirmacion: int, horas_recordatorio: int
                       ) -> tuple[tuple[str, datetime], ...]:
    if estado not in (EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO):
        return ()
    hitos = []
    confirmacion = inicio - timedelta(hours=horas_confirmacion)
    recordatorio = inicio - timedelta(hours=horas_recordatorio)
    if estado == EstadoTurno.PENDIENTE and confirmacion >= ahora:
        hitos.append(("solicitud_confirmacion", confirmacion))
    if recordatorio > ahora:
        hitos.append(("recordatorio", recordatorio))
    return tuple(hitos)
