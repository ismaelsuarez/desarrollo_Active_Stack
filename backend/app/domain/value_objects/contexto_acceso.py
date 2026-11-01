from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ContextoAcceso:
    """Datos contextuales requeridos por las políticas puras que no viajan en el token."""

    ahora: datetime
    ficha_vigente_id: int | None = None
    profesional_vinculado_id: int | None = None
    ficha_usuario_id: int | None = None
    horas_limite_cancelacion: int = 24
    consultorio_modo_manual: bool = False
    turno_sin_confirmar: bool = False
    turnos_del_profesional: frozenset[int] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if self.ahora.tzinfo is None:
            raise ValueError("ahora debe tener zona horaria explícita")
