from typing import Protocol


class ErrorEnvioCorreo(Exception):
    """Fallo de transporte sin información privada del proveedor."""


class EnviadorCorreo(Protocol):
    async def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        """Entrega un mensaje o informa el fallo al caso de uso."""
        ...
