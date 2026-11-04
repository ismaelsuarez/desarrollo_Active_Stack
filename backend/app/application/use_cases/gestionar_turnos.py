from datetime import datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from app.application.errors_turnos import RechazoDeTurno
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo
from app.application.ports.hitos import PlanificadorDeHitos, PlanificadorSinEfectos
from app.domain.entities.auth import Principal
from app.domain.entities.historial import HechoDeTurno
from app.domain.entities.turno import NuevoTurno, Turno
from app.domain.errors import HorarioOcupado
from app.domain.ports.reloj import Reloj
from app.domain.policies.reserva import duracion_turno, estado_inicial, validar_intervalo
from app.domain.policies.acceso import autorizar
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso


class GestionTurnos:
    """Operaciones de turnos con una transacción para reserva e historia."""

    def __init__(self, unidades: FabricaDeUnidadesDeTrabajo, reloj: Reloj,
                 hitos: PlanificadorDeHitos | None = None) -> None:
        self._unidades = unidades
        self._reloj = reloj
        self._hitos = hitos if hitos is not None else PlanificadorSinEfectos()

    async def crear(self, principal: Principal, paciente_id: int, profesional_id: int,
                    prestacion_id: int, inicio: datetime, duracion_min: int | None = None,
                    confirmar: bool = False) -> Turno:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            profesional = await unidad.profesionales.obtener(principal.consultorio_id, profesional_id)
            prestacion = await unidad.prestaciones.obtener(principal.consultorio_id, prestacion_id)
            config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            paciente = await unidad.agenda.obtener_paciente(principal.consultorio_id, paciente_id)
            if any(recurso is None for recurso in (profesional, prestacion, config, paciente)):
                raise RechazoDeTurno(404, "Recurso no encontrado")
            decision = autorizar(principal, Accion.TURNO_CREAR, config, ContextoAcceso(ahora=ahora))
            if not decision.permitido:
                logging.getLogger("tpi.acceso").info("Acceso denegado", extra={
                    "usuario_id": principal.usuario_id, "accion": Accion.TURNO_CREAR.value,
                    "motivo": decision.motivo,
                })
                raise RechazoDeTurno(decision.codigo_http, decision.motivo)
            try:
                duracion = duracion_turno(prestacion.duracion_min, duracion_min, config.minutos_granularidad)
                fin = inicio + timedelta(minutes=duracion)
            except ValueError as error:
                raise RechazoDeTurno(422, str(error)) from None
            except OverflowError:
                raise RechazoDeTurno(422, "El intervalo no puede representarse") from None
            bloques = await unidad.agenda.bloques(principal.consultorio_id, profesional_id,
                                                 inicio.astimezone(ZoneInfo(config.zona_horaria)).isoweekday())
            bloqueos = await unidad.agenda.bloqueos(principal.consultorio_id, profesional_id)
            try:
                validar_intervalo(inicio, fin, bloques, bloqueos,
                                  config.minutos_granularidad, config.zona_horaria)
            except ValueError as error:
                raise RechazoDeTurno(422, str(error)) from None
            if await unidad.turnos.hay_solapamiento(principal.consultorio_id, profesional_id, inicio, fin):
                raise HorarioOcupado()
            estado = estado_inicial(inicio, ahora, config.horas_confirmacion, confirmar)
            turno = await unidad.turnos.guardar(NuevoTurno(
                consultorio_id=principal.consultorio_id, paciente_id=paciente_id,
                profesional_id=profesional.id, box_id=profesional.box_id,
                prestacion_id=prestacion.id, inicio=inicio,
                fin=fin,
                estado=estado, origen="recepcion", creado_por_id=principal.usuario_id,
                creado_en=ahora, actualizado_en=ahora,
                confirmado_en=ahora if estado.value == "confirmado" else None,
            ))
            await unidad.historial.agregar(HechoDeTurno(
                consultorio_id=principal.consultorio_id, turno_id=turno.id,
                usuario_id=principal.usuario_id, accion="crear", estado_anterior=None,
                estado_nuevo=estado, detalle={"motivo": "confirmacion_manual" if confirmar else "RN-29" if estado.value == "confirmado" else "RN-23"},
                ocurrido_en=ahora,
            ))
            await self._hitos.planificar(unidad, turno, "crear", ahora)
        return turno

    async def reprogramar(self, principal: Principal, turno_id: int, inicio: datetime,
                          duracion_min: int | None = None) -> Turno:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            anterior = await unidad.turnos.obtener(principal.consultorio_id, turno_id)
            config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            if anterior is None or config is None:
                raise RechazoDeTurno(404, "Recurso no encontrado")
            decision = autorizar(principal, Accion.TURNO_REPROGRAMAR, anterior, ContextoAcceso(ahora=ahora))
            if not decision.permitido:
                logging.getLogger("tpi.acceso").info("Acceso denegado", extra={
                    "usuario_id": principal.usuario_id, "accion": Accion.TURNO_REPROGRAMAR.value,
                    "motivo": decision.motivo,
                })
                raise RechazoDeTurno(decision.codigo_http, decision.motivo)
            try:
                duracion = anterior.fin - anterior.inicio
                if duracion_min is not None:
                    duracion = timedelta(minutes=duracion_turno(1, duracion_min, config.minutos_granularidad))
                fin = inicio + duracion
                bloques = await unidad.agenda.bloques(principal.consultorio_id, anterior.profesional_id,
                                                     inicio.astimezone(ZoneInfo(config.zona_horaria)).isoweekday())
                bloqueos = await unidad.agenda.bloqueos(principal.consultorio_id, anterior.profesional_id)
                validar_intervalo(inicio, fin, bloques, bloqueos,
                                  config.minutos_granularidad, config.zona_horaria)
            except ValueError as error:
                raise RechazoDeTurno(422, str(error)) from None
            except OverflowError:
                raise RechazoDeTurno(422, "El intervalo no puede representarse") from None
            if await unidad.turnos.hay_solapamiento(principal.consultorio_id, anterior.profesional_id,
                                                   inicio, fin, excluir_id=anterior.id):
                raise HorarioOcupado()
            estado = estado_inicial(inicio, ahora, config.horas_confirmacion)
            turno = await unidad.turnos.actualizar(anterior, {
                "inicio": inicio, "fin": fin, "estado": estado,
                "ciclo_confirmacion": anterior.ciclo_confirmacion + 1,
                "marcado_sin_confirmar_en": None, "confirmacion_solicitada_en": None,
                "recordatorio_enviado_en": None,
                "confirmado_en": ahora if estado.value == "confirmado" else None,
                "reprogramado_de_inicio": anterior.inicio, "actualizado_en": ahora,
            })
            await unidad.historial.agregar(HechoDeTurno(
                consultorio_id=principal.consultorio_id, turno_id=turno.id,
                usuario_id=principal.usuario_id, accion="reprogramar", estado_anterior=anterior.estado,
                estado_nuevo=estado, detalle={"motivo": "RN-29" if estado.value == "confirmado" else "RN-32",
                                            "inicio_anterior": anterior.inicio.isoformat()},
                ocurrido_en=ahora,
            ))
            await self._hitos.planificar(unidad, turno, "reprogramar", ahora)
        return turno
