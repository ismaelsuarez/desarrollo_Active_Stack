from datetime import datetime, time
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


NombreBox = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
NombreProfesional = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]


class BoxEntrada(Estricto):
    nombre: NombreBox


class BoxRespuesta(BaseModel):
    id: int
    nombre: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class ProfesionalEntrada(Estricto):
    usuario_id: int = Field(gt=0)
    box_id: int = Field(gt=0)
    nombre: NombreProfesional
    apellido: NombreProfesional


class ProfesionalActualizacion(Estricto):
    box_id: int | None = Field(default=None, gt=0)
    nombre: NombreProfesional | None = None
    apellido: NombreProfesional | None = None
    activo: bool | None = None

    @model_validator(mode="after")
    def validar_cambios(self):
        if not self.model_fields_set:
            raise ValueError("Indicá al menos un campo para actualizar")
        return self


class ProfesionalRespuesta(BaseModel):
    id: int
    usuario_id: int | None
    box_id: int
    nombre: str
    apellido: str
    activo: bool

    model_config = ConfigDict(from_attributes=True)


class BloqueHorario(Estricto):
    dia_semana: int = Field(ge=1, le=7)
    hora_inicio: time
    hora_fin: time

    @model_validator(mode="after")
    def validar_intervalo(self):
        if self.hora_inicio >= self.hora_fin:
            raise ValueError("La hora de inicio debe ser anterior a la hora de fin")
        return self


class HorarioEntrada(Estricto):
    bloques: list[BloqueHorario]

    @model_validator(mode="after")
    def validar_superposiciones(self):
        por_dia: dict[int, list[BloqueHorario]] = {}
        for bloque in self.bloques:
            por_dia.setdefault(bloque.dia_semana, []).append(bloque)
        for bloques in por_dia.values():
            ordenados = sorted(bloques, key=lambda bloque: bloque.hora_inicio)
            if any(actual.hora_inicio < anterior.hora_fin for anterior, actual in zip(ordenados, ordenados[1:])):
                raise ValueError("Los bloques semanales no pueden superponerse")
        return self


class HorarioRespuesta(BaseModel):
    id: int
    dia_semana: int
    hora_inicio: time
    hora_fin: time

    model_config = ConfigDict(from_attributes=True)


class BloqueoEntrada(Estricto):
    tipo: Literal["feriado", "vacaciones", "ausencia", "bloqueo"]
    inicio: datetime
    fin: datetime
    motivo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validar_intervalo_local(self):
        if self.inicio.tzinfo is not None or self.fin.tzinfo is not None:
            raise ValueError("Los bloqueos se expresan en hora local sin zona")
        if self.inicio >= self.fin:
            raise ValueError("El inicio debe ser anterior al fin")
        return self


class BloqueoRespuesta(BaseModel):
    id: int
    profesional_id: int | None
    tipo: str
    inicio: datetime
    fin: datetime
    motivo: str | None

    model_config = ConfigDict(from_attributes=True)
