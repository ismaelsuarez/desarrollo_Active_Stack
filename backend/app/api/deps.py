from collections.abc import AsyncIterator, Callable
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.auth_service import AuthService
from app.application.services.rate_limiter import LoginRateLimiter
from app.application.services.token_service import AuthTokenService, TokenError
from app.core.config import Settings


def get_settings(request: Request) -> Settings:
    """Obtiene la configuración activa asociada al ciclo de vida de la aplicación."""
    if hasattr(request.app.state, "settings") and request.app.state.settings is not None:
        return request.app.state.settings
    from app.core.config import get_settings as core_get_settings
    return core_get_settings()
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj, RelojSistema
from app.infrastructure.db.models import ConsultorioModel
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_reloj() -> Reloj:
    """Retorna la implementación del puerto Reloj."""
    return RelojSistema()


async def get_sesion(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> AsyncIterator[AsyncSession]:
    """Genera una sesión de base de datos asíncrona única por solicitud (Regla Dura 10)."""
    if not hasattr(request.app.state, "session_factory"):
        engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.engine = engine
        request.app.state.session_factory = crear_fabrica_de_sesiones(engine)

    async with request.app.state.session_factory() as sesion:
        yield sesion


def get_token_service(
    reloj: Reloj = Depends(get_reloj),
    settings: Settings = Depends(get_settings),
) -> AuthTokenService:
    return AuthTokenService(
        reloj=reloj,
        secret_key=settings.jwt_secret_key.get_secret_value(),
    )


def get_rate_limiter(
    sesion: AsyncSession = Depends(get_sesion),
    reloj: Reloj = Depends(get_reloj),
    settings: Settings = Depends(get_settings),
) -> LoginRateLimiter:
    return LoginRateLimiter(
        sesion=sesion,
        reloj=reloj,
        origin_hash_secret=settings.origin_hash_secret.get_secret_value(),
        login_max_attempts=settings.login_max_attempts,
        login_lockout_minutes=settings.login_lockout_minutes,
        login_max_attempts_per_origin=settings.login_max_attempts_per_origin,
        trusted_proxy_hops=settings.trusted_proxy_hops,
    )


def get_auth_service(
    sesion: AsyncSession = Depends(get_sesion),
    reloj: Reloj = Depends(get_reloj),
    token_service: AuthTokenService = Depends(get_token_service),
    rate_limiter: LoginRateLimiter = Depends(get_rate_limiter),
) -> AuthService:
    return AuthService(
        sesion=sesion,
        reloj=reloj,
        token_service=token_service,
        rate_limiter=rate_limiter,
    )


def usuario_actual(
    token: str | None = Depends(oauth2_scheme),
    token_service: AuthTokenService = Depends(get_token_service),
) -> Principal:
    """Extrae y valida el token JWT retornando el Principal autenticado."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return token_service.decodificar_access_token(token)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def requiere_rol(*roles: RolUsuario) -> Callable[[Principal], Principal]:
    """Fábrica de dependencias RBAC con denegación por defecto (403 Forbidden)."""

    def verificar_rol(principal: Principal = Depends(usuario_actual)) -> Principal:
        if principal.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permisos insuficientes para realizar esta acción",
            )
        return principal

    return verificar_rol


async def consultorio_sin_token(
    settings: Settings = Depends(get_settings),
    sesion: AsyncSession = Depends(get_sesion),
) -> ConsultorioModel:
    """Resuelve el consultorio activo configurado para endpoints sin token (RN-55, RN-59, Regla 1)."""
    cid = settings.consultorio_activo_id
    consultorio = await sesion.scalar(
        select(ConsultorioModel).where(ConsultorioModel.id == cid)
    )
    if consultorio is None or not consultorio.activo:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Consultorio configurado no disponible o inactivo",
        )
    return consultorio
