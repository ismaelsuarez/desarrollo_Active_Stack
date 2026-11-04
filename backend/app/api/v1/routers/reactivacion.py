from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.reactivacion import ReactivarRequest
from app.application.use_cases.reactivar_paciente import ReactivarPaciente
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/api/v1/pacientes", tags=["Pacientes"], responses={
    401: {"description": "No autenticado"},
    403: {"description": "Acción no permitida para el rol"},
    404: {"description": "Ficha inexistente o ajena"},
    409: {"description": "Ficha ya activa o cambio concurrente"},
    422: {"description": "La reactivación no acepta campos de negocio"},
})
Personal = Annotated[Principal, Depends(requiere_rol(RolUsuario.RECEPCION, RolUsuario.ADMINISTRADOR))]


def get_reactivacion(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                     settings: Annotated[Settings, Depends(get_settings)]):
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return ReactivarPaciente(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj)


@router.post("/{paciente_id}/reactivar", summary="Reactivar ficha inactiva",
             description="Sólo Recepción y Administrador. Sin motivo ni correo. No modifica datos ni turnos y no permite desactivar fichas.")
async def reactivar(paciente_id: int, principal: Personal,
                    servicio: Annotated[ReactivarPaciente, Depends(get_reactivacion)],
                    payload: ReactivarRequest | None = None):
    await servicio.ejecutar(principal, paciente_id)
    return {"mensaje": "Ficha reactivada"}
