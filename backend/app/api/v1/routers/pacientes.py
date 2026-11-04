from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request

from app.api.deps import get_reloj, get_settings, requiere_rol
from app.api.v1.schemas.pacientes import ConsultaPacientes, CrearPaciente, EditarPaciente
from app.api.v1.routers.cuentas import CorreoSalida, Configuracion, RelojActual, programar_despacho
from app.application.use_cases.gestionar_pacientes import GestionarPacientes
from app.core.config import Settings
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.sesion import crear_engine, crear_fabrica_de_sesiones
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL

router = APIRouter(prefix="/api/v1/pacientes", tags=["Pacientes"], responses={
    401: {"description": "No autenticado"},
    403: {"description": "Acción no permitida para el rol"},
    404: {"description": "Ficha inexistente o fuera del alcance autorizado"},
    409: {"description": "Conflicto con el estado actual de los datos"},
    422: {"description": "Entrada inválida o campo no declarado"},
})
Personal = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION))]
Editor = Annotated[Principal, Depends(requiere_rol(
    RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PACIENTE,
))]
Lector = Annotated[Principal, Depends(requiere_rol(
    RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PROFESIONAL, RolUsuario.PACIENTE,
))]


def get_gestion(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                settings: Annotated[Settings, Depends(get_settings)]) -> GestionarPacientes:
    if not hasattr(request.app.state, "session_factory"):
        request.app.state.engine = crear_engine(settings.database_url.get_secret_value())
        request.app.state.session_factory = crear_fabrica_de_sesiones(request.app.state.engine)
    return GestionarPacientes(lambda: UnidadDeTrabajoSQL(request.app.state.session_factory), reloj, settings)


Gestion = Annotated[GestionarPacientes, Depends(get_gestion)]


@router.post("", status_code=201, summary="Crear ficha mínima sin cuenta",
             description="Recepción y Administrador crean una ficha en su consultorio. DNI duplicado: 409; no acepta activo, usuario_id ni consultorio_id.")
async def crear_ficha(payload: CrearPaciente, principal: Personal, gestion: Gestion) -> dict:
    return await gestion.crear(principal, payload.model_dump())


@router.get("", summary="Buscar fichas con paginación")
async def listar_fichas(parametros: Annotated[ConsultaPacientes, Query()], principal: Lector, gestion: Gestion) -> dict:
    return await gestion.listar(principal, **parametros.model_dump())


@router.get("/{paciente_id}", summary="Consultar ficha autorizada",
            description="Personal: ficha de su consultorio y cuenta mínima o null. Profesional: pacientes de su agenda. Paciente: ficha vigente. Los otros roles lectores no reciben el bloque cuenta.")
async def detalle_ficha(paciente_id: int, principal: Lector, gestion: Gestion) -> dict:
    return await gestion.detalle(principal, paciente_id)


@router.patch("/{paciente_id}", summary="Corregir datos de la ficha",
              description="Personal corrige la ficha sin cambiar login ni turnos. Paciente sólo teléfono/correo propios; un correo diferente exige reverificación y se despacha tras commit. Campos omitidos se conservan; sólo obra_social/notas admiten null. No permite activo ni vínculo.")
async def editar_ficha(paciente_id: int, payload: EditarPaciente, principal: Editor, gestion: Gestion,
                       request: Request, tareas: BackgroundTasks, reloj: RelojActual,
                       enviador: CorreoSalida, settings: Configuracion) -> dict:
    if principal.rol == RolUsuario.PACIENTE:
        notificacion_id = await gestion.editar_contacto(principal, paciente_id, payload.model_dump(exclude_unset=True))
        programar_despacho(tareas, request, principal.consultorio_id, notificacion_id,
                          reloj, enviador, settings)
        return {"id": paciente_id}
    return await gestion.editar(principal, paciente_id, payload.model_dump(exclude_unset=True))
