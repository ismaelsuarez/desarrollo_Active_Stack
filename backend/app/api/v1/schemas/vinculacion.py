from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from app.api.v1.schemas.cuenta import Texto


class EntradaVinculacion(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)


class VincularRequest(EntradaVinculacion):
    paciente_id: int = Field(gt=0)


class ConsultaSolicitudes(EntradaVinculacion):
    estado: Literal["pendiente", "vinculada", "rechazada"] | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class RechazarRequest(EntradaVinculacion):
    motivo: Texto | None = None


class DesvincularRequest(EntradaVinculacion):
    motivo: Texto
