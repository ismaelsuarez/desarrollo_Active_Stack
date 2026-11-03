from email.message import EmailMessage
import asyncio

import aiosmtplib

from app.core.config import Settings
from app.domain.ports.correo import ErrorEnvioCorreo


class EnviadorSMTP:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def enviar(self, destinatario: str, asunto: str, cuerpo: str) -> None:
        mensaje = EmailMessage()
        mensaje['From'] = self.settings.smtp_from
        mensaje['To'] = destinatario
        mensaje['Subject'] = asunto
        mensaje.set_content(cuerpo)
        try:
            # aiosmtplib's timeout is per socket operation. Bound the complete
            # exchange too, so several slow commands cannot outlive the claim.
            async with asyncio.timeout(self.settings.smtp_timeout_seconds):
                await aiosmtplib.send(
                    mensaje,
                    hostname=self.settings.smtp_host,
                    port=self.settings.smtp_port,
                    username=self.settings.smtp_user,
                    password=(self.settings.smtp_password.get_secret_value()
                              if self.settings.smtp_password else None),
                    start_tls=self.settings.smtp_starttls,
                    use_tls=False,
                    timeout=self.settings.smtp_timeout_seconds,
                )
        except (aiosmtplib.SMTPException, OSError, TimeoutError):
            raise ErrorEnvioCorreo('No se pudo enviar el correo') from None
