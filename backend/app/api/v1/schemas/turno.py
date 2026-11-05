from datetime import datetime

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.domain.value_objects.estado_turno import EstadoTurno


class TurnoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paciente_id: int = Field(gt=0)
    profesional_id: int = Field(gt=0)
    prestacion_id: int = Field(gt=0)
    inicio: AwareDatetime
    duracion_min: int | None = Field(default=None, gt=0)
    confirmar: bool = False


class TurnoOnlineEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profesional_id: int = Field(gt=0)
    prestacion_id: int = Field(gt=0)
    inicio: AwareDatetime


class TurnoRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paciente_id: int
    profesional_id: int
    box_id: int
    prestacion_id: int
    inicio: datetime
    fin: datetime
    estado: EstadoTurno
    es_sobreturno: bool
    ciclo_confirmacion: int


class ReprogramacionEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: AwareDatetime
    duracion_min: int | None = Field(default=None, gt=0)


class ReprogramacionOnlineEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inicio: AwareDatetime
