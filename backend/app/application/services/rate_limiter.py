from datetime import timedelta
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ports.reloj import Reloj
from app.domain.services.auth_crypto import (
    calcular_identificador_hash,
    calcular_origen_hash,
    resolver_ip_origen,
)
from app.infrastructure.db.models import IntentoIngresoModel


class LoginRateLimiter:
    """Gestor de tasa de intentos de ingreso, bloqueos por par y origen y purga (RN-09, DD-21, DD-25)."""

    def __init__(
        self,
        sesion: AsyncSession,
        reloj: Reloj,
        origin_hash_secret: str,
        login_max_attempts: int = 5,
        login_lockout_minutes: int = 15,
        login_max_attempts_per_origin: int = 20,
        trusted_proxy_hops: int = 0,
    ) -> None:
        self.sesion = sesion
        self.reloj = reloj
        self.origin_hash_secret = origin_hash_secret
        self.login_max_attempts = login_max_attempts
        self.login_lockout_minutes = login_lockout_minutes
        self.login_max_attempts_per_origin = login_max_attempts_per_origin
        self.trusted_proxy_hops = trusted_proxy_hops

    async def registrar_intento_y_verificar_bloqueo(
        self,
        consultorio_id: int,
        identificador: str,
        client_host: str | None,
        x_forwarded_for: str | None,
    ) -> tuple[bool, str, str | None]:
        """Inserta previamente el intento en una transacción atómica, purga y verifica si está bloqueado."""
        ip = resolver_ip_origen(client_host, x_forwarded_for, self.trusted_proxy_hops)
        identificador_hash = calcular_identificador_hash(identificador, self.origin_hash_secret)
        origen_hash = calcular_origen_hash(ip, self.origin_hash_secret)

        ahora = self.reloj.ahora()

        # 1. Inserción previa obligatoria (RN-09)
        intento = IntentoIngresoModel(
            consultorio_id=consultorio_id,
            identificador_hash=identificador_hash,
            origen_hash=origen_hash,
            creado_en=ahora,
        )
        self.sesion.add(intento)

        # 2. Purga oportunista al escribir de intentos con más de 24 horas
        limite_purga = ahora - timedelta(hours=24)
        await self.sesion.execute(
            delete(IntentoIngresoModel).where(IntentoIngresoModel.creado_en < limite_purga)
        )

        # Confirmación atómica antes de evaluar el conteo de la ventana
        await self.sesion.commit()

        # 3. Conteo en la ventana configurada
        limite_ventana = ahora - timedelta(minutes=self.login_lockout_minutes)

        # Conteo para el par (identificador, origen) con semántica segura de nulidad
        filtro_origen = (
            IntentoIngresoModel.origen_hash == origen_hash
            if origen_hash is not None
            else IntentoIngresoModel.origen_hash.is_(None)
        )
        query_par = select(func.count(IntentoIngresoModel.id)).where(
            IntentoIngresoModel.consultorio_id == consultorio_id,
            IntentoIngresoModel.identificador_hash == identificador_hash,
            filtro_origen,
            IntentoIngresoModel.creado_en >= limite_ventana,
        )
        conteo_par = (await self.sesion.scalar(query_par)) or 0
        if conteo_par > self.login_max_attempts:
            return (True, identificador_hash, origen_hash)

        # Conteo por origen (únicamente cuando el origen está determinado)
        if origen_hash is not None:
            query_origen = select(func.count(IntentoIngresoModel.id)).where(
                IntentoIngresoModel.consultorio_id == consultorio_id,
                IntentoIngresoModel.origen_hash == origen_hash,
                IntentoIngresoModel.creado_en >= limite_ventana,
            )
            conteo_origen = (await self.sesion.scalar(query_origen)) or 0
            if conteo_origen > self.login_max_attempts_per_origin:
                return (True, identificador_hash, origen_hash)

        return (False, identificador_hash, origen_hash)

    async def limpiar_intentos_exitosos(
        self,
        consultorio_id: int,
        identificador_hash: str,
        origen_hash: str | None,
        *, confirmar: bool = True,
    ) -> None:
        """Limpia el par; login confirma junto a la emisión para conservar su lock."""
        filtro_origen = (
            IntentoIngresoModel.origen_hash == origen_hash
            if origen_hash is not None
            else IntentoIngresoModel.origen_hash.is_(None)
        )
        stmt = delete(IntentoIngresoModel).where(
            IntentoIngresoModel.consultorio_id == consultorio_id,
            IntentoIngresoModel.identificador_hash == identificador_hash,
            filtro_origen,
        )
        await self.sesion.execute(stmt)
        if confirmar:
            await self.sesion.commit()
