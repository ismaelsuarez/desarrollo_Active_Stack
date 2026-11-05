from datetime import datetime, timezone

import pytest

from app.domain.entities.auth import Principal, RolUsuario
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso


def test_booking_without_verification_context_denies_by_default():
    contexto = ContextoAcceso(ahora=datetime(2026,11,1,tzinfo=timezone.utc), ficha_vigente_id=7)
    decision = autorizar(Principal(1,1,RolUsuario.PACIENTE),Accion.TURNO_CREAR,contexto=contexto)
    assert not decision.permitido and decision.codigo_http==403


@pytest.mark.parametrize("verificado,permitido",[(False,False),(True,True)])
def test_booking_uses_explicit_current_verification(verificado,permitido):
    contexto = ContextoAcceso(ahora=datetime(2026,11,1,tzinfo=timezone.utc), ficha_vigente_id=7,correo_verificado=verificado)
    assert autorizar(Principal(1,1,RolUsuario.PACIENTE),Accion.TURNO_CREAR,contexto=contexto).permitido is permitido
