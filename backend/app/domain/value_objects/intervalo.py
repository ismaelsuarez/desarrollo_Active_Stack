from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Intervalo:
    """Intervalo de tiempo semicerrado [inicio, fin) con zona horaria obligatoria."""

    inicio: datetime
    fin: datetime

    def __post_init__(self) -> None:
        if self.inicio.tzinfo is None or self.fin.tzinfo is None:
            raise ValueError("inicio y fin deben tener zona horaria explícita")
        if self.inicio >= self.fin:
            raise ValueError("inicio debe ser menor que fin")

    def duracion_minutos(self) -> int:
        delta = self.fin - self.inicio
        return int(delta.total_seconds() // 60)

    def solapa_con(self, otro: "Intervalo") -> bool:
        """Determina si dos intervalos semicerrados [inicio, fin) se superponen."""
        return max(self.inicio, otro.inicio) < min(self.fin, otro.fin)

    def contiene(self, instante: datetime) -> bool:
        """Verifica si un instante está comprendido en [inicio, fin)."""
        return self.inicio <= instante < self.fin
