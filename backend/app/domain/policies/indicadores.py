from app.domain.entities.auth import Principal, RolUsuario


def puede_ver_ausentismo(usuario: Principal | None) -> bool:
    """RBAC. Solo administrador puede visualizar métricas e indicadores de ausentismo."""
    if usuario is None:
        return False
    return usuario.rol == RolUsuario.ADMINISTRADOR
