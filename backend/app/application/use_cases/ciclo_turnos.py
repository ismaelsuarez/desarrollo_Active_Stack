import logging

from app.application.errors_turnos import RechazoDeTurno
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.historial import HechoDeTurno
from app.domain.entities.turno import Turno
from app.domain.ports.reloj import Reloj
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.domain.value_objects.estado_turno import EstadoTurno


class CicloTurnos:
    """Transiciones autorizadas con turno e historial en una sola transacción."""

    def __init__(self, unidades: FabricaDeUnidadesDeTrabajo, reloj: Reloj) -> None:
        self._unidades = unidades
        self._reloj = reloj

    async def ejecutar(self, principal: Principal, turno_id: int, accion: str,
                       motivo: str | None = None) -> Turno:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            turno = await unidad.turnos.obtener(principal.consultorio_id, turno_id)
            config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            if turno is None or config is None:
                raise RechazoDeTurno(404, "Turno no encontrado")
            ficha = None
            if principal.rol == RolUsuario.PACIENTE:
                ficha = await unidad.cuentas.ficha_de_usuario(principal.consultorio_id, principal.usuario_id)
                cuenta = await unidad.cuentas.usuario_por_id(principal.consultorio_id, principal.usuario_id)
                if cuenta is None:
                    ficha = None
            contexto = ContextoAcceso(
                ahora=ahora,
                ficha_vigente_id=ficha.id if ficha else None,
                horas_limite_cancelacion=config.horas_limite_paciente,
                profesional_vinculado_id=await unidad.agenda.profesional_vinculado(
                    principal.consultorio_id, principal.usuario_id),
                consultorio_modo_manual=config.modo_liberacion == "manual",
                turno_sin_confirmar=turno.marcado_sin_confirmar_en is not None,
            )
            corregir = accion == "atendido" and turno.estado == EstadoTurno.AUSENTE
            accion_politica = Accion.TURNO_CORREGIR_AUSENTE if corregir else Accion(f"turno.{accion}")
            decision = autorizar(principal, accion_politica, turno, contexto)
            if not decision.permitido:
                logging.getLogger("tpi.acceso").info("Acceso denegado", extra={
                    "usuario_id": principal.usuario_id, "accion": accion_politica.value,
                    "motivo": decision.motivo,
                })
                motivo_rechazo = decision.motivo
                if decision.motivo == "fuera_de_ventana_paciente":
                    telefono = config.telefono or "teléfono no configurado"
                    motivo_rechazo = (
                        f"fuera_de_ventana_paciente. Comunicate con el consultorio: {telefono}"
                    )
                raise RechazoDeTurno(decision.codigo_http, motivo_rechazo)
            cambios = {"actualizado_en": ahora}
            if accion == "cancelar":
                cambios.update(estado=EstadoTurno.CANCELADO, cancelado_en=ahora,
                               cancelado_por_id=principal.usuario_id, motivo_cancelacion=motivo)
            elif accion == "liberar":
                cambios.update(estado=EstadoTurno.LIBERADO, liberado_en=ahora)
            elif accion == "ausente":
                cambios.update(estado=EstadoTurno.AUSENTE)
            elif accion == "atendido":
                cambios.update(estado=EstadoTurno.ATENDIDO)
            else:
                cambios.update(estado=EstadoTurno.CONFIRMADO, confirmado_en=ahora)
            actualizado = await unidad.turnos.actualizar(turno, cambios)
            await unidad.historial.agregar(HechoDeTurno(
                consultorio_id=principal.consultorio_id, turno_id=turno.id,
                usuario_id=principal.usuario_id, accion="corregir" if corregir else accion,
                estado_anterior=turno.estado, estado_nuevo=actualizado.estado,
                detalle={"motivo": motivo} if motivo is not None else None, ocurrido_en=ahora,
            ))
        return actualizado
