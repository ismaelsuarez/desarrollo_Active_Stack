from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.turno import ReprogramacionEntrada, ReprogramacionOnlineEntrada, TurnoEntrada, TurnoOnlineEntrada, TurnoRespuesta
from app.api.v1.routers.acciones_turnos import router as acciones_router
from app.application.use_cases.gestionar_turnos import GestionTurnos
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.core.config import Settings
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from app.domain.errors import HorarioOcupado
from app.domain.errors_turnos import ConflictoDeTurno

router = APIRouter(prefix="/api/v1", tags=["Turnos"])
Personal = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION))]
Reservante = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PACIENTE))]


def get_gestion(request: Request, reloj: Reloj = Depends(get_reloj),
                settings: Settings = Depends(get_settings)) -> GestionTurnos:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return GestionTurnos(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj)


Gestion = Annotated[GestionTurnos, Depends(get_gestion)]


async def ejecutar_reserva(operacion, principal, gestion, **alternativas):
    try:
        return await operacion
    except HorarioOcupado:
        if principal.rol != RolUsuario.PACIENTE:
            raise HTTPException(409, "horario ocupado") from None
        intervalos = await gestion.alternativas(principal, **alternativas)
        raise HTTPException(409, {"motivo": "horario ocupado", "alternativas": [
            {"inicio": i.inicio.isoformat(), "fin": i.fin.isoformat()} for i in intervalos
        ]}) from None
    except ConflictoDeTurno:
        raise HTTPException(409, "El turno cambió durante la operación") from None


@router.post("/turnos", response_model=TurnoRespuesta, status_code=201,
             summary="Reservar un turno regular por personal o paciente verificado",
             description="Recepción/Administrador conservan sus campos. Paciente sólo profesional_id, prestacion_id e inicio: el servidor deriva ficha vigente y origen online. Exige correo actual verificado y respeta horizonte y máximo futuro atómico. Turno e historial se confirman juntos. Ocupación online devuelve hasta tres alternativas; el 409 de máximo indica el límite.",
             responses={401: {"description": "No autenticado"},
                        403: {"description": "Rol no autorizado"},
                        404: {"description": "Referencia inexistente o ajena"},
                        409: {"description": "Horario ocupado con alternativas online o máximo futuro alcanzado"},
                        422: {"description": "Entrada, duración, grilla o agenda inválidas"}})
async def crear_turno(payload: TurnoEntrada | TurnoOnlineEntrada, principal: Reservante, gestion: Gestion):
    modelo = TurnoOnlineEntrada if principal.rol == RolUsuario.PACIENTE else TurnoEntrada
    try:
        entrada = modelo.model_validate(payload.model_dump())
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from None
    datos = entrada.model_dump()
    if principal.rol == RolUsuario.PACIENTE:
        datos["paciente_id"] = None
    return await ejecutar_reserva(gestion.crear(principal, **datos), principal, gestion,
        inicio=entrada.inicio, profesional_id=entrada.profesional_id, prestacion_id=entrada.prestacion_id)


router.include_router(acciones_router)


@router.patch("/turnos/{turno_id}", response_model=TurnoRespuesta,
              summary="Reprogramar el mismo turno de forma atómica",
              description="Paciente titular sólo inicio: ventana de horas_limite_paciente, horizonte y grilla, conserva duración actual incluso ajustada por personal y no consume cupo nuevo. Personal conserva ajuste de duración. Reinicia ciclo y limpia marca. Fuera de plazo403 con teléfono; ajenos404; ocupación409 con alternativas online después del rollback. Fallos conservan turno e historial.",
              responses={401: {"description": "No autenticado"},
                         403: {"description": "Rol o estado no permitido"},
                         404: {"description": "Turno inexistente o ajeno"},
                         409: {"description": "Horario ocupado o lectura obsoleta"},
                         422: {"description": "Entrada, duración, grilla o agenda inválidas"}})
async def reprogramar_turno(turno_id: int, payload: ReprogramacionEntrada | ReprogramacionOnlineEntrada, principal: Reservante, gestion: Gestion):
    modelo = ReprogramacionOnlineEntrada if principal.rol == RolUsuario.PACIENTE else ReprogramacionEntrada
    try:
        entrada = modelo.model_validate(payload.model_dump(exclude_unset=True))
    except ValidationError as error:
        raise RequestValidationError(error.errors()) from None
    return await ejecutar_reserva(gestion.reprogramar(principal, turno_id, **entrada.model_dump()),
        principal, gestion, inicio=entrada.inicio, turno_id=turno_id)
