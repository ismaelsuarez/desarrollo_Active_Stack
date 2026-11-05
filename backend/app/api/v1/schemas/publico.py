from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class ConsultaCatalogo(BaseModel):
    model_config = ConfigDict(extra='forbid')


class ConsultaDisponibilidad(ConsultaCatalogo):
    profesional_id: int = Field(gt=0)
    prestacion_id: int = Field(gt=0)
    fecha: date


class IntervaloPublico(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    inicio: datetime
    fin: datetime


class ConsultorioPublico(BaseModel):
    nombre: str
    direccion: str | None
    telefono: str | None
    zona_horaria: str


class PrestacionPublica(BaseModel):
    id: int
    nombre: str
    duracion_min: int


class ProfesionalPublico(BaseModel):
    id: int
    nombre: str
