from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NombrePrestacion = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=160),
]


class PrestacionEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nombre: NombrePrestacion
    duracion_min: int = Field(gt=0)


class PrestacionActualizacion(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nombre: NombrePrestacion | None = None
    duracion_min: int | None = Field(default=None, gt=0)
    activa: bool | None = None

    @model_validator(mode="after")
    def requiere_cambios(self) -> "PrestacionActualizacion":
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un campo para actualizar")
        return self


class PrestacionRespuesta(BaseModel):
    id: int
    nombre: str
    duracion_min: int
    activa: bool
    sugerida: bool

    model_config = ConfigDict(from_attributes=True)
