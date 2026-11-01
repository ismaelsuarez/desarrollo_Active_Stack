from app.domain.entities.auth import Principal, RolUsuario
from app.domain.policies.paciente import (
    puede_ver_paciente,
    puede_editar_paciente,
    puede_vincular_paciente,
    puede_desvincular_paciente,
    puede_reactivar_paciente,
)
from app.domain.policies.indicadores import puede_ver_ausentismo


def test_puede_ver_paciente_por_rol():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)
    fin = Principal(5, 1, RolUsuario.ADMINISTRATIVO)

    paciente_id = 10
    turnos_del_prof = frozenset({10, 11})

    # Nulos
    assert puede_ver_paciente(None, paciente_id, 4, turnos_del_prof) is False
    assert puede_editar_paciente(None, paciente_id, 4) is False

    # Administrador y Recepción ven cualquier paciente
    assert puede_ver_paciente(admin, paciente_id, ficha_usuario_id=99, turnos_del_profesional=frozenset()) is True
    assert puede_ver_paciente(recep, paciente_id, ficha_usuario_id=99, turnos_del_profesional=frozenset()) is True

    # Profesional solo ve pacientes con turnos en su agenda
    assert puede_ver_paciente(prof, paciente_id, ficha_usuario_id=99, turnos_del_profesional=turnos_del_prof) is True
    assert puede_ver_paciente(prof, 999, ficha_usuario_id=99, turnos_del_profesional=turnos_del_prof) is False

    # Paciente solo ve su propia ficha (ficha_usuario_id coincide con pac.usuario_id)
    assert puede_ver_paciente(pac, paciente_id, ficha_usuario_id=4, turnos_del_profesional=frozenset()) is True
    assert puede_ver_paciente(pac, paciente_id, ficha_usuario_id=88, turnos_del_profesional=frozenset()) is False
    assert puede_ver_paciente(pac, paciente_id, ficha_usuario_id=None, turnos_del_profesional=frozenset()) is False

    # Administrativo no ve pacientes
    assert puede_ver_paciente(fin, paciente_id, ficha_usuario_id=5, turnos_del_profesional=turnos_del_prof) is False


def test_puede_editar_paciente_por_rol():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)

    assert puede_editar_paciente(admin, paciente_id=10, ficha_usuario_id=99) is True
    assert puede_editar_paciente(recep, paciente_id=10, ficha_usuario_id=99) is True
    assert puede_editar_paciente(prof, paciente_id=10, ficha_usuario_id=99) is False

    # Paciente edita solo ficha propia
    assert puede_editar_paciente(pac, paciente_id=10, ficha_usuario_id=4) is True
    assert puede_editar_paciente(pac, paciente_id=10, ficha_usuario_id=88) is False


def test_operaciones_gestion_ficha_paciente():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)

    for fn in (puede_vincular_paciente, puede_desvincular_paciente, puede_reactivar_paciente):
        assert fn(admin) is True
        assert fn(recep) is True
        assert fn(prof) is False
        assert fn(pac) is False
        assert fn(None) is False


def test_puede_ver_ausentismo():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)
    adm_fin = Principal(5, 1, RolUsuario.ADMINISTRATIVO)

    assert puede_ver_ausentismo(admin) is True
    assert puede_ver_ausentismo(recep) is False
    assert puede_ver_ausentismo(prof) is False
    assert puede_ver_ausentismo(pac) is False
    assert puede_ver_ausentismo(adm_fin) is False
    assert puede_ver_ausentismo(None) is False
