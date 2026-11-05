"""Cuota compartida de lecturas públicas; su alcance es un proceso de API."""
from datetime import datetime, timedelta
from math import ceil


class LimitePublico:
    def __init__(self, cuota: int = 60, ventana_segundos: int = 60,
                 capacidad: int = 10000) -> None:
        if min(cuota, ventana_segundos, capacidad) <= 0:
            raise ValueError("La cuota, ventana y capacidad deben ser positivas")
        self._cuota = cuota
        self._capacidad = capacidad
        self._ventana = timedelta(seconds=ventana_segundos)
        self._origenes: dict[str, tuple[datetime, int]] = {}

    def consumir(self, origen: str, ahora: datetime) -> int:
        """Devuelve cero si admite; de lo contrario segundos hasta reintentar."""
        vencidos = [clave for clave, (inicio, _) in self._origenes.items()
                    if ahora >= inicio + self._ventana]
        for clave in vencidos:
            del self._origenes[clave]
        if origen not in self._origenes and len(self._origenes) >= self._capacidad:
            primero = min(inicio for inicio, _ in self._origenes.values())
            return max(1, ceil((primero + self._ventana - ahora).total_seconds()))
        inicio, cantidad = self._origenes.get(origen, (ahora, 0))
        if ahora >= inicio + self._ventana:
            inicio, cantidad = ahora, 0
        if cantidad >= self._cuota:
            return max(1, ceil((inicio + self._ventana - ahora).total_seconds()))
        self._origenes[origen] = inicio, cantidad + 1
        return 0
