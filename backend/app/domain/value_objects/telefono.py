import re


def normalizar_telefono(valor: str | None) -> str | None:
    """Devuelve dígitos internacionales o None si el formato es ambiguo."""
    if not valor:
        return None
    valor = valor.strip()
    if not re.fullmatch(r'\+?[0-9 ()\-.]+', valor, flags=re.ASCII):
        return None
    internacional = valor.startswith('+')
    digitos = ''.join(c for c in valor if c.isascii() and c.isdigit())
    if not internacional and digitos.startswith('00'):
        internacional, digitos = True, digitos[2:]
    if internacional:
        return digitos if 8 <= len(digitos) <= 15 and not digitos.startswith('0') else None
    if not digitos.startswith('0'):
        return None
    nacional = digitos[1:]
    if len(nacional) == 10 and not nacional.startswith('0'):
        return '54' + nacional
    if len(nacional) == 12:
        candidatos = [nacional[:i] + nacional[i + 2:] for i in (2, 3, 4)
                      if nacional[i:i + 2] == '15' and nacional[0] != '0']
        if len(candidatos) == 1:
            return '549' + candidatos[0]
    return None
