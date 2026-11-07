from datetime import date, datetime, time, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_reloj, get_sesion, requiere_rol
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.ports.reloj import Reloj
from app.infrastructure.db.models import ConsultorioModel, ProfesionalModel, TurnoModel

router = APIRouter(prefix='/api/v1/indicadores', tags=['Indicadores'])


class Filtros(BaseModel):
    model_config = ConfigDict(extra='forbid')
    desde: date
    hasta: date
    profesional_id: int | None = Field(default=None, gt=0)


class Recuento(BaseModel):
    ausentes: int
    atendidos: int
    cancelados: int
    liberados: int
    sin_cierre: int
    tasa: float | None


class RecuentoMensual(Recuento):
    mes: str


class RecuentoProfesional(Recuento):
    profesional_id: int
    nombre: str


class InformeAusentismo(BaseModel):
    resumen: Recuento
    evolucion: list[RecuentoMensual]
    profesionales: list[RecuentoProfesional]


def vacio():
    return {'ausentes': 0, 'atendidos': 0, 'cancelados': 0, 'liberados': 0, 'sin_cierre': 0, 'tasa': None}


def sumar(conteos, estado, cantidad):
    campo = {'ausente': 'ausentes', 'atendido': 'atendidos', 'cancelado': 'cancelados',
             'liberado': 'liberados', 'pendiente': 'sin_cierre', 'confirmado': 'sin_cierre'}[estado]
    conteos[campo] += cantidad
    denominador = conteos['ausentes'] + conteos['atendidos']
    conteos['tasa'] = conteos['ausentes'] / denominador if denominador else None


@router.get('/ausentismo', response_model=InformeAusentismo)
async def ausentismo(principal: Annotated[Principal, Depends(requiere_rol(RolUsuario.ADMINISTRADOR))],
                     filtros: Annotated[Filtros, Query()],
                     sesion: Annotated[AsyncSession, Depends(get_sesion)],
                     reloj: Annotated[Reloj, Depends(get_reloj)]):
    if filtros.desde > filtros.hasta or filtros.hasta == date.max:
        raise HTTPException(status_code=422, detail='Período inválido')
    zona_nombre = await sesion.scalar(select(ConsultorioModel.zona_horaria).where(ConsultorioModel.id == principal.consultorio_id))
    if zona_nombre is None:
        raise HTTPException(status_code=404, detail='Consultorio no encontrado')
    zona = ZoneInfo(zona_nombre)
    inicio = datetime.combine(filtros.desde, time.min, tzinfo=zona)
    fin = datetime.combine(filtros.hasta + timedelta(days=1), time.min, tzinfo=zona)
    mes = func.to_char(func.timezone(zona_nombre, TurnoModel.inicio), 'YYYY-MM')
    consulta = (select(TurnoModel.profesional_id, ProfesionalModel.nombre, ProfesionalModel.apellido,
                       mes.label('mes'), TurnoModel.estado, func.count())
        .join(ProfesionalModel, (ProfesionalModel.id == TurnoModel.profesional_id) & (ProfesionalModel.consultorio_id == TurnoModel.consultorio_id))
        .where(TurnoModel.consultorio_id == principal.consultorio_id, TurnoModel.inicio >= inicio,
               TurnoModel.inicio < fin, TurnoModel.inicio <= reloj.ahora())
        .group_by(TurnoModel.profesional_id, ProfesionalModel.nombre, ProfesionalModel.apellido, mes, TurnoModel.estado))
    if filtros.profesional_id is not None:
        consulta = consulta.where(TurnoModel.profesional_id == filtros.profesional_id)
    resumen, meses, profesionales = vacio(), {}, {}
    for pid, nombre, apellido, periodo, estado, cantidad in (await sesion.execute(consulta)).all():
        mes_actual = meses.setdefault(periodo, vacio())
        profesional = profesionales.setdefault(pid, {'profesional_id': pid, 'nombre': f'{nombre} {apellido}', **vacio()})
        for conteos in (resumen, mes_actual, profesional):
            sumar(conteos, estado.value, cantidad)
    return {'resumen': resumen,
            'evolucion': [{'mes': key, **meses[key]} for key in sorted(meses)],
            'profesionales': [profesionales[key] for key in sorted(profesionales)]}
