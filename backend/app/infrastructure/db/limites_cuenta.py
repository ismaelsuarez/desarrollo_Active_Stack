"""Límites durables de cuenta sin almacenar direcciones de origen."""
from datetime import timedelta
import ipaddress

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.domain.ports.reloj import Reloj
from app.domain.services.auth_crypto import calcular_origen_hash, resolver_ip_origen
from app.infrastructure.db.account_models import IntentoRegistroModel
from app.infrastructure.db.models import TokenUsuarioModel


class LimiteSolicitudes(Exception):
    pass


class PurgarIntentosRegistro:
    def __init__(self, sesion: AsyncSession, reloj: Reloj):
        self.sesion = sesion
        self.reloj = reloj

    async def ejecutar(self) -> None:
        await self.sesion.execute(delete(IntentoRegistroModel).where(
            IntentoRegistroModel.creado_en < self.reloj.ahora() - timedelta(hours=24)))


class LimitesCuentaPostgres:
    def __init__(self, sesion: AsyncSession, reloj: Reloj, settings: Settings):
        self.sesion = sesion
        self.reloj = reloj
        self.settings = settings

    async def admitir_registro(self, consultorio_id: int, host: str | None,
                               forwarded: str | None) -> None:
        origin = resolver_ip_origen(host, forwarded, self.settings.trusted_proxy_hops)
        try:
            if origin is not None:
                origin = str(ipaddress.ip_address(origin))
        except ValueError:
            origin = None
        digest = calcular_origen_hash(origin, self.settings.origin_hash_secret.get_secret_value())
        now = self.reloj.ahora()
        conditions = [IntentoRegistroModel.consultorio_id == consultorio_id,
                      IntentoRegistroModel.creado_en >= now - timedelta(minutes=self.settings.registration_limit_window_minutes)]
        maximum = self.settings.registration_limit_global
        if digest is not None:
            conditions.append(IntentoRegistroModel.origen_hash == digest)
            maximum = self.settings.registration_limit_per_origin
        count = await self.sesion.scalar(select(func.count()).select_from(IntentoRegistroModel).where(*conditions))
        if count >= maximum:
            raise LimiteSolicitudes('Demasiadas solicitudes; intentá nuevamente más tarde')
        await PurgarIntentosRegistro(self.sesion, self.reloj).ejecutar()
        self.sesion.add(IntentoRegistroModel(consultorio_id=consultorio_id,
                                           origen_hash=digest, creado_en=now))
        await self.sesion.commit()

    async def correo_permitido(self, consultorio_id: int, usuario_id: int, tipo: str) -> bool:
        count = await self.sesion.scalar(select(func.count()).select_from(TokenUsuarioModel).where(
            TokenUsuarioModel.consultorio_id == consultorio_id,
            TokenUsuarioModel.usuario_id == usuario_id,
            TokenUsuarioModel.tipo == tipo,
            TokenUsuarioModel.creado_en >= self.reloj.ahora() - timedelta(minutes=self.settings.account_email_window_minutes)))
        return count < self.settings.account_email_limit
