from collections.abc import Awaitable
from typing import TypeVar

from fastapi import HTTPException

from app.domain.errors import HorarioOcupado
from app.domain.errors_turnos import ConflictoDeTurno

Resultado = TypeVar("Resultado")


async def ejecutar_operacion(operacion: Awaitable[Resultado]) -> Resultado:
    """Traduce conflictos de dominio después de salir de la transacción."""
    try:
        return await operacion
    except HorarioOcupado:
        raise HTTPException(409, "horario ocupado") from None
    except ConflictoDeTurno:
        raise HTTPException(409, "El turno cambió durante la operación") from None
