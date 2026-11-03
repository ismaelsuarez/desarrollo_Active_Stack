from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, SecretStr, StringConstraints, model_validator

from app.domain.errors import DniInvalido
from app.domain.value_objects.dni import Dni

Texto = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]
Nombre = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
Telefono = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Identificador = Annotated[str, StringConstraints(strip_whitespace=True, to_lower=True, min_length=1, max_length=255)]
Correo = Annotated[str, StringConstraints(
    strip_whitespace=True, to_lower=True, max_length=255, pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$',
)]
Password = Annotated[SecretStr, Field(min_length=8, max_length=128)]


def normalizar_dni(valor: str) -> str:
    try:
        return str(Dni(valor))
    except DniInvalido as exc:
        raise ValueError(str(exc)) from None


Documento = Annotated[str, Field(max_length=20), AfterValidator(normalizar_dni)]


def aceptar_aviso(valor: object) -> Literal[True]:
    if valor is not True:
        raise ValueError('Es necesario aceptar el aviso de privacidad')
    return True


class EntradaCuenta(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)


class RegistroRequest(EntradaCuenta):
    nombre: Nombre
    apellido: Nombre
    telefono: Telefono
    email: Correo
    dni: Documento
    nombre_usuario: Identificador
    password: Password
    obra_social: Texto | None = None
    acepta_aviso_privacidad: Annotated[Literal[True], BeforeValidator(aceptar_aviso)]
    aviso_privacidad_version: str = Field(min_length=1, max_length=64)


class CorreoRequest(EntradaCuenta):
    email: Correo


class TokenRequest(EntradaCuenta):
    token: SecretStr = Field(min_length=1)


class RestablecerPasswordRequest(TokenRequest):
    password: Password


class CambiarPasswordRequest(EntradaCuenta):
    password_actual: SecretStr = Field(min_length=1)
    password_nueva: Password


class ActualizarCuentaRequest(EntradaCuenta):
    telefono: Telefono | None = None
    email: Correo | None = None

    @model_validator(mode='after')
    def requiere_contacto(self) -> 'ActualizarCuentaRequest':
        if self.telefono is None and self.email is None:
            raise ValueError('Indicá teléfono y/o correo para actualizar')
        return self
