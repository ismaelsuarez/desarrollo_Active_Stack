"""Bucle opcional de la API; cada invocación posee sus propias sesiones."""
import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.domain.ports.planificador import Planificador

logger = logging.getLogger(__name__)


class BucleBarrido:
    def __init__(self, planificador: Planificador, consultorio_id: int,
                 intervalo: int, esperar: Callable[[float], Awaitable[None]] = asyncio.sleep):
        self.planificador = planificador
        self.consultorio_id = consultorio_id
        self.intervalo = intervalo
        self.esperar = esperar

    async def ejecutar(self) -> None:
        while True:
            try:
                await self.planificador.ejecutar(self.consultorio_id)
            except Exception:
                # Deliberately omit exception text and traceback: providers can
                # include addresses, credentials or SQL parameter values.
                logger.error("barrido_en_proceso_fallido")
            await self.esperar(self.intervalo)
