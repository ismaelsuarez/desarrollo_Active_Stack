"""Repositorio PostgreSQL de cuentas, con filtros de consultorio explícitos."""
from datetime import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import UsuarioModel, PacienteModel, TokenUsuarioModel, RefreshTokenModel
from app.infrastructure.db.account_models import NotificacionModel, SolicitudVinculacionModel


class RepositorioCuentas:
    def __init__(self, sesion: AsyncSession):
        self.sesion = sesion

    async def crear_usuario(self, consultorio_id: int, nombre_usuario: str,
                            email: str, password_hash: str, version: str,
                            ahora: datetime) -> UsuarioModel:
        user = UsuarioModel(consultorio_id=consultorio_id,
            nombre_usuario=nombre_usuario.strip().lower(), email=email.strip().lower(),
            password_hash=password_hash, rol='paciente', email_verificado=False,
            aviso_privacidad_aceptado_en=ahora, aviso_privacidad_version=version,
            creado_en=ahora, actualizado_en=ahora)
        self.sesion.add(user)
        await self.sesion.flush()
        return user

    async def crear_ficha_o_solicitud(self, consultorio_id: int, usuario_id: int,
            nombre: str, apellido: str, telefono: str, email: str, dni: str,
            obra_social: str | None, ahora: datetime) -> None:
        pid = await self.sesion.scalar(insert(PacienteModel).values(
            consultorio_id=consultorio_id, usuario_id=usuario_id, nombre=nombre,
            apellido=apellido, telefono=telefono, email=email, dni=dni,
            obra_social=obra_social, activo=True, creado_en=ahora, actualizado_en=ahora
        ).on_conflict_do_nothing(index_elements=['consultorio_id','dni']).returning(PacienteModel.id))
        if pid is None:
            self.sesion.add(SolicitudVinculacionModel(consultorio_id=consultorio_id,
                usuario_id=usuario_id, dni_declarado=dni, estado='pendiente', creada_en=ahora))

    async def programar_token(self, usuario: UsuarioModel, tipo: str, token_hash: str,
            expira_en: datetime, cuerpo: str, ahora: datetime) -> int:
        self.sesion.add(TokenUsuarioModel(consultorio_id=usuario.consultorio_id,
            usuario_id=usuario.id, tipo=tipo, token_hash=token_hash,
            expira_en=expira_en, creado_en=ahora))
        mail = NotificacionModel(consultorio_id=usuario.consultorio_id,
            usuario_id=usuario.id, tipo='verificacion_email' if tipo == 'verificar_email' else 'recuperacion_password',
            canal='email', estado='programada', destinatario=usuario.email,
            programada_para=ahora, mensaje=cuerpo, intentos=0)
        self.sesion.add(mail)
        await self.sesion.flush()
        return mail.id

    async def token_y_usuario_bloqueados(self, token_hash: str):
        token = await self.sesion.scalar(select(TokenUsuarioModel).where(TokenUsuarioModel.token_hash == token_hash))
        if token is None:
            return None, None
        # All account operations acquire user before token, avoiding opposite
        # lock order with an email change invalidating previous token rows.
        user = await self.sesion.scalar(select(UsuarioModel).where(
            UsuarioModel.id == token.usuario_id,
            UsuarioModel.consultorio_id == token.consultorio_id,
            UsuarioModel.activo.is_(True)).with_for_update())
        token = await self.sesion.scalar(select(TokenUsuarioModel).where(
            TokenUsuarioModel.id == token.id,
            TokenUsuarioModel.consultorio_id == token.consultorio_id,
        ).execution_options(populate_existing=True).with_for_update())
        return token, user

    async def usuario_por_correo(self, consultorio_id: int, correo: str):
        return await self.sesion.scalar(select(UsuarioModel).where(
            UsuarioModel.consultorio_id == consultorio_id,
            UsuarioModel.email == correo.strip().lower(),
            UsuarioModel.activo.is_(True)).execution_options(populate_existing=True).with_for_update())

    async def revocar_sesiones(self, consultorio_id: int, usuario_id: int, ahora: datetime) -> None:
        await self.sesion.execute(update(RefreshTokenModel).where(
            RefreshTokenModel.consultorio_id == consultorio_id,
            RefreshTokenModel.usuario_id == usuario_id,
            RefreshTokenModel.revocado_en.is_(None)).values(revocado_en=ahora))

    async def usuario_por_id(self, consultorio_id: int, usuario_id: int):
        return await self.sesion.scalar(select(UsuarioModel).where(
            UsuarioModel.consultorio_id == consultorio_id, UsuarioModel.id == usuario_id,
            UsuarioModel.activo.is_(True)).execution_options(populate_existing=True).with_for_update())

    async def ficha_de_usuario(self, consultorio_id: int, usuario_id: int):
        return await self.sesion.scalar(select(PacienteModel).where(
            PacienteModel.consultorio_id == consultorio_id,
            PacienteModel.usuario_id == usuario_id).with_for_update())

    async def invalidar_enlaces_correo(self, consultorio_id: int, usuario_id: int, ahora: datetime) -> None:
        await self.sesion.execute(update(TokenUsuarioModel).where(
            TokenUsuarioModel.consultorio_id == consultorio_id,
            TokenUsuarioModel.usuario_id == usuario_id,
            TokenUsuarioModel.tipo.in_(('verificar_email', 'recuperar_password')),
            TokenUsuarioModel.usado_en.is_(None)).values(usado_en=ahora))
