from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints, model_validator

RolPersonal = Literal["administrador", "recepcion", "profesional", "administrativo"]
TextoNormalizado = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=255)]
EmailNormalizado = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=3, max_length=255)]


class PersonalBase(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class PersonalEntrada(PersonalBase):
    nombre_usuario: TextoNormalizado
    email: EmailNormalizado
    password: SecretStr = Field(min_length=12, max_length=128)
    rol: RolPersonal


class PersonalActualizacion(PersonalBase):
    nombre_usuario: TextoNormalizado | None = None
    email: EmailNormalizado | None = None
    rol: RolPersonal | None = None

    @model_validator(mode="after")
    def requiere_cambios(self) -> "PersonalActualizacion":
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un campo para actualizar")
        return self


class PersonalRespuesta(PersonalBase):
    id: int
    nombre_usuario: str
    email: str
    rol: RolPersonal
    activo: bool
