from datetime import datetime, timedelta, timezone
import pytest

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.acceso import autorizar


def _crear_turno(
    consultorio_id: int = 1,
    paciente_id: int = 10,
    profesional_id: int = 20,
    estado: EstadoTurno = EstadoTurno.PENDIENTE,
    inicio: datetime | None = None,
    es_sobreturno: bool = False,
) -> Turno:
    if inicio is None:
        inicio = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    return Turno(
        id=1,
        consultorio_id=consultorio_id,
        paciente_id=paciente_id,
        profesional_id=profesional_id,
        box_id=1,
        prestacion_id=1,
        inicio=inicio,
        fin=inicio + timedelta(hours=1),
        estado=estado,
        es_sobreturno=es_sobreturno,
    )


@pytest.mark.parametrize("accion", list(Accion))
def test_rol_administrativo_es_denegado_en_todas_las_acciones(accion: Accion):
    fin = Principal(usuario_id=99, consultorio_id=1, rol=RolUsuario.ADMINISTRATIVO)
    turno = _crear_turno(consultorio_id=1)
    ctx = ContextoAcceso(ahora=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc), ficha_vigente_id=10, profesional_vinculado_id=20)

    decision = autorizar(fin, accion, recurso=turno, contexto=ctx)
    assert decision.permitido is False
    assert decision.codigo_http == 403


@pytest.mark.parametrize("rol", [
    RolUsuario.ADMINISTRADOR,
    RolUsuario.RECEPCION,
    RolUsuario.PROFESIONAL,
    RolUsuario.PACIENTE,
])
def test_a2_consultorio_ajeno_siempre_responde_404(rol: RolUsuario):
    user = Principal(usuario_id=10, consultorio_id=1, rol=rol)
    turno_ajeno = _crear_turno(consultorio_id=2)
    ctx = ContextoAcceso(ahora=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc), ficha_vigente_id=10, profesional_vinculado_id=20)

    decision = autorizar(user, Accion.TURNO_VER, recurso=turno_ajeno, contexto=ctx)
    assert decision.permitido is False
    assert decision.codigo_http == 404
    assert decision.motivo == "consultorio_ajeno"


@pytest.mark.parametrize(
    "accion,rol_esperado,espera_permitido",
    [
        (Accion.AGENDA_VER, RolUsuario.ADMINISTRADOR, True),
        (Accion.AGENDA_VER, RolUsuario.RECEPCION, True),
        (Accion.AGENDA_VER, RolUsuario.PACIENTE, False),
        (Accion.SOBRETURNO_AUTORIZAR, RolUsuario.ADMINISTRADOR, True),
        (Accion.SOBRETURNO_AUTORIZAR, RolUsuario.RECEPCION, True),
        (Accion.SOBRETURNO_AUTORIZAR, RolUsuario.PROFESIONAL, False),
        (Accion.SOBRETURNO_AUTORIZAR, RolUsuario.PACIENTE, False),
        (Accion.CONFIGURACION_GESTIONAR, RolUsuario.ADMINISTRADOR, True),
        (Accion.CONFIGURACION_GESTIONAR, RolUsuario.RECEPCION, False),
        (Accion.CONFIGURACION_GESTIONAR, RolUsuario.PROFESIONAL, False),
        (Accion.CONFIGURACION_GESTIONAR, RolUsuario.PACIENTE, False),
        (Accion.INDICADOR_AUSENTISMO, RolUsuario.ADMINISTRADOR, True),
        (Accion.INDICADOR_AUSENTISMO, RolUsuario.RECEPCION, False),
        (Accion.INDICADOR_AUSENTISMO, RolUsuario.PROFESIONAL, False),
        (Accion.INDICADOR_AUSENTISMO, RolUsuario.PACIENTE, False),
        (Accion.NOTIFICACION_GESTIONAR, RolUsuario.ADMINISTRADOR, True),
        (Accion.NOTIFICACION_GESTIONAR, RolUsuario.RECEPCION, True),
        (Accion.NOTIFICACION_GESTIONAR, RolUsuario.PROFESIONAL, False),
        (Accion.NOTIFICACION_GESTIONAR, RolUsuario.PACIENTE, False),
    ],
)
def test_matriz_rbac_acciones_directas(accion: Accion, rol_esperado: RolUsuario, espera_permitido: bool):
    user = Principal(usuario_id=1, consultorio_id=1, rol=rol_esperado)
    decision = autorizar(user, accion)
    assert decision.permitido is espera_permitido
    if not espera_permitido:
        assert decision.codigo_http == 403


def test_motivos_de_rechazo_no_contienen_datos_personales():
    paciente = Principal(usuario_id=100, consultorio_id=1, rol=RolUsuario.PACIENTE)
    turno = _crear_turno(paciente_id=10)
    ctx_sin_ficha = ContextoAcceso(ahora=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc), ficha_vigente_id=None)

    decision = autorizar(paciente, Accion.TURNO_VER, recurso=turno, contexto=ctx_sin_ficha)
    assert decision.permitido is False
    # Verificamos que el motivo no divulgue DNI, nombres ni números sensibles
    motivo = decision.motivo or ""
    assert "dni" not in motivo.lower()
    assert "nombre" not in motivo.lower()
    assert "@" not in motivo
