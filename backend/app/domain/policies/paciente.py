from app.domain.entities.auth import Principal, RolUsuario


def puede_ver_paciente(
    usuario: Principal | None,
    paciente_id: int,
    ficha_usuario_id: int | None,
    turnos_del_profesional: frozenset[int],
) -> bool:
    """A1. Administrador y Recepción ven todo el consultorio; profesional ve pacientes con turnos en su agenda; paciente solo ve su ficha."""
    if usuario is None:
        return False

    if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
        return True

    if usuario.rol == RolUsuario.PROFESIONAL:
        return paciente_id in turnos_del_profesional

    if usuario.rol == RolUsuario.PACIENTE:
        return ficha_usuario_id is not None and ficha_usuario_id == usuario.usuario_id

    return False


def puede_editar_paciente(
    usuario: Principal | None,
    paciente_id: int,
    ficha_usuario_id: int | None,
) -> bool:
    """A1. Administrador y Recepción editan todo el consultorio; paciente solo su propia ficha (RN-47)."""
    if usuario is None:
        return False

    if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
        return True

    if usuario.rol == RolUsuario.PACIENTE:
        return ficha_usuario_id is not None and ficha_usuario_id == usuario.usuario_id

    return False


def puede_vincular_paciente(usuario: Principal | None) -> bool:
    """RBAC. Solo recepcion o administrador pueden vincular o rechazar solicitudes de cuenta."""
    if usuario is None:
        return False
    return usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION)


def puede_desvincular_paciente(usuario: Principal | None) -> bool:
    """RBAC. Solo recepcion o administrador pueden desvincular una cuenta (RN-63)."""
    if usuario is None:
        return False
    return usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION)


def puede_reactivar_paciente(usuario: Principal | None) -> bool:
    """RBAC. Solo recepcion o administrador pueden reactivar una ficha."""
    if usuario is None:
        return False
    return usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION)
