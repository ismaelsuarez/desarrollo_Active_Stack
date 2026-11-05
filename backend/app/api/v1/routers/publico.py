"""Lecturas mínimas del consultorio resuelto por el servidor (RN-59)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import consultorio_sin_token, get_sesion, get_reloj, get_settings
from app.api.v1.schemas.publico import (
    ConsultaCatalogo, ConsultorioPublico, PrestacionPublica, ProfesionalPublico,
    ConsultaDisponibilidad, IntervaloPublico,
)
from app.domain.ports.reloj import Reloj
from app.application.use_cases.consultar_disponibilidad import ConsultarDisponibilidad
from app.infrastructure.db.unidad_de_trabajo import UnidadDeTrabajoSQL
from app.application.services.limite_publico import LimitePublico
from app.core.config import Settings
from app.domain.services.auth_crypto import calcular_origen_hash, resolver_ip_origen
from app.infrastructure.db.models import ConsultorioModel, PrestacionModel, ProfesionalModel

async def limitar_lecturas(request: Request, reloj: Annotated[Reloj, Depends(get_reloj)],
                           settings: Annotated[Settings, Depends(get_settings)]) -> None:
    if not hasattr(request.app.state, 'limite_publico'):
        request.app.state.limite_publico = LimitePublico()
    ip = resolver_ip_origen(request.client.host if request.client else None,
                           request.headers.get('x-forwarded-for'), settings.trusted_proxy_hops)
    origen = calcular_origen_hash(ip, settings.origin_hash_secret.get_secret_value()) or 'origen-desconocido'
    demora = request.app.state.limite_publico.consumir(origen, reloj.ahora())
    if demora:
        raise HTTPException(429, 'Límite de lecturas públicas excedido', headers={'Retry-After': str(demora)})


router = APIRouter(prefix='/api/v1/publico', tags=['Público'], dependencies=[Depends(limitar_lecturas)],
    responses={429: {'description': 'Cuota compartida por origen y proceso; reintentar según Retry-After',
                     'headers': {'Retry-After': {'schema': {'type': 'integer'}, 'description': 'Segundos hasta renovar cuota'}}}})
Consultorio = Annotated[ConsultorioModel, Depends(consultorio_sin_token)]
Sesion = Annotated[AsyncSession, Depends(get_sesion)]
Catalogo = Annotated[ConsultaCatalogo, Query()]


@router.get('/consultorio', response_model=ConsultorioPublico)
async def consultorio(consulta: Catalogo, consultorio: Consultorio):
    return ConsultorioPublico(nombre=consultorio.nombre, direccion=consultorio.direccion,
                              telefono=consultorio.telefono, zona_horaria=consultorio.zona_horaria)


@router.get('/prestaciones', response_model=list[PrestacionPublica])
async def prestaciones(consulta: Catalogo, consultorio: Consultorio, sesion: Sesion):
    filas = await sesion.execute(select(PrestacionModel.id, PrestacionModel.nombre, PrestacionModel.duracion_min).where(
        PrestacionModel.consultorio_id == consultorio.id, PrestacionModel.activa.is_(True),
    ).order_by(PrestacionModel.nombre, PrestacionModel.id))
    return [PrestacionPublica(id=f.id, nombre=f.nombre, duracion_min=f.duracion_min) for f in filas]


@router.get('/profesionales', response_model=list[ProfesionalPublico])
async def profesionales(consulta: Catalogo, consultorio: Consultorio, sesion: Sesion):
    filas = await sesion.execute(select(ProfesionalModel.id, ProfesionalModel.nombre, ProfesionalModel.apellido).where(
        ProfesionalModel.consultorio_id == consultorio.id, ProfesionalModel.activo.is_(True),
    ).order_by(ProfesionalModel.apellido, ProfesionalModel.nombre, ProfesionalModel.id))
    return [ProfesionalPublico(id=f.id, nombre=f'{f.nombre} {f.apellido}') for f in filas]


@router.get('/disponibilidad', response_model=list[IntervaloPublico])
async def disponibilidad(request: Request, consulta: Annotated[ConsultaDisponibilidad, Query()],
                         consultorio: Consultorio, reloj: Annotated[Reloj, Depends(get_reloj)]):
    unidades = lambda: UnidadDeTrabajoSQL(request.app.state.session_factory, reloj)
    return await ConsultarDisponibilidad(unidades, reloj).consultar(consultorio.id,
        consulta.profesional_id, consulta.prestacion_id, consulta.fecha)
