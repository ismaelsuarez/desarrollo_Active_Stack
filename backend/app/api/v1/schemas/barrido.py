from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ResumenBarridoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ejecucion_id: UUID
    reclamadas: int
    enviadas: int
    reintentadas: int
    omitidas: int
    fallidas: int
