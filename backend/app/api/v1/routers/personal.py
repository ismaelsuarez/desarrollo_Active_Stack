from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_reloj, get_sesion, requiere_rol
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.models import UsuarioModel
from app.api.v1.schemas.personal import (
    PersonalActualizacion,
    PersonalEntrada,
    PersonalRespuesta,
)

router = APIRouter(prefix="/api/v1/usuarios", tags=["Personal"])
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
RelojActual = Annotated[Reloj, Depends(get_reloj)]
Administrador = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR))]
HASHEADOR = PasswordHash.recommended()


def es_conflicto_unicidad(error: IntegrityError) -> bool:
    causa = getattr(error.orig, "__cause__", None)
    return getattr(error.orig, "sqlstate", None) == "23505" or getattr(causa, "sqlstate", None) == "23505"


@router.get(
    "",
    response_model=list[PersonalRespuesta],
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permisos insuficientes"}},
)
async def listar_personal(principal: Administrador, sesion: Sesion) -> list[UsuarioModel]:
    resultado = await sesion.scalars(
        select(UsuarioModel)
        .where(
            UsuarioModel.consultorio_id == principal.consultorio_id,
            UsuarioModel.rol != RolUsuario.PACIENTE.value,
        )
        .order_by(UsuarioModel.nombre_usuario, UsuarioModel.id)
    )
    return list(resultado.all())


@router.post(
    "",
    response_model=PersonalRespuesta,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        409: {"description": "El nombre de usuario o correo ya está registrado"},
    },
)
async def crear_personal(
    payload: PersonalEntrada,
    principal: Administrador,
    sesion: Sesion,
    reloj: RelojActual,
) -> UsuarioModel:
    ahora = reloj.ahora()
    usuario = UsuarioModel(
        consultorio_id=principal.consultorio_id,
        nombre_usuario=payload.nombre_usuario,
        email=payload.email,
        password_hash=HASHEADOR.hash(payload.password.get_secret_value()),
        rol=payload.rol,
        email_verificado=False,
        email_verificado_en=None,
        aviso_privacidad_aceptado_en=None,
        aviso_privacidad_version=None,
        activo=True,
        creado_en=ahora,
        actualizado_en=ahora,
    )
    sesion.add(usuario)
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto_unicidad(error):
            raise HTTPException(409, "El nombre de usuario o correo ya está registrado") from None
        raise
    await sesion.refresh(usuario)
    return usuario


@router.patch(
    "/{usuario_id}",
    response_model=PersonalRespuesta,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Personal no encontrado"},
        409: {"description": "El nombre de usuario o correo ya está registrado"},
    },
)
async def actualizar_personal(
    usuario_id: int,
    payload: PersonalActualizacion,
    principal: Administrador,
    sesion: Sesion,
    reloj: RelojActual,
) -> UsuarioModel:
    usuario = await sesion.scalar(
        select(UsuarioModel).where(
            UsuarioModel.id == usuario_id,
            UsuarioModel.consultorio_id == principal.consultorio_id,
            UsuarioModel.rol != RolUsuario.PACIENTE.value,
        )
    )
    if usuario is None:
        raise HTTPException(404, "Personal no encontrado")
    for campo, valor in payload.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)
    usuario.actualizado_en = reloj.ahora()
    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_conflicto_unicidad(error):
            raise HTTPException(409, "El nombre de usuario o correo ya está registrado") from None
        raise
    await sesion.refresh(usuario)
    return usuario


@router.delete(
    "/{usuario_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Personal no encontrado"},
    },
)
async def desactivar_personal(
    usuario_id: int,
    principal: Administrador,
    sesion: Sesion,
    reloj: RelojActual,
) -> Response:
    usuario = await sesion.scalar(
        select(UsuarioModel).where(
            UsuarioModel.id == usuario_id,
            UsuarioModel.consultorio_id == principal.consultorio_id,
            UsuarioModel.rol != RolUsuario.PACIENTE.value,
        )
    )
    if usuario is None:
        raise HTTPException(404, "Personal no encontrado")
    usuario.activo = False
    usuario.actualizado_en = reloj.ahora()
    await sesion.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

