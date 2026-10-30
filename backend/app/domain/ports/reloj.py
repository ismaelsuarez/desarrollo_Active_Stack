from datetime import datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

ZONA_HORARIA_CONSULTORIO = ZoneInfo("America/Argentina/Buenos_Aires")


class Reloj(Protocol):
    """Puerto para abstraer la obtención de fecha y hora consciente de zona."""

    def ahora(self) -> datetime:
        """Retorna el instante actual en la zona horaria del consultorio."""
        ...


class RelojSistema:
    """Implementación real basada en el reloj del sistema operativo."""

    def __init__(self, zona_horaria: ZoneInfo = ZONA_HORARIA_CONSULTORIO) -> None:
        self._zona_horaria = zona_horaria

    def ahora(self) -> datetime:
        return datetime.now(self._zona_horaria)


class RelojSimulado:
    """Implementación determinística para pruebas o simulaciones temporales."""

    def __init__(
        self,
        instante_inicial: datetime,
        zona_horaria: ZoneInfo = ZONA_HORARIA_CONSULTORIO,
    ) -> None:
        if instante_inicial.tzinfo is None:
            raise ValueError("El instante inicial del RelojSimulado no puede ser naive.")
        self._zona_horaria = zona_horaria
        self._actual = instante_inicial.astimezone(self._zona_horaria)

    def ahora(self) -> datetime:
        return self._actual

    def avanzar(self, lapso: timedelta) -> None:
        self._actual += lapso

    def fijar(self, nuevo_instante: datetime) -> None:
        if nuevo_instante.tzinfo is None:
            raise ValueError("El nuevo instante del RelojSimulado no puede ser naive.")
        self._actual = nuevo_instante.astimezone(self._zona_horaria)
