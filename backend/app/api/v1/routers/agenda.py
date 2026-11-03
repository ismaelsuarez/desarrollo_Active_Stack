from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_reloj, get_sesion, requiere_rol
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.models import (
    BloqueoAgendaModel, BoxModel, ConsultorioModel, HorarioSemanalModel,
    ProfesionalModel, TurnoModel, UsuarioModel,
)
from app.api.v1.schemas.agenda import (
    BloqueHorario, BloqueoEntrada, BloqueoRespuesta, BoxEntrada, BoxRespuesta,
    HorarioEntrada, HorarioRespuesta, ProfesionalActualizacion, ProfesionalEntrada,
    ProfesionalRespuesta,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["Configuración de agenda"],
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
    },
)
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
RelojActual = Annotated[Reloj, Depends(get_reloj)]
Administrador = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR))]


def es_conflicto(error: IntegrityError) -> bool:
    causa = getattr(error.orig, "__cause__", None)
    return getattr(error.orig, "sqlstate", None) == "23505" or getattr(causa, "sqlstate", None) == "23505"


async def validar_profesional(sesion: AsyncSession, consultorio_id: int, profesional_id: int) -> ProfesionalModel:
    profesional = await sesion.scalar(select(ProfesionalModel).where(
        ProfesionalModel.id == profesional_id,
        ProfesionalModel.consultorio_id == consultorio_id,
        ProfesionalModel.activo.is_(True),
    ))
    if profesional is None:
        raise HTTPException(404, "Profesional no encontrado")
    return profesional


@router.get("/boxes", response_model=list[BoxRespuesta])
async def listar_boxes(principal: Administrador, sesion: Sesion) -> list[BoxModel]:
    filas = await sesion.scalars(select(BoxModel).where(BoxModel.consultorio_id == principal.consultorio_id).order_by(BoxModel.nombre))
    return list(filas.all())


@router.post("/boxes", response_model=BoxRespuesta, status_code=201, responses={409: {"description": "Nombre duplicado"}})
async def crear_box(payload: BoxEntrada, principal: Administrador, sesion: Sesion) -> BoxModel:
    box = BoxModel(consultorio_id=principal.consultorio_id, nombre=payload.nombre, activo=True)
    sesion.add(box)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto(error):
            raise HTTPException(409, "Ya existe un box con ese nombre") from None
        raise
    await sesion.refresh(box)
    return box


@router.get("/profesionales", response_model=list[ProfesionalRespuesta])
async def listar_profesionales(principal: Administrador, sesion: Sesion) -> list[ProfesionalModel]:
    filas = await sesion.scalars(select(ProfesionalModel).where(ProfesionalModel.consultorio_id == principal.consultorio_id).order_by(ProfesionalModel.apellido, ProfesionalModel.nombre))
    return list(filas.all())


@router.post("/profesionales", response_model=ProfesionalRespuesta, status_code=201, responses={404: {"description": "Cuenta o box no encontrado"}, 409: {"description": "Asociación duplicada"}})
async def crear_profesional(payload: ProfesionalEntrada, principal: Administrador, sesion: Sesion) -> ProfesionalModel:
    usuario = await sesion.scalar(select(UsuarioModel).where(
        UsuarioModel.id == payload.usuario_id,
        UsuarioModel.consultorio_id == principal.consultorio_id,
        UsuarioModel.activo.is_(True),
    ))
    if usuario is None:
        raise HTTPException(404, "Cuenta no encontrada")
    if usuario.rol not in (RolUsuario.PROFESIONAL.value, RolUsuario.ADMINISTRADOR.value):
        raise HTTPException(422, "La cuenta debe tener rol profesional o administrador")
    box = await sesion.scalar(select(BoxModel).where(
        BoxModel.id == payload.box_id,
        BoxModel.consultorio_id == principal.consultorio_id,
        BoxModel.activo.is_(True),
    ))
    if box is None:
        raise HTTPException(404, "Box no encontrado")
    profesional = ProfesionalModel(
        consultorio_id=principal.consultorio_id, usuario_id=usuario.id,
        box_id=box.id, nombre=payload.nombre, apellido=payload.apellido, activo=True,
    )
    sesion.add(profesional)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto(error):
            raise HTTPException(409, "La cuenta o el box ya está asociado") from None
        raise
    await sesion.refresh(profesional)
    return profesional


