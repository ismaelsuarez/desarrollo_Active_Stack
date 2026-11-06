from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.value_objects.estado_turno import EstadoTurno


class TurnoBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    paciente_nombre: str
    paciente_apellido: str
    profesional_id: int
    box_id: int
    prestacion_id: int
    prestacion_nombre: str
    inicio: datetime
    fin: datetime
    estado: EstadoTurno
    es_sobreturno: bool
    marcado_sin_confirmar_en: datetime | None


class AutorizacionOperativa(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    autorizado_por_id: int
    autorizado_en: datetime
    motivo: str
    avisado_en: datetime
    respuesta: str | None
    respondido_en: datetime | None
    respondido_por_id: int | None
    comentario: str | None


class TurnoOperativo(TurnoBase):
    autorizacion_sobreturno: AutorizacionOperativa | None = None
    acciones_permitidas: list[str]


class TurnoPaciente(TurnoBase):
    acciones_permitidas: list[str]


class HechoOperativo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int | None
    accion: str
    estado_anterior: EstadoTurno | None
    estado_nuevo: EstadoTurno
    ocurrido_en: datetime


class ConsultaAgenda(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profesional_id: int = Field(gt=0)
    fecha: date
