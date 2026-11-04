from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.turno import ReprogramacionEntrada, TurnoEntrada, TurnoRespuesta
from app.api.v1.turno_errors import ejecutar_operacion
from app.api.v1.routers.acciones_turnos import router as acciones_router
from app.application.use_cases.gestionar_turnos import GestionTurnos
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.core.config import Settings
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/api/v1", tags=["Turnos"])
Personal = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION))]


def get_gestion(request: Request, reloj: Reloj = Depends(get_reloj),
                settings: Settings = Depends(get_settings)) -> GestionTurnos:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return GestionTurnos(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj)


Gestion = Annotated[GestionTurnos, Depends(get_gestion)]


@router.post("/turnos", response_model=TurnoRespuesta, status_code=201,
             summary="Reservar un turno regular por personal",
             description="Recepción o Administrador. El consultorio proviene de la identidad autenticada; el servidor calcula el fin. La reserva y su historial se confirman juntos antes de responder.",
             responses={401: {"description": "No autenticado"},
                        403: {"description": "Rol no autorizado"},
                        404: {"description": "Referencia inexistente o ajena"},
                        409: {"description": "Horario ocupado"},
                        422: {"description": "Entrada, duración, grilla o agenda inválidas"}})
async def crear_turno(payload: TurnoEntrada, principal: Personal, gestion: Gestion):
    return await ejecutar_operacion(gestion.crear(principal, **payload.model_dump()))


router.include_router(acciones_router)


@router.patch("/turnos/{turno_id}", response_model=TurnoRespuesta,
              summary="Reprogramar el mismo turno de forma atómica",
              description="Recepción o Administrador. Conserva la duración salvo ajuste, reinicia el ciclo y limpia la marca sin confirmar. Si falla el turno y su historial permanecen intactos.",
              responses={401: {"description": "No autenticado"},
                         403: {"description": "Rol o estado no permitido"},
                         404: {"description": "Turno inexistente o ajeno"},
                         409: {"description": "Horario ocupado o lectura obsoleta"},
                         422: {"description": "Entrada, duración, grilla o agenda inválidas"}})
async def reprogramar_turno(turno_id: int, payload: ReprogramacionEntrada, principal: Personal, gestion: Gestion):
    return await ejecutar_operacion(gestion.reprogramar(principal, turno_id, **payload.model_dump()))
