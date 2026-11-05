from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.turno import Turno
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.domain.policies.acceso import autorizar


@pytest.mark.parametrize("asignados,permitido,codigo", [
    (frozenset(), False, 404), (frozenset({22}), True, None),
])
def test_c08_ficha_profesional_fuera_de_agenda_es_404(asignados, permitido, codigo):
    profesional = Principal(3, 1, RolUsuario.PROFESIONAL)
    ficha = SimpleNamespace(id=22, consultorio_id=1)
    decision = autorizar(profesional, Accion.PACIENTE_VER, ficha,
                         ContextoAcceso(ahora=datetime(2026, 11, 6, tzinfo=timezone.utc),
                                        turnos_del_profesional=asignados))
    assert decision.permitido is permitido
    assert decision.codigo_http == codigo


def _crear_turno(
    consultorio_id: int = 1,
    paciente_id: int = 10,
    profesional_id: int = 20,
    estado: EstadoTurno = EstadoTurno.CONFIRMADO,
    inicio: datetime | None = None,
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
        es_sobreturno=False,
    )


def test_autorizar_a2_consultorio_ajeno_siempre_404():
    user = Principal(usuario_id=1, consultorio_id=1, rol=RolUsuario.ADMINISTRADOR)
    turno_ajeno = _crear_turno(consultorio_id=2)

    decision = autorizar(user, Accion.TURNO_VER, recurso=turno_ajeno)
    assert decision.permitido is False
    assert decision.codigo_http == 404
    assert decision.motivo == "consultorio_ajeno"


def test_autorizar_rol_administrativo_siempre_denegado_403():
    fin = Principal(usuario_id=5, consultorio_id=1, rol=RolUsuario.ADMINISTRATIVO)
    turno = _crear_turno(consultorio_id=1)

    decision = autorizar(fin, Accion.TURNO_VER, recurso=turno)
    assert decision.permitido is False
    assert decision.codigo_http == 403


def test_autorizar_paciente_turno_ver_propio_y_ajeno():
    paciente = Principal(usuario_id=100, consultorio_id=1, rol=RolUsuario.PACIENTE)
    turno_propio = _crear_turno(paciente_id=10)
    turno_ajeno = _crear_turno(paciente_id=99)

    ctx_valido = ContextoAcceso(ahora=datetime.now(timezone.utc), ficha_vigente_id=10)
    ctx_sin_ficha = ContextoAcceso(ahora=datetime.now(timezone.utc), ficha_vigente_id=None)

    # Titular con ficha vigente
    d_ok = autorizar(paciente, Accion.TURNO_VER, recurso=turno_propio, contexto=ctx_valido)
    assert d_ok.permitido is True

    # Turno ajeno -> 404 (evitar revelar existencia)
    d_ajeno = autorizar(paciente, Accion.TURNO_VER, recurso=turno_ajeno, contexto=ctx_valido)
    assert d_ajeno.permitido is False
    assert d_ajeno.codigo_http == 404

    # Sin ficha vigente -> 404
    d_sin_ficha = autorizar(paciente, Accion.TURNO_VER, recurso=turno_propio, contexto=ctx_sin_ficha)
    assert d_sin_ficha.permitido is False
    assert d_sin_ficha.codigo_http == 404


def test_autorizar_profesional_turno_ver_agenda_propia_y_ajena():
    prof = Principal(usuario_id=5, consultorio_id=1, rol=RolUsuario.PROFESIONAL)
    turno_propio = _crear_turno(profesional_id=20)
    turno_ajeno = _crear_turno(profesional_id=99)

    ctx = ContextoAcceso(ahora=datetime.now(timezone.utc), profesional_vinculado_id=20)

    # Agenda propia
    d_ok = autorizar(prof, Accion.TURNO_VER, recurso=turno_propio, contexto=ctx)
    assert d_ok.permitido is True

    # Turno ajeno por identificador -> 404 (la agenda ajena conserva 403)
    d_ajeno = autorizar(prof, Accion.TURNO_VER, recurso=turno_ajeno, contexto=ctx)
    assert d_ajeno.permitido is False
    assert d_ajeno.codigo_http == 404


def test_autorizar_cancelar_paciente_dentro_y_fuera_de_ventana():
    paciente = Principal(usuario_id=100, consultorio_id=1, rol=RolUsuario.PACIENTE)
    inicio = datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc)
    turno = _crear_turno(paciente_id=10, inicio=inicio, estado=EstadoTurno.CONFIRMADO)

    # 30 horas antes -> permitido
    ctx_ok = ContextoAcceso(ahora=inicio - timedelta(hours=30), ficha_vigente_id=10)
    d_ok = autorizar(paciente, Accion.TURNO_CANCELAR, recurso=turno, contexto=ctx_ok)
    assert d_ok.permitido is True

    # 10 horas antes -> 403
    ctx_tarde = ContextoAcceso(ahora=inicio - timedelta(hours=10), ficha_vigente_id=10)
    d_tarde = autorizar(paciente, Accion.TURNO_CANCELAR, recurso=turno, contexto=ctx_tarde)
    assert d_tarde.permitido is False
    assert d_tarde.codigo_http == 403


def test_autorizar_triangulacion_acciones_diversas():
    admin = Principal(1, 1, RolUsuario.ADMINISTRADOR)
    recep = Principal(2, 1, RolUsuario.RECEPCION)
    prof = Principal(3, 1, RolUsuario.PROFESIONAL)
    pac = Principal(4, 1, RolUsuario.PACIENTE)

    # Usuario no autenticado
    d_anon = autorizar(None, Accion.TURNO_VER)
    assert d_anon.permitido is False
    assert d_anon.codigo_http == 401

    # Turno crear: paciente con y sin ficha
    assert autorizar(pac, Accion.TURNO_CREAR, contexto=ContextoAcceso(ahora=datetime.now(timezone.utc), ficha_vigente_id=10, correo_verificado=True)).permitido is True
    assert autorizar(pac, Accion.TURNO_CREAR, contexto=ContextoAcceso(ahora=datetime.now(timezone.utc), ficha_vigente_id=None)).permitido is False
    assert autorizar(prof, Accion.TURNO_CREAR).permitido is False

    # Turno corregir ausente
    turno_ausente = _crear_turno(estado=EstadoTurno.AUSENTE)
    turno_pendiente = _crear_turno(estado=EstadoTurno.PENDIENTE)
    assert autorizar(recep, Accion.TURNO_CORREGIR_AUSENTE, recurso=turno_ausente).permitido is True
    assert autorizar(recep, Accion.TURNO_CORREGIR_AUSENTE, recurso=turno_pendiente).permitido is False
    assert autorizar(prof, Accion.TURNO_CORREGIR_AUSENTE, recurso=turno_ausente).permitido is False

    # Configuración e indicadores
    assert autorizar(admin, Accion.CONFIGURACION_GESTIONAR).permitido is True
    assert autorizar(recep, Accion.CONFIGURACION_GESTIONAR).permitido is False
    assert autorizar(admin, Accion.INDICADOR_AUSENTISMO).permitido is True
    assert autorizar(recep, Accion.INDICADOR_AUSENTISMO).permitido is False
