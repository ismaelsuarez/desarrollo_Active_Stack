class RechazoPaciente(Exception):
    """Rechazo público de aplicación, sin datos privados ni detalles del motor."""

    def __init__(self, codigo: int, motivo: str) -> None:
        self.codigo = codigo
        self.motivo = motivo
        super().__init__(motivo)


def conflicto_paciente(error: Exception) -> bool:
    """Sólo conflictos esperados; asyncpg conserva el nombre en la causa."""
    original = getattr(error, "orig", None)
    while original is not None:
        estado = getattr(original, "sqlstate", None)
        if estado in ("40P01", "40001"):
            return True
        if estado == "23505" and getattr(original, "constraint_name", None) in (
            "uq_paciente_consultorio_dni", "uq_paciente_usuario_id",
        ):
            return True
        original = getattr(original, "__cause__", None)
    return False
