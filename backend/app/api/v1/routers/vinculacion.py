from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.vinculacion import ConsultaSolicitudes, DesvincularRequest, RechazarRequest, VincularRequest
from app.api.v1.routers.cuentas import CorreoSalida, Configuracion, RelojActual, programar_despacho
from app.application.use_cases.vinculos_pacientes import VinculosPacientes
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/api/v1", tags=["Vínculos de pacientes"], responses={
    401: {"description": "No autenticado"},
    403: {"description": "Acción no permitida"},
    404: {"description": "Recurso inexistente o ajeno"},
    409: {"description": "Conflicto de estado o resolución concurrente"},
    422: {"description": "Entrada inválida"},
})
Personal = Annotated[Principal, Depends(requiere_rol(
    RolUsuario.RECEPCION, RolUsuario.ADMINISTRADOR,
))]


def get_vinculos(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                 settings: Annotated[Settings, Depends(get_settings)]) -> VinculosPacientes:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return VinculosPacientes(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj)


Vinculos = Annotated[VinculosPacientes, Depends(get_vinculos)]


@router.post("/pacientes/{paciente_id}/desvincular", summary="Desvincular cuenta conservando ficha y turnos",
             description="Personal habilitado, motivo obligatorio. Rechaza o crea la solicitud con origen y última resolución; revoca refresh tokens, incluidos reemplazos en vuelo, en la misma transacción. No cambia contraseña ni envía correo. El JWT de acceso anterior no permite leer la antigua ficha.")
async def desvincular(paciente_id: int, payload: DesvincularRequest,
                     principal: Personal, servicio: Vinculos) -> dict[str, str]:
    await servicio.desvincular(principal, paciente_id, payload.motivo)
    return {"mensaje": "Cuenta desvinculada"}


@router.get("/solicitudes-vinculacion")
async def listar_solicitudes(parametros: Annotated[ConsultaSolicitudes, Query()],
                            principal: Personal, servicio: Vinculos) -> dict:
    return await servicio.listar(principal, **parametros.model_dump())


@router.post("/solicitudes-vinculacion/{solicitud_id}/vincular")
async def vincular(solicitud_id: int, payload: VincularRequest,
                   principal: Personal, servicio: Vinculos) -> dict[str, str]:
    await servicio.vincular(principal, solicitud_id, payload.paciente_id)
    return {"mensaje": "Cuenta vinculada"}


@router.post("/solicitudes-vinculacion/{solicitud_id}/rechazar")
async def rechazar(solicitud_id: int, request: Request,
                   tareas: BackgroundTasks, principal: Personal, servicio: Vinculos,
                   reloj: RelojActual, enviador: CorreoSalida,
                   settings: Configuracion,
                   payload: RechazarRequest = RechazarRequest()) -> dict[str, str]:
    notificacion_id = await servicio.rechazar(principal, solicitud_id, payload.motivo)
    programar_despacho(tareas, request, principal.consultorio_id, notificacion_id,
                      reloj, enviador, settings)
    return {"mensaje": "Solicitud rechazada"}
