from datetime import timedelta
from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.rate_limiter import LoginRateLimiter
from app.application.services.token_service import AuthTokenService
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.domain.services.auth_crypto import (
    calcular_token_hash,
    generar_token_opaco,
    verificar_dummy,
    verificar_password,
)
from app.infrastructure.db.models import RefreshTokenModel, UsuarioModel


class AuthError(Exception):
    """Excepción base de errores de autenticación."""


class CredencialesInvalidasError(AuthError):
    """Credenciales de acceso inválidas o usuario inactivo."""


class EmailNoVerificadoError(AuthError):
    """La cuenta de paciente no ha verificado su correo electrónico."""


class SesionInvalidaError(AuthError):
    """Token de sesión expirado, revocado o reutilizado."""


class AuthService:
    """Orquestador de autenticación, verificación Argon2 y rotación de refresh tokens."""

    def __init__(
        self,
        sesion: AsyncSession,
        reloj: Reloj,
        token_service: AuthTokenService,
        rate_limiter: LoginRateLimiter,
        refresh_token_ttl_dias: int = 7,
    ) -> None:
        self.sesion = sesion
        self.reloj = reloj
        self.token_service = token_service
        self.rate_limiter = rate_limiter
        self.refresh_token_ttl_dias = refresh_token_ttl_dias

    async def login(
        self,
        consultorio_id: int,
        identificador: str,
        password: str,
        client_host: str | None,
        x_forwarded_for: str | None,
    ) -> tuple[str, str, Principal]:
        """Autentica credenciales, mitigando temporización y emitiendo tokens."""
        # 1. Rate limiting y bloqueo por par u origen (RN-09, DD-25)
        bloqueado, id_hash, orig_hash = await self.rate_limiter.registrar_intento_y_verificar_bloqueo(
            consultorio_id=consultorio_id,
            identificador=identificador,
            client_host=client_host,
            x_forwarded_for=x_forwarded_for,
        )
        if bloqueado:
            # Respuesta genérica inmediata sin computar contraseña
            raise CredencialesInvalidasError("Credenciales inválidas")

        # Keep the account locked from password validation through issuance.
        # Reset either precedes this read or revokes the newly issued session.
        # 2. Búsqueda de usuario por nombre de usuario o email normalizado
        id_norm = identificador.strip().lower()
        stmt = select(UsuarioModel).where(
            UsuarioModel.consultorio_id == consultorio_id,
            or_(
                UsuarioModel.nombre_usuario == id_norm,
                UsuarioModel.email == id_norm,
            ),
        ).execution_options(populate_existing=True).with_for_update()
        usuario = await self.sesion.scalar(stmt)

        # 3. Mitigación de timing si no existe o está inactivo
        if usuario is None or not usuario.activo:
            verificar_dummy(password)
            raise CredencialesInvalidasError("Credenciales inválidas")

        # 4. Verificación de contraseña real con Argon2
        if not verificar_password(password, usuario.password_hash):
            raise CredencialesInvalidasError("Credenciales inválidas")

        # 5. Prevención de enumeración: verificación de email de paciente (RN-02)
        if usuario.rol == RolUsuario.PACIENTE.value and not usuario.email_verificado:
            raise EmailNoVerificadoError("El correo electrónico de la cuenta requiere verificación.")

        # 6. Éxito: limpieza de intentos del par (RN-09)
        await self.rate_limiter.limpiar_intentos_exitosos(
            consultorio_id=consultorio_id,
            identificador_hash=id_hash,
            origen_hash=orig_hash,
            confirmar=False,
        )

        ahora = self.reloj.ahora()
        usuario.ultimo_ingreso_en = ahora

        # Emisión de Access Token JWT
        principal = Principal(
            usuario_id=usuario.id,
            consultorio_id=usuario.consultorio_id,
            rol=RolUsuario(usuario.rol),
        )
        access_token = self.token_service.emitir_access_token(principal)

        # Emisión de Refresh Token seguro
        raw_refresh_token = generar_token_opaco(32)
        token_hash = calcular_token_hash(raw_refresh_token)
        expira_en = ahora + timedelta(days=self.refresh_token_ttl_dias)

        refresh_model = RefreshTokenModel(
            consultorio_id=usuario.consultorio_id,
            usuario_id=usuario.id,
            token_hash=token_hash,
            expira_en=expira_en,
            creado_en=ahora,
        )
        self.sesion.add(refresh_model)
        await self.sesion.commit()

        return (access_token, raw_refresh_token, principal)

    async def refresh(self, raw_refresh_token: str) -> tuple[str, str, Principal]:
        """Rota atómicamente el refresh token con detección de repetición e invalidación en cascada."""
        if not raw_refresh_token:
            raise SesionInvalidaError("Token de renovación ausente")

        token_hash = calcular_token_hash(raw_refresh_token)
        token_model = await self.sesion.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        if token_model is None:
            raise SesionInvalidaError("Token de renovación inválido")

        # Password reset and account operations lock the user before its tokens.
        # Serialize in that same order, then reload the token: the initial read
        # can predate a reset committed while this request was already in flight.
        usuario = await self.sesion.scalar(
            select(UsuarioModel).where(
                UsuarioModel.id == token_model.usuario_id,
                UsuarioModel.consultorio_id == token_model.consultorio_id,
            ).execution_options(populate_existing=True).with_for_update()
        )
        if usuario is None or not usuario.activo:
            raise SesionInvalidaError("Usuario inactivo o inexistente")

        token_model = await self.sesion.scalar(
            select(RefreshTokenModel).where(
                RefreshTokenModel.id == token_model.id,
                RefreshTokenModel.consultorio_id == usuario.consultorio_id,
                RefreshTokenModel.usuario_id == usuario.id,
            ).execution_options(populate_existing=True).with_for_update()
        )
        if token_model is None:
            raise SesionInvalidaError("Token de renovación inválido")

        ahora = self.reloj.ahora()

        # Detección de ataque de reuso: token ya revocado o reemplazado previamente
        if token_model.revocado_en is not None or token_model.reemplazado_por_id is not None:
            # Revocación en cascada de todas las sesiones de la cuenta
            await self.sesion.execute(
                update(RefreshTokenModel)
                .where(
                    RefreshTokenModel.usuario_id == token_model.usuario_id,
                    RefreshTokenModel.consultorio_id == token_model.consultorio_id,
                    RefreshTokenModel.revocado_en.is_(None),
                )
                .values(revocado_en=ahora)
            )
            await self.sesion.commit()
            raise SesionInvalidaError("Token de renovación reutilizado; sesiones revocadas")

        # Expiración
        if token_model.expira_en < ahora:
            raise SesionInvalidaError("Token de renovación expirado")

        # Rotación atómica
        nuevo_raw = generar_token_opaco(32)
        nuevo_hash = calcular_token_hash(nuevo_raw)
        nueva_exp = ahora + timedelta(days=self.refresh_token_ttl_dias)

        nuevo_model = RefreshTokenModel(
            consultorio_id=usuario.consultorio_id,
            usuario_id=usuario.id,
            token_hash=nuevo_hash,
            expira_en=nueva_exp,
            creado_en=ahora,
        )
        self.sesion.add(nuevo_model)
        await self.sesion.flush()

        token_model.reemplazado_por_id = nuevo_model.id
        token_model.revocado_en = ahora

        principal = Principal(
            usuario_id=usuario.id,
            consultorio_id=usuario.consultorio_id,
            rol=RolUsuario(usuario.rol),
        )
        access_token = self.token_service.emitir_access_token(principal)
        await self.sesion.commit()

        return (access_token, nuevo_raw, principal)

    async def logout(self, raw_refresh_token: str | None) -> None:
        """Revoca la sesión activa del refresh token provisto."""
        if not raw_refresh_token:
            return

        token_hash = calcular_token_hash(raw_refresh_token)
        token_model = await self.sesion.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        if token_model is not None and token_model.revocado_en is None:
            token_model.revocado_en = self.reloj.ahora()
            await self.sesion.commit()
