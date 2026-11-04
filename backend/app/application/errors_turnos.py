class RechazoDeTurno(Exception):
    """Rechazo de aplicación sin datos del recurso ni detalles de persistencia."""

    def __init__(self, codigo: int, motivo: str) -> None:
        self.codigo = codigo
        self.motivo = motivo
        super().__init__(motivo)