@router.patch("/profesionales/{profesional_id}", response_model=ProfesionalRespuesta, responses={404: {"description": "Profesional o box no encontrado"}, 409: {"description": "Box ya asignado"}})
async def actualizar_profesional(profesional_id: int, payload: ProfesionalActualizacion, principal: Administrador, sesion: Sesion) -> ProfesionalModel:
    profesional = await sesion.scalar(select(ProfesionalModel).where(
        ProfesionalModel.id == profesional_id,
        ProfesionalModel.consultorio_id == principal.consultorio_id,
    ))
    if profesional is None:
        raise HTTPException(404, "Profesional no encontrado")
    cambios = payload.model_dump(exclude_unset=True)
    if "box_id" in cambios:
        box = await sesion.scalar(select(BoxModel).where(
            BoxModel.id == cambios["box_id"],
            BoxModel.consultorio_id == principal.consultorio_id,
            BoxModel.activo.is_(True),
        ))
        if box is None:
            raise HTTPException(404, "Box no encontrado")
    for campo, valor in cambios.items():
        setattr(profesional, campo, valor)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto(error):
            raise HTTPException(409, "El box ya está asignado") from None
        raise
    await sesion.refresh(profesional)
    return profesional


@router.get("/profesionales/{profesional_id}/horario-semanal", response_model=dict[str, list[HorarioRespuesta]], responses={404: {"description": "Profesional no encontrado"}})
async def leer_horario(profesional_id: int, principal: Administrador, sesion: Sesion) -> dict[str, list[HorarioSemanalModel]]:
    await validar_profesional(sesion, principal.consultorio_id, profesional_id)
    filas = await sesion.scalars(select(HorarioSemanalModel).where(
        HorarioSemanalModel.consultorio_id == principal.consultorio_id,
        HorarioSemanalModel.profesional_id == profesional_id,
    ).order_by(HorarioSemanalModel.dia_semana, HorarioSemanalModel.hora_inicio))
    return {"bloques": list(filas.all())}


@router.put("/profesionales/{profesional_id}/horario-semanal", response_model=dict[str, list[HorarioRespuesta]], responses={404: {"description": "Profesional no encontrado"}})
async def reemplazar_horario(profesional_id: int, payload: HorarioEntrada, principal: Administrador, sesion: Sesion) -> dict[str, list[HorarioSemanalModel]]:
    await validar_profesional(sesion, principal.consultorio_id, profesional_id)
    await sesion.execute(delete(HorarioSemanalModel).where(
        HorarioSemanalModel.consultorio_id == principal.consultorio_id,
        HorarioSemanalModel.profesional_id == profesional_id,
    ))
    bloques = [HorarioSemanalModel(
        consultorio_id=principal.consultorio_id, profesional_id=profesional_id,
        dia_semana=b.dia_semana, hora_inicio=b.hora_inicio, hora_fin=b.hora_fin,
    ) for b in payload.bloques]
    sesion.add_all(bloques)
    await sesion.commit()
    return {"bloques": sorted(bloques, key=lambda b: (b.dia_semana, b.hora_inicio))}


async def _consultorio(sesion: AsyncSession, consultorio_id: int) -> ConsultorioModel:
    consultorio = await sesion.get(ConsultorioModel, consultorio_id)
    if consultorio is None:
        raise HTTPException(404, "Consultorio no encontrado")
    return consultorio


