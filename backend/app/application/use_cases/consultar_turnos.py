"""Lecturas operativas de turno sin exponer la ficha clínica ni la cuenta."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import NoReturn
from zoneinfo import ZoneInfo

from app.application.errors_turnos import RechazoDeTurno
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo, UnidadDeTrabajo
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.historial import HechoDeTurno
from app.domain.entities.turno import Turno
from app.domain.policies.acceso import autorizar
from app.domain.ports.reloj import Reloj
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.domain.value_objects.estado_turno import EstadoTurno


@dataclass(frozen=True, slots=True)
class TurnoConsultado:
    id: int
    paciente_id: int
    paciente_nombre: str
    paciente_apellido: str
    profesional_id: int
    box_id: int
    prestacion_id: int
    prestacion_nombre: str
    inicio: datetime
    fin: datetime
    estado: EstadoTurno
    es_sobreturno: bool
    marcado_sin_confirmar_en: datetime | None
    acciones_permitidas: tuple[str, ...] | None = None


class ConsultarTurnos:
    def __init__(self, unidades: FabricaDeUnidadesDeTrabajo, reloj: Reloj) -> None:
        self._unidades = unidades
        self._reloj = reloj

    @staticmethod
    def _rechazar(principal: Principal, accion: Accion, codigo: int, motivo: str) -> NoReturn:
        logging.getLogger("tpi.acceso").info("Acceso denegado", extra={
            "usuario_id": principal.usuario_id, "accion": accion.value, "motivo": motivo,
        })
        raise RechazoDeTurno(codigo, motivo)

    def _autorizar(self, principal: Principal, accion: Accion, recurso: object,
                   contexto: ContextoAcceso) -> None:
        decision = autorizar(principal, accion, recurso, contexto)
        if not decision.permitido:
            self._rechazar(principal, accion, decision.codigo_http, decision.motivo)

    async def _turno_autorizado(self, unidad: UnidadDeTrabajo, principal: Principal,
                                turno_id: int, ahora: datetime) -> tuple[Turno, ContextoAcceso]:
        turno = await unidad.turnos.obtener(principal.consultorio_id, turno_id)
        if turno is None:
            self._rechazar(principal, Accion.TURNO_VER, 404, "Turno no encontrado")
        profesional_id = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                 incluir_inactivos=True)
        ficha = (await unidad.pacientes.de_usuario(principal.consultorio_id, principal.usuario_id)
                 if principal.rol == RolUsuario.PACIENTE else None)
        config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
        contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=profesional_id,
                                 ficha_vigente_id=ficha.id if ficha else None,
                                 horas_limite_cancelacion=config.horas_limite_paciente if config else 24)
        self._autorizar(principal, Accion.TURNO_VER, turno, contexto)
        return turno, contexto

    @staticmethod
    async def _presentar(unidad: UnidadDeTrabajo, turno: Turno,
                         principal: Principal | None = None,
                         contexto: ContextoAcceso | None = None) -> TurnoConsultado:
        paciente = await unidad.agenda.obtener_paciente(turno.consultorio_id, turno.paciente_id)
        prestacion = await unidad.prestaciones.obtener(turno.consultorio_id, turno.prestacion_id,
                                                       incluir_inactivos=True)
        if paciente is None or prestacion is None:
            raise RechazoDeTurno(404, "Recurso no encontrado")
        return TurnoConsultado(
            id=turno.id, paciente_id=paciente.id, paciente_nombre=paciente.nombre,
            paciente_apellido=paciente.apellido, profesional_id=turno.profesional_id,
            box_id=turno.box_id, prestacion_id=prestacion.id, prestacion_nombre=prestacion.nombre,
            inicio=turno.inicio, fin=turno.fin, estado=turno.estado,
            es_sobreturno=turno.es_sobreturno, marcado_sin_confirmar_en=turno.marcado_sin_confirmar_en,
            acciones_permitidas=tuple(
                nombre for nombre, accion in (
                    ("confirmar", Accion.TURNO_CONFIRMAR), ("cancelar", Accion.TURNO_CANCELAR),
                    ("reprogramar", Accion.TURNO_REPROGRAMAR),
                ) if autorizar(principal, accion, turno, contexto).permitido
            ) if principal is not None and principal.rol == RolUsuario.PACIENTE else None,
        )

    async def detalle(self, principal: Principal, turno_id: int) -> TurnoConsultado:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            turno, contexto = await self._turno_autorizado(unidad, principal, turno_id, ahora)
            return await self._presentar(unidad, turno, principal, contexto)

    async def listar(self, principal: Principal) -> list[TurnoConsultado]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            if principal.rol == RolUsuario.PACIENTE:
                ficha = await unidad.pacientes.de_usuario(principal.consultorio_id, principal.usuario_id)
                if ficha is None:
                    return []
                turnos = await unidad.turnos.listar(principal.consultorio_id, paciente_id=ficha.id)
                config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
                contexto = ContextoAcceso(ahora=ahora, ficha_vigente_id=ficha.id,
                    horas_limite_cancelacion=config.horas_limite_paciente if config else 24)
                for turno in turnos:
                    self._autorizar(principal, Accion.TURNO_VER, turno, contexto)
                return [await self._presentar(unidad, turno, principal, contexto) for turno in turnos]
            profesional_id = None
            recurso = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                         incluir_inactivos=True)
                recurso = await unidad.profesionales.obtener(principal.consultorio_id, profesional_id,
                                                             incluir_inactivos=True)
            if recurso is None:
                self._rechazar(principal, Accion.AGENDA_VER, 404, "Agenda no encontrada")
            contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=profesional_id)
            self._autorizar(principal, Accion.AGENDA_VER, recurso, contexto)
            turnos = await unidad.turnos.listar(principal.consultorio_id, profesional_id=profesional_id)
            return [await self._presentar(unidad, turno) for turno in turnos]

    async def historial(self, principal: Principal, turno_id: int) -> list[HechoDeTurno]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            turno, _ = await self._turno_autorizado(unidad, principal, turno_id, ahora)
            return await unidad.historial.listar(principal.consultorio_id, turno.id)

    async def agenda(self, principal: Principal, profesional_id: int, fecha: date) -> list[TurnoConsultado]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            profesional = await unidad.profesionales.obtener(principal.consultorio_id, profesional_id,
                                                             incluir_inactivos=True)
            config = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            if profesional is None or config is None:
                self._rechazar(principal, Accion.AGENDA_VER, 404, "Agenda no encontrada")
            vinculado = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                incluir_inactivos=True)
            contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=vinculado)
            self._autorizar(principal, Accion.AGENDA_VER, profesional, contexto)
            zona = ZoneInfo(config.zona_horaria)
            desde = datetime.combine(fecha, time.min, tzinfo=zona)
            hasta = datetime.combine(fecha + timedelta(days=1), time.min, tzinfo=zona)
            turnos = await unidad.turnos.listar(principal.consultorio_id,
                profesional_id=profesional_id, desde=desde, hasta=hasta)
            return [await self._presentar(unidad, turno) for turno in turnos]

    async def de_paciente(self, principal: Principal, paciente_id: int) -> list[TurnoConsultado]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            profesional_id = None
            pacientes_permitidos = frozenset()
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                         incluir_inactivos=True)
                if profesional_id is not None:
                    pacientes_permitidos = await unidad.agenda.pacientes_de_profesional(principal.consultorio_id, profesional_id)
                # Un identificador de ficha fuera de la agenda se comporta como
                # inexistente: no se carga ni se revela su información (KB 11).
                if paciente_id not in pacientes_permitidos:
                    self._rechazar(principal, Accion.PACIENTE_VER, 404, "Ficha no encontrada")
            paciente = await unidad.agenda.obtener_paciente(principal.consultorio_id, paciente_id)
            if paciente is None:
                self._rechazar(principal, Accion.PACIENTE_VER, 404, "Ficha no encontrada")
            contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=profesional_id,
                turnos_del_profesional=pacientes_permitidos)
            self._autorizar(principal, Accion.PACIENTE_VER, paciente, contexto)
            turnos = await unidad.turnos.listar(principal.consultorio_id,
                profesional_id=profesional_id, paciente_id=paciente_id)
            return [await self._presentar(unidad, turno) for turno in turnos]
