from app.domain.errors import ErrorDeDominio


class ConflictoDeTurno(ErrorDeDominio):
    """El turno cambió desde la lectura con la que se evaluó la operación."""

    mensaje = "el turno fue modificado por otra operación"
