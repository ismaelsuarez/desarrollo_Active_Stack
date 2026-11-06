from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.notificaciones import ConsultaNotificaciones, EnlaceWhatsApp, EnvioManual, IndicadoresNotificaciones, NotificacionOperativa
from app.application.use_cases.consultar_notificaciones import ConsultarNotificaciones
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones

router = APIRouter(prefix="/api/v1/notificaciones", tags=["Operación de notificaciones"])
Operador = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION))]


def get_consulta(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                 settings: Annotated[Settings, Depends(get_settings)]) -> ConsultarNotificaciones:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return ConsultarNotificaciones(request.app.state.session_factory, reloj, settings)


Consulta = Annotated[ConsultarNotificaciones, Depends(get_consulta)]


@router.get("", response_model=list[NotificacionOperativa])
async def listar(principal: Operador, consulta: Consulta,
                 filtros: Annotated[ConsultaNotificaciones, Query()]):
    return await consulta.listar(principal, **filtros.model_dump())


@router.get("/indicadores", response_model=IndicadoresNotificaciones)
async def indicadores(principal: Operador, consulta: Consulta):
    return await consulta.indicadores(principal)


@router.get('/{notificacion_id}/whatsapp', response_model=EnlaceWhatsApp)
async def enlace_whatsapp(notificacion_id: int, principal: Operador, consulta: Consulta):
    return await consulta.enlace_whatsapp(principal, notificacion_id)


@router.post('/{notificacion_id}/marcar-enviada', response_model=EnvioManual)
async def marcar_enviada(notificacion_id: int, principal: Operador, consulta: Consulta):
    return await consulta.marcar_enviada(principal, notificacion_id)
