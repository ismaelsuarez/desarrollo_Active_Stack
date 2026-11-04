"""Casos de uso de cuenta; datos obtenidos exclusivamente por repositorio."""
from datetime import timedelta
from functools import wraps
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.domain.ports.reloj import Reloj
from app.domain.services.auth_crypto import calcular_token_hash, generar_token_opaco, hashear_password, verificar_password
from app.infrastructure.correo.plantillas import correo_cuenta
from app.infrastructure.db.cuentas import RepositorioCuentas
from app.application.privacidad import VERSION_AVISO
from app.domain.ports.limites_cuenta import LimitesCorreoCuenta
from app.infrastructure.db.limites_cuenta import LimitesCuentaPostgres


class ErrorCuenta(Exception):
    def __init__(self, status_code: int, mensaje: str):
        super().__init__(mensaje)
        self.status_code = status_code


def revertir_conflicto(funcion):
    @wraps(funcion)
    async def ejecutar(self, *args, **kwargs):
        try:
            return await funcion(self, *args, **kwargs)
        except IntegrityError:
            await self.sesion.rollback()
            raise ErrorCuenta(409, 'Los datos de la cuenta no están disponibles') from None
    return ejecutar


class ServicioCuentas:
    def __init__(self, sesion, reloj: Reloj, settings: Settings, limites: LimitesCorreoCuenta | None = None):
        self.repo = RepositorioCuentas(sesion)
        self.sesion = sesion
        self.reloj = reloj
        self.settings = settings
        self.limites = limites or LimitesCuentaPostgres(sesion, reloj, settings)

    @revertir_conflicto
    async def registrar(self, consultorio_id: int, *, nombre: str, apellido: str,
            telefono: str, email: str, dni: str, nombre_usuario: str, password: str,
            obra_social: str | None, acepta_aviso_privacidad: bool,
            aviso_privacidad_version: str) -> int:
        if acepta_aviso_privacidad is not True or aviso_privacidad_version != VERSION_AVISO:
            raise ErrorCuenta(422, 'Aceptá la versión vigente del aviso de privacidad')
        ahora = self.reloj.ahora()
        user = await self.repo.crear_usuario(consultorio_id, nombre_usuario,
            email, hashear_password(password), aviso_privacidad_version, ahora)
        await self.repo.crear_ficha_o_solicitud(consultorio_id, user.id, nombre,
            apellido, telefono, user.email, dni, obra_social, ahora)
        raw = generar_token_opaco()
        _, cuerpo = correo_cuenta('verificacion_email', raw, self.settings.frontend_base_url)
        nid = await self.repo.programar_token(user, 'verificar_email',
            calcular_token_hash(raw), ahora + timedelta(hours=self.settings.email_verification_ttl_hours), cuerpo, ahora)
        await self.sesion.commit()
        return nid
    async def _token_valido(self, raw: str, tipo: str):
        token, user = await self.repo.token_y_usuario_bloqueados(calcular_token_hash(raw))
        if token is None or user is None or token.tipo != tipo or token.usado_en is not None or token.expira_en <= self.reloj.ahora():
            await self.sesion.rollback()
            raise ErrorCuenta(400, 'El enlace no es válido o venció')
        return token, user

    async def verificar_email(self, raw: str) -> None:
        token, user = await self._token_valido(raw, 'verificar_email')
        token.usado_en = self.reloj.ahora()
        user.email_verificado = True
        user.email_verificado_en = self.reloj.ahora()
        user.actualizado_en = self.reloj.ahora()
        await self.sesion.commit()

    async def recuperar_password(self, consultorio_id: int, email: str) -> int | None:
        user = await self.repo.usuario_por_correo(consultorio_id, email)
        if user is None or not user.email_verificado:
            await self.sesion.rollback()
            return None
        if not await self.limites.correo_permitido(consultorio_id, user.id, 'recuperar_password'):
            await self.sesion.rollback()
            return None
        ahora = self.reloj.ahora()
        raw = generar_token_opaco()
        _, cuerpo = correo_cuenta('recuperacion_password', raw, self.settings.frontend_base_url)
        nid = await self.repo.programar_token(user, 'recuperar_password', calcular_token_hash(raw),
            ahora + timedelta(minutes=self.settings.password_reset_ttl_minutes), cuerpo, ahora)
        await self.sesion.commit()
        return nid

    async def reenviar_verificacion(self, consultorio_id: int, email: str) -> int | None:
        user = await self.repo.usuario_por_correo(consultorio_id, email)
        if user is None or user.email_verificado:
            await self.sesion.rollback()
            return None
        if not await self.limites.correo_permitido(consultorio_id, user.id, 'verificar_email'):
            await self.sesion.rollback()
            return None
        ahora = self.reloj.ahora()
        raw = generar_token_opaco()
        _, cuerpo = correo_cuenta('verificacion_email', raw, self.settings.frontend_base_url)
        nid = await self.repo.programar_token(user, 'verificar_email', calcular_token_hash(raw),
            ahora + timedelta(hours=self.settings.email_verification_ttl_hours), cuerpo, ahora)
        await self.sesion.commit()
        return nid

    async def restablecer_password(self, raw: str, password: str) -> None:
        token, user = await self._token_valido(raw, 'recuperar_password')
        user.password_hash = hashear_password(password)
        user.actualizado_en = self.reloj.ahora()
        token.usado_en = self.reloj.ahora()
        await self.repo.revocar_sesiones(user.consultorio_id, user.id, self.reloj.ahora())
        await self.sesion.commit()

    async def cambiar_password(self, principal, password_actual: str, password_nueva: str) -> None:
        user = await self.repo.usuario_por_id(principal.consultorio_id, principal.usuario_id)
        if user is None or not verificar_password(password_actual, user.password_hash):
            await self.sesion.rollback()
            raise ErrorCuenta(403, 'La contraseña actual no es correcta')
        user.password_hash = hashear_password(password_nueva)
        user.actualizado_en = self.reloj.ahora()
        await self.sesion.commit()

    @revertir_conflicto
    async def actualizar_cuenta(self, principal, telefono: str | None, email: str | None) -> int | None:
        try:
            nid = await actualizar_contacto_transaccional(
                self.repo, self.reloj, self.settings, principal, telefono, email,
            )
        except ErrorCuenta:
            await self.sesion.rollback()
            raise
        await self.sesion.commit()
        return nid


