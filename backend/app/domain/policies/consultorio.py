from typing import Any
from app.domain.entities.auth import Principal


def mismo_consultorio(usuario: Principal, recurso: Any) -> bool:
    """A2. Verifica si el usuario y el recurso pertenecen al mismo consultorio."""
    if usuario is None or recurso is None:
        return False

    consultorio_recurso = getattr(recurso, "consultorio_id", None)
    if consultorio_recurso is None:
        return False

    return usuario.consultorio_id == consultorio_recurso
