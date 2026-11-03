from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_sesion, requiere_rol
from app.domain.entities.auth import Principal, RolUsuario
from app.infrastructure.db.models import PrestacionModel
from app.api.v1.schemas.prestacion import (
    PrestacionActualizacion,
    PrestacionEntrada,
    PrestacionRespuesta,
)

router = APIRouter(prefix="/api/v1/prestaciones", tags=["Prestaciones"])
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
Administrador = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR))]


def es_conflicto_unicidad(error: IntegrityError) -> bool:
    causa = getattr(error.orig, "__cause__", None)
    return getattr(error.orig, "sqlstate", None) == "23505" or getattr(causa, "sqlstate", None) == "23505"


@router.get(
    "",
    response_model=list[PrestacionRespuesta],
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permisos insuficientes"}},
)
async def listar_prestaciones(principal: Administrador, sesion: Sesion) -> list[PrestacionModel]:
    prestaciones = await sesion.scalars(
        select(PrestacionModel)
        .where(PrestacionModel.consultorio_id == principal.consultorio_id)
        .order_by(PrestacionModel.nombre, PrestacionModel.id)
    )
    return list(prestaciones.all())


@router.post(
    "",
    response_model=PrestacionRespuesta,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "Ya existe una prestación con ese nombre"},
    },
)
async def crear_prestacion(
    payload: PrestacionEntrada,
    principal: Administrador,
    sesion: Sesion,
) -> PrestacionModel:
    prestacion = PrestacionModel(
        consultorio_id=principal.consultorio_id,
        nombre=payload.nombre,
        duracion_min=payload.duracion_min,
        activa=True,
        sugerida=False,
    )
    sesion.add(prestacion)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto_unicidad(error):
            raise HTTPException(409, "Ya existe una prestación con ese nombre") from None
        raise
    await sesion.refresh(prestacion)
    return prestacion


@router.patch(
    "/{prestacion_id}",
    response_model=PrestacionRespuesta,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Prestación no encontrada"},
        409: {"description": "Ya existe una prestación con ese nombre"},
    },
)
async def actualizar_prestacion(
    prestacion_id: int,
    payload: PrestacionActualizacion,
    principal: Administrador,
    sesion: Sesion,
) -> PrestacionModel:
    prestacion = await sesion.scalar(
        select(PrestacionModel).where(
            PrestacionModel.id == prestacion_id,
            PrestacionModel.consultorio_id == principal.consultorio_id,
        )
    )
    if prestacion is None:
        raise HTTPException(404, "Prestación no encontrada")

    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(prestacion, campo, valor)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto_unicidad(error):
            raise HTTPException(409, "Ya existe una prestación con ese nombre") from None
        raise
    await sesion.refresh(prestacion)
    return prestacion


@router.delete(
    "/{prestacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Prestación no encontrada"},
    },
)
async def desactivar_prestacion(
    prestacion_id: int,
    principal: Administrador,
    sesion: Sesion,
) -> Response:
    prestacion = await sesion.scalar(
        select(PrestacionModel).where(
            PrestacionModel.id == prestacion_id,
            PrestacionModel.consultorio_id == principal.consultorio_id,
        )
    )
    if prestacion is None:
        raise HTTPException(404, "Prestación no encontrada")
    prestacion.activa = False
    await sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
