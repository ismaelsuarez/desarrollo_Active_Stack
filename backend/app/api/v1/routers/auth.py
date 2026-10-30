from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    consultorio_sin_token,
    get_auth_service,
    get_sesion,
    get_settings,
    usuario_actual,
)
from app.api.v1.schemas.auth import (
    LoginRequest,
    MensajeResponse,
    TokenResponse,
    UsuarioPerfilResponse,
)
from app.application.services.auth_service import (
    AuthService,
    CredencialesInvalidasError,
    EmailNoVerificadoError,
    SesionInvalidaError,
)
from app.core.config import Settings
from app.domain.entities.auth import Principal
from app.infrastructure.db.models import ConsultorioModel, UsuarioModel

router = APIRouter(prefix="/api/v1/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    consultorio: ConsultorioModel = Depends(consultorio_sin_token),
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Inicia sesión con credenciales, emitiendo JWT y cookie refresh_token (RN-02, RN-06, RN-09)."""
    client_host = request.client.host if request.client else None
    x_forwarded_for = request.headers.get("x-forwarded-for")

    try:
        access_token, raw_refresh_token, _ = await auth_service.login(
            consultorio_id=consultorio.id,
            identificador=payload.identificador,
            password=payload.password,
            client_host=client_host,
            x_forwarded_for=x_forwarded_for,
        )
    except CredencialesInvalidasError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        ) from exc
    except EmailNoVerificadoError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    # Fijar cookie segura de refresh token (DD-26)
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh_token,
        max_age=604800,  # 7 días
        path="/api/v1/auth",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )

    return TokenResponse(access_token=access_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    """Rota atómicamente el refresh token recibido por cookie (RN-59, Regla Dura 1)."""
    raw_refresh = request.cookies.get("refresh_token")
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de renovación ausente",
        )

    try:
        nuevo_access, nuevo_refresh, _ = await auth_service.refresh(raw_refresh)
    except SesionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    response.set_cookie(
        key="refresh_token",
        value=nuevo_refresh,
        max_age=604800,
        path="/api/v1/auth",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )

    return TokenResponse(access_token=nuevo_access)


@router.post("/logout", response_model=MensajeResponse)
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> MensajeResponse:
    """Cierra la sesión activa revocando el refresh token y limpiando la cookie."""
    raw_refresh = request.cookies.get("refresh_token")
    if raw_refresh:
        await auth_service.logout(raw_refresh)

    response.delete_cookie(
        key="refresh_token",
        path="/api/v1/auth",
        httponly=True,
        samesite="strict",
        secure=settings.cookie_secure,
    )

    return MensajeResponse(mensaje="Sesión cerrada exitosamente")


@router.get("/me", response_model=UsuarioPerfilResponse)
async def perfil_usuario(
    principal: Principal = Depends(usuario_actual),
    sesion: AsyncSession = Depends(get_sesion),
) -> UsuarioPerfilResponse:
    """Retorna el perfil del usuario autenticado a partir del Principal (RN-06)."""
    usuario = await sesion.scalar(
        select(UsuarioModel).where(
            UsuarioModel.id == principal.usuario_id,
            UsuarioModel.consultorio_id == principal.consultorio_id,
        )
    )
    if usuario is None or not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo o inexistente",
        )

    return UsuarioPerfilResponse(
        id=usuario.id,
        consultorio_id=usuario.consultorio_id,
        nombre_usuario=usuario.nombre_usuario,
        email=usuario.email,
        rol=usuario.rol,
        email_verificado=usuario.email_verificado,
    )
