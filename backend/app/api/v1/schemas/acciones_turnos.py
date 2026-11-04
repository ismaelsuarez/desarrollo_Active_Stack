from pydantic import BaseModel, ConfigDict


class AccionTurnoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CancelarTurnoEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid")

    motivo: str | None = None
