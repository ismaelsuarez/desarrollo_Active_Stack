from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno


def puede_autorizar_sobreturno(usuario: Principal | None) -> bool:
    """RBAC. Solo recepcion o administrador pueden autorizar un sobreturno (RN-39)."""
    if usuario is None:
        return False
    return usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION)


def puede_responder_sobreturno(
    usuario: Principal | None,
    turno: Turno | None,
    profesional_id: int | None,
) -> bool:
    """A1. El profesional (o administrador con agenda) solo responde sobreturnos en su propia agenda (DD-24)."""
    if usuario is None or turno is None or profesional_id is None:
        return False

    if not turno.es_sobreturno:
        return False

    if usuario.rol not in (RolUsuario.PROFESIONAL, RolUsuario.ADMINISTRADOR):
        return False

    return turno.profesional_id == profesional_id


def sobreturno_cumple_condiciones(
    turno: Turno | None,
    profesional_avisado: bool,
    autorizante_id: int | None,
) -> bool:
    """RN-43. Exige que el turno sea sobreturno, profesional avisado y autorizante registrado."""
    if turno is None or not turno.es_sobreturno:
        return False

    if not profesional_avisado:
        return False

    if autorizante_id is None:
        return False

    return True
