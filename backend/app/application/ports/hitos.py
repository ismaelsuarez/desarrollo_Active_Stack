from datetime import datetime
from typing import Protocol

from app.application.ports.unidad_de_trabajo import UnidadDeTrabajo
from app.domain.entities.turno import Turno


class PlanificadorDeHitos(Protocol):
    """Contrato transaccional de C-16, invocado antes del commit.

    La implementación recibe la misma unidad de trabajo para que sus
    escrituras se confirmen o reviertan junto al turno y su historial. No debe
    hacer commit, enviar correo ni abrir una transacción independiente.
    """

    async def planificar(self, unidad: UnidadDeTrabajo, turno: Turno,
                         accion: str, ahora: datetime) -> None: ...


class PlanificadorSinEfectos:
    """C-07 deja el punto de integración sin programar ni despachar avisos.

    La planificación real, omisión de hitos viejos, barridos, SMTP y WhatsApp
    pertenecen a sus changes posteriores. Este adaptador no escribe filas.
    """

    async def planificar(self, unidad: UnidadDeTrabajo, turno: Turno,
                         accion: str, ahora: datetime) -> None:
        return None
