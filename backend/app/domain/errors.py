class ErrorDeDominio(Exception):
    """Base de los errores de reglas de negocio."""

    mensaje = "error de dominio"

    def __init__(self) -> None:
        super().__init__(self.mensaje)


class HorarioOcupado(ErrorDeDominio):
    """El profesional ya tiene un turno activo en ese horario (RN-17)."""

    mensaje = "horario ocupado"


class ProfesionalInexistente(ErrorDeDominio):
    mensaje = "profesional inexistente"


class PrestacionInexistente(ErrorDeDominio):
    mensaje = "prestación inexistente"


class InicioSinZonaHoraria(ErrorDeDominio):
    mensaje = "el inicio debe indicar zona horaria"
