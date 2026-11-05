"""Enlace bearer sin sesión: su único permiso es confirmar el turno asociado."""
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_reloj, get_settings
from app.api.v1.schemas.confirmacion_turno import ConfirmacionTurnoRespuesta
from app.api.v1.schemas.cuenta import TokenRequest
from app.application.use_cases.confirmar_por_enlace import ConfirmarTurnoPorEnlace
from app.core.config import Settings
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones

router = APIRouter(prefix="/api/v1/turnos", tags=["Confirmación de turnos"])


def get_confirmacion(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                     settings: Annotated[Settings, Depends(get_settings)]) -> ConfirmarTurnoPorEnlace:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return ConfirmarTurnoPorEnlace(request.app.state.session_factory, reloj)


@router.post("/confirmar-por-enlace", response_model=ConfirmacionTurnoRespuesta,
    summary="Confirmar únicamente el turno y ciclo asociados al enlace",
    description="Sin sesión. El consultorio se obtiene del token; no admite consultorio_id. El token no autoriza cancelar ni reprogramar.",
    responses={400: {"description": "Enlace inválido, usado o vencido"},
               409: {"description": "El estado del turno ya no permite confirmar"},
               422: {"description": "Cuerpo inválido o campos no declarados"}})
async def confirmar_por_enlace(payload: TokenRequest,
    caso: Annotated[ConfirmarTurnoPorEnlace, Depends(get_confirmacion)]):
    return await caso.ejecutar(payload.token.get_secret_value())
