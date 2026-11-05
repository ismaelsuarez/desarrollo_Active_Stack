from typing import Protocol


class Planificador(Protocol):
    """Dispara el mismo barrido desde HTTP o desde el bucle local."""

    async def ejecutar(self, consultorio_id: int) -> object: ...
