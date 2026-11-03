"""Mensajes de cuenta sin datos de la ficha del paciente."""

from urllib.parse import urlencode


_PLANTILLAS = {
    'verificacion_email': ('Verificá tu correo', '/verificar-email', 'Para verificar tu correo'),
    'recuperacion_password': ('Restablecé tu contraseña', '/restablecer-password', 'Para restablecer tu contraseña'),
}


def correo_cuenta(tipo: str, token: str, frontend_base_url: str) -> tuple[str, str]:
    try:
        asunto, ruta, instruccion = _PLANTILLAS[tipo]
    except KeyError as exc:
        raise ValueError('Tipo de correo de cuenta no soportado') from exc
    enlace = f'{frontend_base_url.rstrip("/")}{ruta}#{urlencode({"token": token})}'
    return asunto, f'{instruccion}, abrí este enlace:\n\n{enlace}\n'
