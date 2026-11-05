"""Decisión de RN-60 a partir de hechos del ciclo, sin efectos externos."""
from datetime import datetime, timedelta


def decidir_sin_confirmar(*, estado: str, inicio: datetime, ahora: datetime,
                         marca: datetime | None, modo: str, solicitud_enviada: bool,
                         horas_liberacion: int) -> str | None:
    if estado != 'pendiente' or marca is not None or inicio <= ahora:
        return None
    if ahora < inicio - timedelta(hours=horas_liberacion):
        return None
    return 'liberar' if modo == 'automatico' and solicitud_enviada else 'marcar_sin_confirmar'
