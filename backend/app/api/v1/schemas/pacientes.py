"""Entradas estrictas de las fichas de paciente."""
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.schemas.cuenta import Correo, Documento, Nombre, Telefono, Texto


class CrearPaciente(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nombre: Nombre
    apellido: Nombre
    telefono: Telefono
    email: Correo
    dni: Documento
    obra_social: Texto | None = None
    notas: str | None = None


class EditarPaciente(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    nombre: Nombre | None = None
    apellido: Nombre | None = None
    telefono: Telefono | None = None
    email: Correo | None = None
    dni: Documento | None = None
    obra_social: Texto | None = None
    notas: str | None = None

    @model_validator(mode="after")
    def validar_cambios(self) -> "EditarPaciente":
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un dato para actualizar")
        for campo in self.model_fields_set - {"obra_social", "notas"}:
            if getattr(self, campo) is None:
                raise ValueError("Los datos obligatorios no admiten null")
        return self


class ConsultaPacientes(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    apellido: Nombre | None = None
    dni: Documento | None = None
    telefono: Telefono | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