async def _crear_bloqueo(profesional_id: int | None, payload: BloqueoEntrada, principal: Principal, sesion: AsyncSession, reloj: Reloj) -> BloqueoRespuesta | dict[str, list[int]]:
    if profesional_id is not None:
        await validar_profesional(sesion, principal.consultorio_id, profesional_id)
    consultorio = await _consultorio(sesion, principal.consultorio_id)
    zona = ZoneInfo(consultorio.zona_horaria)
    inicio = payload.inicio.replace(tzinfo=zona)
    fin = payload.fin.replace(tzinfo=zona)
    consulta_turnos = select(TurnoModel.id).where(
        TurnoModel.consultorio_id == principal.consultorio_id,
        TurnoModel.estado.in_(["pendiente", "confirmado", "atendido", "ausente"]),
        TurnoModel.inicio < fin,
        TurnoModel.fin > inicio,
    )
    if profesional_id is not None:
        consulta_turnos = consulta_turnos.where(TurnoModel.profesional_id == profesional_id)
    afectados = list((await sesion.scalars(consulta_turnos.order_by(TurnoModel.inicio))).all())
    if afectados:
        return {"turnos_afectados": afectados}
    bloqueo = BloqueoAgendaModel(
        consultorio_id=principal.consultorio_id, profesional_id=profesional_id,
        tipo=payload.tipo, inicio=inicio, fin=fin, motivo=payload.motivo,
        creado_por_id=principal.usuario_id, creado_en=reloj.ahora(),
    )
    sesion.add(bloqueo)
    await sesion.commit()
    await sesion.refresh(bloqueo)
    return BloqueoRespuesta.model_validate(bloqueo)


@router.get("/bloqueos", response_model=list[BloqueoRespuesta])
async def listar_bloqueos_globales(principal: Administrador, sesion: Sesion) -> list[BloqueoAgendaModel]:
    filas = await sesion.scalars(select(BloqueoAgendaModel).where(
        BloqueoAgendaModel.consultorio_id == principal.consultorio_id,
        BloqueoAgendaModel.profesional_id.is_(None),
    ).order_by(BloqueoAgendaModel.inicio))
    return list(filas.all())


@router.post("/bloqueos", status_code=201, responses={409: {"description": "Turnos pendientes de resolver"}})
async def crear_bloqueo_global(payload: BloqueoEntrada, principal: Administrador, sesion: Sesion, reloj: RelojActual):
    resultado = await _crear_bloqueo(None, payload, principal, sesion, reloj)
    if isinstance(resultado, dict):
        raise HTTPException(409, detail=resultado)
    return resultado


@router.get("/profesionales/{profesional_id}/bloqueos", response_model=list[BloqueoRespuesta])
async def listar_bloqueos_profesional(profesional_id: int, principal: Administrador, sesion: Sesion) -> list[BloqueoAgendaModel]:
    await validar_profesional(sesion, principal.consultorio_id, profesional_id)
    filas = await sesion.scalars(select(BloqueoAgendaModel).where(
        BloqueoAgendaModel.consultorio_id == principal.consultorio_id,
        or_(
            BloqueoAgendaModel.profesional_id == profesional_id,
            BloqueoAgendaModel.profesional_id.is_(None),
        ),
    ).order_by(BloqueoAgendaModel.inicio))
    return list(filas.all())


@router.post("/profesionales/{profesional_id}/bloqueos", status_code=201, responses={409: {"description": "Turnos pendientes de resolver"}})
async def crear_bloqueo_profesional(profesional_id: int, payload: BloqueoEntrada, principal: Administrador, sesion: Sesion, reloj: RelojActual):
    resultado = await _crear_bloqueo(profesional_id, payload, principal, sesion, reloj)
    if isinstance(resultado, dict):
        raise HTTPException(409, detail=resultado)
    return resultado


@router.delete("/bloqueos/{bloqueo_id}", status_code=204, responses={404: {"description": "Bloqueo no encontrado"}})
async def eliminar_bloqueo(bloqueo_id: int, principal: Administrador, sesion: Sesion) -> Response:
    bloqueo = await sesion.scalar(select(BloqueoAgendaModel).where(
        BloqueoAgendaModel.id == bloqueo_id,
        BloqueoAgendaModel.consultorio_id == principal.consultorio_id,
    ))
    if bloqueo is None:
        raise HTTPException(404, "Bloqueo no encontrado")
    await sesion.delete(bloqueo)
    await sesion.commit()
    return Response(status_code=204)
