import uuid
import jwt

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj


class TokenError(Exception):
    """Error al procesar, emitir o validar un token."""


class AuthTokenService:
    """Servicio de emisión y validación de tokens de acceso JWT (HS256)."""

    def __init__(self, reloj: Reloj, secret_key: str, ttl_segundos: int = 900) -> None:
        self.reloj = reloj
        self.secret_key = secret_key
        self.ttl_segundos = ttl_segundos

    def emitir_access_token(self, principal: Principal) -> str:
        ahora = self.reloj.ahora()
        iat = int(ahora.timestamp())
        exp = iat + self.ttl_segundos

        payload = {
            "sub": str(principal.usuario_id),
            "consultorio_id": principal.consultorio_id,
            "rol": principal.rol.value if isinstance(principal.rol, RolUsuario) else str(principal.rol),
            "jti": str(uuid.uuid4()),
            "iat": iat,
            "exp": exp,
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")

    def decodificar_access_token(self, token: str) -> Principal:
        try:
            # Validamos firma y estructura con PyJWT; los tiempos se validan contra el puerto Reloj
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False, "verify_iat": False},
            )
        except jwt.PyJWTError as exc:
            raise TokenError(f"Firma de token inválida: {exc}") from exc

        ahora_timestamp = int(self.reloj.ahora().timestamp())
        exp = payload.get("exp")
        if exp is None or exp < ahora_timestamp:
            raise TokenError("Token expirado")

        sub = payload.get("sub")
        consultorio_id = payload.get("consultorio_id")
        rol_str = payload.get("rol")
        jti = payload.get("jti")

        if not sub or consultorio_id is None or not rol_str or not jti:
            raise TokenError("Token incompleto: claims obligatorios ausentes")

        try:
            usuario_id = int(sub)
            consultorio_id = int(consultorio_id)
            rol = RolUsuario(rol_str)
        except (ValueError, TypeError) as exc:
            raise TokenError(f"Contenido de claims inválido: {exc}") from exc

        return Principal(usuario_id=usuario_id, consultorio_id=consultorio_id, rol=rol)
