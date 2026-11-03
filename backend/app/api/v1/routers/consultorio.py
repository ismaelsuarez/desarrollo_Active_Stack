from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_reloj, get_sesion, requiere_rol
from app.api.v1.schemas.consultorio import (
    ConfiguracionConsultorioCompleta,
    ConfiguracionConsultorioEntrada,
    ConfiguracionConsultorioRespuesta,
)
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.models import ConsultorioModel

router = APIRouter(prefix="/api/v1/consultorio", tags=["Configuración del consultorio"])
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
RelojActual = Annotated[Reloj, Depends(get_reloj)]
Administrador = Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR))]


def validar_configuracion(datos: dict[str, object]) -> ConfiguracionConsultorioCompleta:
    try:
        return ConfiguracionConsultorioCompleta.model_validate(datos)
    except ValidationError:
        raise HTTPException(422, "La configuración del consultorio no es válida") from None


def es_check_constraint(error: IntegrityError) -> bool:
    causa = getattr(error.orig, "__cause__", None)
    return getattr(error.orig, "sqlstate", None) == "23514" or getattr(causa, "sqlstate", None) == "23514"


@router.get(
    "",
    response_model=ConfiguracionConsultorioRespuesta,
    responses={401: {"description": "No autenticado"}, 403: {"description": "Permisos insuficientes"}},
)
async def consultar_configuracion(
    principal: Administrador,
    sesion: Sesion,
) -> ConsultorioModel:
    consultorio = await sesion.scalar(
        select(ConsultorioModel).where(ConsultorioModel.id == principal.consultorio_id)
    )
    if consultorio is None:
        raise HTTPException(404, "Consultorio no encontrado")
    return consultorio


@router.patch(
    "",
    response_model=ConfiguracionConsultorioRespuesta,
    responses={
        401: {"description": "No autenticado"},
        403: {"description": "Permisos insuficientes"},
        404: {"description": "Consultorio no encontrado"},
    },
)
async def actualizar_configuracion(
    payload: ConfiguracionConsultorioEntrada,
    principal: Administrador,
    sesion: Sesion,
    reloj: RelojActual,
) -> ConsultorioModel:
    consultorio = await sesion.scalar(
        select(ConsultorioModel).where(ConsultorioModel.id == principal.consultorio_id)
    )
    if consultorio is None:
        raise HTTPException(404, "Consultorio no encontrado")

    campos = (
        "modo_liberacion",
        "horas_confirmacion",
        "horas_recordatorio",
        "horas_liberacion",
        "horas_limite_paciente",
        "telefono",
        "minutos_granularidad",
        "dias_anticipacion_maxima",
        "max_turnos_activos_paciente",
    )
    valores = {campo: getattr(consultorio, campo) for campo in campos}
    valores.update(payload.model_dump(exclude_unset=True))
    configuracion = validar_configuracion(valores)
    for campo, valor in configuracion.model_dump().items():
        setattr(consultorio, campo, valor)
    consultorio.actualizado_en = reloj.ahora()

    try:
        await sesion.commit()
    except IntegrityError as error:
        await sesion.rollback()
        if es_check_constraint(error):
            raise HTTPException(422, "La configuración del consultorio no es válida") from None
        raise
    await sesion.refresh(consultorio)
    return consultorio
