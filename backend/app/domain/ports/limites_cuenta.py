from typing import Protocol


class LimitesCorreoCuenta(Protocol):
    async def correo_permitido(self, consultorio_id: int, usuario_id: int, tipo: str) -> bool:
        """Comprueba el límite durable sin revelar existencia de la cuenta."""
        ...
