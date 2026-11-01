from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Decision:
    """Resultado inmutable de una evaluación de política de acceso."""

    permitido: bool
    motivo: str | None = None
    codigo_http: int | None = None