async def _actualizar_contacto_transaccional(repo: RepositorioCuentas, reloj: Reloj,
        settings: Settings, principal, telefono: str | None, email: str | None,
        paciente_id_esperado: int | None = None) -> int | None:
    """Actualiza contacto y programa verificación sin confirmar la transacción."""
    user = await repo.usuario_por_id(principal.consultorio_id, principal.usuario_id)
    if user is None:
        raise ErrorCuenta(401, 'Cuenta no disponible')
    patient = await repo.ficha_de_usuario(principal.consultorio_id, principal.usuario_id)
    if paciente_id_esperado is not None and (patient is None or patient.id != paciente_id_esperado):
        raise ErrorCuenta(404, 'Ficha no encontrada')
    ahora = reloj.ahora()
    if patient is not None and telefono is not None:
        patient.telefono = telefono
        patient.actualizado_en = ahora
    nid = None
    if email is not None and email.strip().lower() != user.email:
        user.email = email.strip().lower()
        user.email_verificado = False
        user.email_verificado_en = None
        user.actualizado_en = ahora
        if patient is not None:
            patient.email = user.email
            patient.actualizado_en = ahora
        await repo.invalidar_enlaces_correo(user.consultorio_id, user.id, ahora)
        raw = generar_token_opaco()
        _, cuerpo = correo_cuenta('verificacion_email', raw, settings.frontend_base_url)
        nid = await repo.programar_token(user, 'verificar_email', calcular_token_hash(raw),
            ahora + timedelta(hours=settings.email_verification_ttl_hours), cuerpo, ahora)
    return nid


async def actualizar_contacto_transaccional(repo: RepositorioCuentas, reloj: Reloj,
        settings: Settings, principal, telefono: str | None, email: str | None,
        paciente_id_esperado: int | None = None) -> int | None:
    try:
        return await _actualizar_contacto_transaccional(
            repo, reloj, settings, principal, telefono, email, paciente_id_esperado,
        )
    except IntegrityError as error:
        causa = error.orig
        while causa is not None:
            if (getattr(causa, 'sqlstate', None) == '23505'
                    and getattr(causa, 'constraint_name', None) == 'uq_usuario_consultorio_email'):
                raise ErrorCuenta(409, 'El correo de la cuenta no está disponible') from None
            causa = getattr(causa, '__cause__', None)
        raise
