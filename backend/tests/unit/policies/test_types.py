from datetime import datetime, timezone
import pytest

from app.domain.value_objects.accion import Accion
from app.domain.value_objects.decision import Decision
from app.domain.value_objects.intervalo import Intervalo
from app.domain.value_objects.contexto_acceso import ContextoAcceso


def test_accion_enum_contains_all_canonical_actions():
    acciones_esperadas = {
        "agenda.ver",
        "turno.ver", "turno.sin_confirmar_ver",
        "turno.crear",
        "turno.reprogramar",
        "turno.cancelar",
        "turno.confirmar",
        "turno.atendido",
        "turno.ausente",
        "turno.corregir_ausente",
        "turno.liberar",
        "sobreturno.autorizar",
        "sobreturno.responder",
        "paciente.ver",
        "paciente.editar",
        "paciente.vincular",
        "paciente.desvincular",
        "paciente.reactivar",
        "configuracion.gestionar",
        "notificacion.gestionar",
        "indicador.ausentismo",
    }
    assert {a.value for a in Accion} == acciones_esperadas


def test_decision_structure_immutable():
    d_ok = Decision(permitido=True)
    assert d_ok.permitido is True
    assert d_ok.motivo is None
    assert d_ok.codigo_http is None

    d_err = Decision(permitido=False, motivo="no_autorizado", codigo_http=403)
    assert d_err.permitido is False
    assert d_err.motivo == "no_autorizado"
    assert d_err.codigo_http == 403

    with pytest.raises(Exception):
        d_ok.permitido = False  # frozen dataclass


def test_intervalo_creation_and_validation():
    t1 = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)

    intervalo = Intervalo(inicio=t1, fin=t2)
    assert intervalo.inicio == t1
    assert intervalo.fin == t2
    assert intervalo.duracion_minutos() == 60

    # Rechaza fin anterior o igual a inicio
    with pytest.raises(ValueError, match="inicio debe ser menor que fin"):
        Intervalo(inicio=t2, fin=t1)

    # Rechaza sin zona horaria
    t_naive1 = datetime(2026, 10, 31, 10, 0)
    t_naive2 = datetime(2026, 10, 31, 11, 0)
    with pytest.raises(ValueError, match="zona horaria"):
        Intervalo(inicio=t_naive1, fin=t_naive2)


def test_intervalo_triangulation_solapamiento_y_contencion():
    t1 = datetime(2026, 10, 31, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 10, 31, 11, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)

    i1 = Intervalo(t1, t2)
    i2 = Intervalo(t2, t3)  # contiguo, no solapa
    i3 = Intervalo(datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc), t3)  # solapa con i1 e i2

    assert i1.solapa_con(i2) is False
    assert i2.solapa_con(i1) is False
    assert i1.solapa_con(i3) is True
    assert i3.solapa_con(i1) is True

    # Comprobación de contención en bordes exactos [inicio, fin)
    assert i1.contiene(t1) is True
    assert i1.contiene(datetime(2026, 10, 31, 10, 30, tzinfo=timezone.utc)) is True
    assert i1.contiene(t2) is False


def test_contexto_acceso_structure_and_defaults():
    ahora = datetime(2026, 10, 31, 12, 0, tzinfo=timezone.utc)
    ctx = ContextoAcceso(ahora=ahora)

    assert ctx.ahora == ahora
    assert ctx.ficha_vigente_id is None
    assert ctx.horas_limite_cancelacion == 24
    assert ctx.consultorio_modo_manual is False
    assert ctx.turno_sin_confirmar is False
    assert ctx.turnos_del_profesional == frozenset()

    with pytest.raises(Exception):
        ctx.horas_limite_cancelacion = 48  # frozen

    # Triangulación: rechaza datetime naive
    with pytest.raises(ValueError, match="zona horaria"):
        ContextoAcceso(ahora=datetime(2026, 10, 31, 12, 0))
