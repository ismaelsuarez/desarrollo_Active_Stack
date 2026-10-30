import hashlib
import hmac
import ipaddress
import secrets

from pwdlib import PasswordHash

PASSWORD_HASH = PasswordHash.recommended()
DUMMY_HASH = PASSWORD_HASH.hash(secrets.token_hex(32))


def calcular_identificador_hash(identificador: str, secret: str) -> str:
    """Calcula HMAC-SHA256 del identificador normalizado (sin espacios y en minúsculas)."""
    normalizado = identificador.strip().lower()
    return hmac.new(
        secret.encode("utf-8"),
        normalizado.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def calcular_origen_hash(ip_origen: str | None, secret: str) -> str | None:
    """Calcula HMAC-SHA256 de la IP de origen, o retorna None si no se determinó."""
    if not ip_origen:
        return None
    return hmac.new(
        secret.encode("utf-8"),
        ip_origen.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def resolver_ip_origen(
    client_host: str | None,
    x_forwarded_for: str | None,
    trusted_hops: int = 0,
) -> str | None:
    """Resuelve la dirección IP de origen respetando los saltos de proxy confiables (DD-21)."""
    if trusted_hops <= 0:
        return client_host.strip() if client_host else None

    if not x_forwarded_for:
        return None

    hops = [hop.strip() for hop in x_forwarded_for.split(",") if hop.strip()]
    if len(hops) < trusted_hops:
        return None

    candidato = hops[-trusted_hops]
    try:
        ipaddress.ip_address(candidato)
        return candidato
    except ValueError:
        return None


def calcular_token_hash(raw_token: str) -> str:
    """Calcula el resumen SHA-256 en hexadecimal de un token opaco."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generar_token_opaco(bytes_len: int = 32) -> str:
    """Genera una cadena aleatoria criptográfica URL-safe."""
    return secrets.token_urlsafe(bytes_len)


def hashear_password(password: str) -> str:
    """Genera un hash Argon2id de la contraseña."""
    return PASSWORD_HASH.hash(password)


def verificar_password(password: str, password_hash: str) -> bool:
    """Verifica una contraseña contra su hash Argon2id."""
    return PASSWORD_HASH.verify(password, password_hash)


def verificar_dummy(password: str) -> bool:
    """Ejecuta una verificación contra DUMMY_HASH para mitigar ataques de temporización."""
    PASSWORD_HASH.verify(password, DUMMY_HASH)
    return False
