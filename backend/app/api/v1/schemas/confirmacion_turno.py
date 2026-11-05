from typing import Literal

from pydantic import BaseModel


class ConfirmacionTurnoRespuesta(BaseModel):
    turno_id: int
    estado: Literal["confirmado"]
