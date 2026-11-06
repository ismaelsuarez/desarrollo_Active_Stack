from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

EstadoNotificacion = Literal["programada", "enviando", "enviada", "fallida", "preparada", "enviada_manual", "omitida"]


class EnlaceWhatsApp(BaseModel):
    id: int
    enlace_whatsapp: str


class EnvioManual(BaseModel):
    id: int
    estado: Literal['enviada_manual']
    enviada_en: datetime


class ConsultaNotificaciones(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estado: EstadoNotificacion | None = None
    canal: Literal['email', 'whatsapp'] | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class NotificacionOperativa(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    turno_id: int | None
    tipo: str
    canal: str
    estado: EstadoNotificacion
    intentos: int
    programada_para: datetime
    reclamada_en: datetime | None
    enviada_en: datetime | None


class EstadoBarrido(BaseModel):
    ejecucion_id: UUID
    iniciado_en: datetime
    finalizado_en: datetime | None
    estado: Literal["en_curso", "exitoso", "error"]
    reclamadas: int
    enviadas: int
    reintentadas: int
    omitidas: int
    fallidas: int


class IndicadoresNotificaciones(BaseModel):
    fallidas: int
    programada_mas_antigua_segundos: float | None
    enviando: int
    enviando_mas_antigua_segundos: float | None
    correos_del_dia: int
    limite_diario: int
    limite_cuenta: int
    alerta: bool
    ultimo_barrido: EstadoBarrido | None
