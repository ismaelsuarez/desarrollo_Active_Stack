from app.application.errors_pacientes import RechazoPaciente, conflicto_paciente
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso


class ReactivarPaciente:
    def __init__(self, unidades, reloj):
        self._unidades = unidades
        self._reloj = reloj

    async def ejecutar(self, principal, paciente_id):
        decision = autorizar(principal, Accion.PACIENTE_REACTIVAR,
                             contexto=ContextoAcceso(ahora=self._reloj.ahora()))
        if not decision.permitido:
            raise RechazoPaciente(decision.codigo_http, decision.motivo)
        try:
            async with self._unidades() as unidad:
                ficha = await unidad.pacientes.obtener(principal.consultorio_id, paciente_id, bloquear=True)
                if ficha is None:
                    raise RechazoPaciente(404, "Ficha no encontrada")
                if not await unidad.pacientes.reactivar(principal.consultorio_id, paciente_id, self._reloj.ahora()):
                    raise RechazoPaciente(409, "La ficha ya está activa o cambió")
        except Exception as error:
            if conflicto_paciente(error):
                raise RechazoPaciente(409, "La ficha cambió") from None
            raise
