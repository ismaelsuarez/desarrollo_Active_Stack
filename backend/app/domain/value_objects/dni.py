import re
from dataclasses import dataclass

from app.domain.errors import DniInvalido

_REGEX_DNI = re.compile(r"^[0-9]+$")


@dataclass(frozen=True, slots=True)
class Dni:
    """Documento Nacional de Identidad normalizado (solo dígitos numéricos)."""

    valor: str

    def __init__(self, valor: str) -> None:
        normalizado = str(valor).strip()
        if not normalizado or not _REGEX_DNI.match(normalizado):
            raise DniInvalido()
        object.__setattr__(self, "valor", normalizado)

    def __str__(self) -> str:
        return self.valor
