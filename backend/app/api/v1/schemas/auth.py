from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    """Modelo base estricto con rechazo de campos adicionales (Regla Dura 11)."""

    model_config = ConfigDict(extra="forbid")


class LoginRequest(StrictModel):
    identificador: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(StrictModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioPerfilResponse(StrictModel):
    id: int
    consultorio_id: int
    nombre_usuario: str
    email: str
    rol: str
    email_verificado: bool


class MensajeResponse(StrictModel):
    mensaje: str
