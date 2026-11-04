from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.agenda_turnos import ConsultaAgenda, HechoOperativo, TurnoOperativo
from app.application.use_cases.consultar_turnos import ConsultarTurnos
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/api/v1", tags=["Agenda de turnos"], responses={
    401: {"description": "No autenticado"},
    403: {"description": "Acción o agenda no permitida"},
    404: {"description": "Recurso inexistente o fuera del alcance autorizado"},
})
PersonalAgenda = Annotated[Principal, Depends(requiere_rol(
    RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PROFESIONAL,
))]


def get_consulta(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                 settings: Annotated[Settings, Depends(get_settings)]) -> ConsultarTurnos:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return ConsultarTurnos(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj)


Consulta = Annotated[ConsultarTurnos, Depends(get_consulta)]


@router.get("/turnos", response_model=list[TurnoOperativo])
async def listar_turnos(principal: PersonalAgenda, consulta: Consulta):
    return await consulta.listar(principal)


@router.get("/turnos/{turno_id}", response_model=TurnoOperativo)
async def detalle_turno(turno_id: int, principal: PersonalAgenda, consulta: Consulta):
    return await consulta.detalle(principal, turno_id)


@router.get("/turnos/{turno_id}/historial", response_model=list[HechoOperativo])
async def historial_turno(turno_id: int, principal: PersonalAgenda, consulta: Consulta):
    return await consulta.historial(principal, turno_id)


@router.get("/agenda", response_model=list[TurnoOperativo])
async def agenda_profesional(parametros: Annotated[ConsultaAgenda, Query()],
                             principal: PersonalAgenda, consulta: Consulta):
    return await consulta.agenda(principal, parametros.profesional_id, parametros.fecha)


@router.get("/pacientes/{paciente_id}/turnos", response_model=list[TurnoOperativo])
async def turnos_de_paciente(paciente_id: int, principal: PersonalAgenda, consulta: Consulta):
    return await consulta.de_paciente(principal, paciente_id)
