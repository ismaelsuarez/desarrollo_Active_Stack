"""Contratos HTTP de cuenta de paciente y aviso público."""

from typing import Annotated
from json import JSONDecodeError

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import consultorio_sin_token, get_reloj, get_sesion, get_settings, requiere_rol, usuario_actual
from app.api.v1.schemas.auth import MensajeResponse
from app.api.v1.schemas.cuenta import (
    ActualizarCuentaRequest, CambiarPasswordRequest, CorreoRequest,
    RegistroRequest, RestablecerPasswordRequest, TokenRequest,
)
from app.application.services.cuentas import ErrorCuenta, ServicioCuentas
from app.application.services.notificaciones import DespacharNotificacion
from app.application.privacidad import aviso_completo, renderizar_aviso
from app.core.config import Settings
from app.domain.ports.correo import EnviadorCorreo
from app.domain.ports.reloj import Reloj
from app.domain.entities.auth import Principal, RolUsuario
from app.infrastructure.correo.smtp import EnviadorSMTP
from app.infrastructure.db.limites_cuenta import LimiteSolicitudes, LimitesCuentaPostgres
from app.infrastructure.db.models import ConsultorioModel

router = APIRouter(prefix='/api/v1', tags=['Cuenta del paciente'])
ConsultorioPublico = Annotated[ConsultorioModel, Depends(consultorio_sin_token)]
Configuracion = Annotated[Settings, Depends(get_settings)]
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
RelojActual = Annotated[Reloj, Depends(get_reloj)]


def get_servicio_cuentas(sesion: Sesion, reloj: RelojActual, settings: Configuracion) -> ServicioCuentas:
    return ServicioCuentas(sesion, reloj, settings)


def get_enviador_correo(settings: Configuracion) -> EnviadorCorreo:
    return EnviadorSMTP(settings)


Servicio = Annotated[ServicioCuentas, Depends(get_servicio_cuentas)]
CorreoSalida = Annotated[EnviadorCorreo, Depends(get_enviador_correo)]
CuentaActual = Annotated[Principal, Depends(usuario_actual)]
PacienteActual = Annotated[Principal, Depends(requiere_rol(RolUsuario.PACIENTE))]


async def admitir_registro(request: Request, consultorio: ConsultorioPublico,
                          sesion: Sesion, reloj: RelojActual, settings: Configuracion) -> None:
    try:
        await LimitesCuentaPostgres(sesion, reloj, settings).admitir_registro(
            consultorio.id, request.client.host if request.client else None,
            request.headers.get('x-forwarded-for'),
        )
    except LimiteSolicitudes as exc:
        raise HTTPException(429, str(exc)) from None


