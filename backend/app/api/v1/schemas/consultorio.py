from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

TelefonoConsultorio = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=40),
]


class ConfiguracionConsultorioEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    modo_liberacion: Literal["automatico", "manual"] | None = None
    horas_confirmacion: int | None = Field(default=None, ge=1)
    horas_recordatorio: int | None = Field(default=None, ge=1)
    horas_liberacion: int | None = Field(default=None, ge=1)
    horas_limite_paciente: int | None = Field(default=None, ge=1)
    telefono: TelefonoConsultorio | None = None
    minutos_granularidad: int | None = Field(default=None, ge=5, le=120)
    dias_anticipacion_maxima: int | None = Field(default=None, ge=1)
    max_turnos_activos_paciente: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def requiere_cambios(self) -> "ConfiguracionConsultorioEntrada":
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un parámetro para actualizar")
        return self


class ConfiguracionConsultorioCompleta(BaseModel):
    modo_liberacion: Literal["automatico", "manual"]
    horas_confirmacion: int = Field(ge=1)
    horas_recordatorio: int = Field(ge=1)
    horas_liberacion: int = Field(ge=1)
    horas_limite_paciente: int = Field(ge=1)
    telefono: TelefonoConsultorio | None
    minutos_granularidad: int = Field(ge=5, le=120)
    dias_anticipacion_maxima: int = Field(ge=1)
    max_turnos_activos_paciente: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    @model_validator(mode="after")
    def plazos_en_orden(self) -> "ConfiguracionConsultorioCompleta":
        if not (
            self.horas_confirmacion
            > self.horas_recordatorio
            > self.horas_liberacion
            > 0
        ):
            raise ValueError(
                "Los plazos deben cumplir confirmación > recordatorio > liberación > 0"
            )
        return self


class ConfiguracionConsultorioRespuesta(BaseModel):
    modo_liberacion: str
    horas_confirmacion: int
    horas_recordatorio: int
    horas_liberacion: int
    horas_limite_paciente: int
    telefono: str | None
    minutos_granularidad: int
    dias_anticipacion_maxima: int
    max_turnos_activos_paciente: int

    model_config = ConfigDict(from_attributes=True)
