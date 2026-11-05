from datetime import datetime, timedelta, timezone
import pytest

from app.domain.policies.decision_hitos import decidir_sin_confirmar

AHORA = datetime(2026,11,6,12,tzinfo=timezone.utc)


def test_rn60_libera_pendiente_con_solicitud_enviada_al_hito():
    assert decidir_sin_confirmar(estado='pendiente', inicio=AHORA+timedelta(hours=12),
        ahora=AHORA, marca=None, modo='automatico', solicitud_enviada=True,
        horas_liberacion=12) == 'liberar'


@pytest.mark.parametrize('modo,enviada,estado,marca,horas,limite,esperado', [
    ('manual', True, 'pendiente', None, 12, 12, 'marcar_sin_confirmar'),
    ('automatico', False, 'pendiente', None, 12, 12, 'marcar_sin_confirmar'),
    ('automatico', True, 'pendiente', AHORA, 12, 12, None),
    ('automatico', True, 'confirmado', None, 12, 12, None),
    ('automatico', True, 'pendiente', None, 12+1/3600, 12, None),
    ('automatico', True, 'pendiente', None, 0, 12, None),
    ('automatico', True, 'pendiente', None, -1, 12, None),
    ('automatico', True, 'pendiente', None, 6, 6, 'liberar'),
    ('automatico', True, 'pendiente', None, 6+1/3600, 6, None),
])
def test_rn60_triangula_guarda_temporal_marca_y_modo(modo,enviada,estado,marca,horas,limite,esperado):
    assert decidir_sin_confirmar(estado=estado,inicio=AHORA+timedelta(hours=horas),
        ahora=AHORA,marca=marca,modo=modo,solicitud_enviada=enviada,horas_liberacion=limite)==esperado