async def validar_payload_registro(
        request: Request, admitido: Annotated[None, Depends(admitir_registro)]) -> RegistroRequest:
    # FastAPI parses automatic Body parameters before solving dependencies.
    # Registration must record an admitted attempt even for malformed JSON.
    try:
        datos = await request.json()
    except (JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(422, detail=[{
            'loc': ['body'], 'msg': 'El cuerpo debe ser JSON válido', 'type': 'json_invalid',
        }]) from None
    try:
        return RegistroRequest.model_validate(datos)
    except ValidationError as exc:
        detalles = [{'loc': ['body', *error['loc']], 'msg': error['msg'], 'type': error['type']}
                    for error in exc.errors(include_input=False, include_context=False)]
        raise HTTPException(422, detail=detalles) from None


def programar_despacho(tareas: BackgroundTasks, request: Request, consultorio_id: int,
                      notificacion_id: int | None, reloj: Reloj, enviador: EnviadorCorreo,
                      settings: Settings) -> None:
    if notificacion_id is not None:
        despacho = DespacharNotificacion(request.app.state.session_factory, reloj, enviador, settings)
        tareas.add_task(despacho.ejecutar, consultorio_id, notificacion_id)


@router.get('/publico/aviso-privacidad')
async def aviso_privacidad(consultorio: ConsultorioPublico, settings: Configuracion) -> dict[str, str]:
    aviso = renderizar_aviso(consultorio.nombre, consultorio.direccion, consultorio.telefono)
    if settings.app_env == 'production' and not aviso_completo(aviso['texto']):
        raise HTTPException(503, 'El aviso de privacidad todavía no está disponible')
    return aviso


@router.post('/auth/registro', status_code=201, openapi_extra={
    'requestBody': {'required': True, 'content': {
        'application/json': {'schema': RegistroRequest.model_json_schema()},
    }},
})
async def registrar(payload: Annotated[RegistroRequest, Depends(validar_payload_registro)],
                    request: Request, tareas: BackgroundTasks,
                    consultorio: ConsultorioPublico, servicio: Servicio, reloj: RelojActual,
                    enviador: CorreoSalida, settings: Configuracion) -> MensajeResponse:
    consultorio_id = consultorio.id
    datos = payload.model_dump(exclude={'password'})
    try:
        notificacion_id = await servicio.registrar(
            consultorio_id, **datos, password=payload.password.get_secret_value())
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    programar_despacho(tareas, request, consultorio_id, notificacion_id, reloj, enviador, settings)
    return MensajeResponse(mensaje='Revisá tu correo para verificar la cuenta')


@router.post('/auth/verificar-email')
async def verificar_email(payload: TokenRequest, servicio: Servicio) -> MensajeResponse:
    try:
        await servicio.verificar_email(payload.token.get_secret_value())
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    return MensajeResponse(mensaje='Correo verificado')


@router.post('/auth/reenviar-verificacion')
async def reenviar_verificacion(payload: CorreoRequest, request: Request, tareas: BackgroundTasks,
                               consultorio: ConsultorioPublico, servicio: Servicio,
                               reloj: RelojActual, enviador: CorreoSalida,
                               settings: Configuracion) -> MensajeResponse:
    # A generic no-op can roll back the session and expire ORM objects.
    consultorio_id = consultorio.id
    try:
        notificacion_id = await servicio.reenviar_verificacion(consultorio_id, payload.email)
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    programar_despacho(tareas, request, consultorio_id, notificacion_id, reloj, enviador, settings)
    return MensajeResponse(mensaje='Si corresponde, recibirás un correo')


@router.post('/auth/recuperar-password')
async def recuperar_password(payload: CorreoRequest, request: Request, tareas: BackgroundTasks,
                             consultorio: ConsultorioPublico, servicio: Servicio,
                             reloj: RelojActual, enviador: CorreoSalida,
                             settings: Configuracion) -> MensajeResponse:
    consultorio_id = consultorio.id
    try:
        notificacion_id = await servicio.recuperar_password(consultorio_id, payload.email)
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    programar_despacho(tareas, request, consultorio_id, notificacion_id, reloj, enviador, settings)
    return MensajeResponse(mensaje='Si corresponde, recibirás un correo')


@router.post('/auth/restablecer-password')
async def restablecer_password(payload: RestablecerPasswordRequest, servicio: Servicio) -> MensajeResponse:
    try:
        await servicio.restablecer_password(payload.token.get_secret_value(), payload.password.get_secret_value())
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    return MensajeResponse(mensaje='Contraseña restablecida')


@router.patch('/auth/cambiar-password')
async def cambiar_password(payload: CambiarPasswordRequest, principal: CuentaActual,
                           servicio: Servicio) -> MensajeResponse:
    try:
        await servicio.cambiar_password(principal, payload.password_actual.get_secret_value(),
                                       payload.password_nueva.get_secret_value())
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    return MensajeResponse(mensaje='Contraseña actualizada')


@router.patch('/auth/actualizar-cuenta')
async def actualizar_cuenta(payload: ActualizarCuentaRequest, request: Request, tareas: BackgroundTasks,
                            principal: PacienteActual, servicio: Servicio, reloj: RelojActual,
                            enviador: CorreoSalida, settings: Configuracion) -> MensajeResponse:
    try:
        notificacion_id = await servicio.actualizar_cuenta(principal, telefono=payload.telefono, email=payload.email)
    except ErrorCuenta as exc:
        raise HTTPException(exc.status_code, str(exc)) from None
    programar_despacho(tareas, request, principal.consultorio_id, notificacion_id, reloj, enviador, settings)
    return MensajeResponse(mensaje='Cuenta actualizada')
