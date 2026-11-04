from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.acciones_turnos import AccionTurnoEntrada, CancelarTurnoEntrada
from app.api.v1.schemas.turno import TurnoRespuesta
from app.api.v1.turno_errors import ejecutar_operacion
from app.application.use_cases.ciclo_turnos import CicloTurnos
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/turnos", tags=["Ciclo de turnos"], responses={
    401: {"description": "No autenticado"},
    403: {"description": "Acción no permitida para el rol, estado o instante"},
    404: {"description": "Turno no encontrado dentro del alcance autorizado"},
    409: {"description": "El turno cambió durante la operación"},
    422: {"description": "Entrada inválida o campos no declarados"},
})
Personal = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION))]
Atencion = Annotated[Principal, Depends(requiere_rol(
    RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PROFESIONAL,
))]


def get_ciclo(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
              settings: Annotated[Settings, Depends(get_settings)]) -> CicloTurnos:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return CicloTurnos(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory, reloj=reloj), reloj)


Ciclo = Annotated[CicloTurnos, Depends(get_ciclo)]


@router.post("/{turno_id}/confirmar", response_model=TurnoRespuesta)
async def confirmar(turno_id: int, principal: Personal, ciclo: Ciclo,
                    payload: AccionTurnoEntrada = AccionTurnoEntrada()):
    """Confirma un pendiente por teléfono o WhatsApp, con actor y fecha."""
    return await ejecutar_operacion(ciclo.ejecutar(principal, turno_id, "confirmar"))


@router.post("/{turno_id}/cancelar", response_model=TurnoRespuesta)
async def cancelar(turno_id: int, principal: Personal, ciclo: Ciclo,
                   payload: CancelarTurnoEntrada = CancelarTurnoEntrada()):
    """Cancela conservando el turno, motivo opcional y trazabilidad del personal."""
    return await ejecutar_operacion(ciclo.ejecutar(principal, turno_id, "cancelar", payload.motivo))


@router.post("/{turno_id}/liberar", response_model=TurnoRespuesta)
async def liberar(turno_id: int, principal: Personal, ciclo: Ciclo,
                  payload: AccionTurnoEntrada = AccionTurnoEntrada()):
    """Libera un pendiente si el modo es manual o tiene marca sin confirmar."""
    return await ejecutar_operacion(ciclo.ejecutar(principal, turno_id, "liberar"))


@router.post("/{turno_id}/ausente", response_model=TurnoRespuesta)
async def ausente(turno_id: int, principal: Atencion, ciclo: Ciclo,
                  payload: AccionTurnoEntrada = AccionTurnoEntrada()):
    """Marca ausente desde el instante exacto de inicio, con política centralizada."""
    return await ejecutar_operacion(ciclo.ejecutar(principal, turno_id, "ausente"))


@router.post("/{turno_id}/atendido", response_model=TurnoRespuesta)
async def atendido(turno_id: int, principal: Atencion, ciclo: Ciclo,
                   payload: AccionTurnoEntrada = AccionTurnoEntrada()):
    """Marca atendido desde el inicio; la corrección de ausente se audita aparte."""
    return await ejecutar_operacion(ciclo.ejecutar(principal, turno_id, "atendido"))
