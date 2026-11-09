"""Lecturas operativas de turno sin exponer la ficha clínica ni la cuenta."""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import logging
from typing import NoReturn
from zoneinfo import ZoneInfo

from app.application.errors_turnos import RechazoDeTurno
from app.application.dto.agenda import FichaAgenda
from app.application.ports.unidad_de_trabajo import FabricaDeUnidadesDeTrabajo, UnidadDeTrabajo
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.entities.historial import HechoDeTurno
from app.domain.entities.turno import Turno
from app.domain.entities.prestacion import Prestacion
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
    autorizacion_sobreturno: object | None = None


@dataclass(frozen=True, slots=True)
class DatosPresentacion:
    pacientes: dict[int, FichaAgenda]
    prestaciones: dict[int, Prestacion]
    autorizaciones: dict[int, object]
    profesional_activo: int | None


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
                         contexto: ContextoAcceso | None = None,
                         datos: DatosPresentacion | None = None) -> TurnoConsultado:
        paciente = (datos.pacientes.get(turno.paciente_id) if datos is not None
                    else await unidad.agenda.obtener_paciente(turno.consultorio_id, turno.paciente_id))
        prestacion = (datos.prestaciones.get(turno.prestacion_id) if datos is not None
                      else await unidad.prestaciones.obtener(turno.consultorio_id, turno.prestacion_id,
                                                              incluir_inactivos=True))
        if paciente is None or prestacion is None:
            raise RechazoDeTurno(404, "Recurso no encontrado")
        if datos is not None:
            autorizacion = datos.autorizaciones.get(turno.id)
            profesional_activo = datos.profesional_activo
        else:
            autorizacion = (await unidad.sobreturnos.obtener(turno.consultorio_id, turno.id)
                            if turno.es_sobreturno and principal is not None and principal.rol != RolUsuario.PACIENTE else None)
            profesional_activo = (await unidad.agenda.profesional_vinculado(turno.consultorio_id, principal.usuario_id)
                                  if principal is not None and
                                  (autorizacion is not None or principal.rol == RolUsuario.PROFESIONAL) else None)
        candidatas = [
            ("confirmar", Accion.TURNO_CONFIRMAR), ("cancelar", Accion.TURNO_CANCELAR),
            ("reprogramar", Accion.TURNO_REPROGRAMAR),
        ]
        if principal is not None and principal.rol != RolUsuario.PACIENTE:
            candidatas.extend([
                ("atendido", Accion.TURNO_ATENDIDO), ("ausente", Accion.TURNO_AUSENTE),
                ("corregir_ausente", Accion.TURNO_CORREGIR_AUSENTE),
                ("responder_sobreturno", Accion.SOBRETURNO_RESPONDER),
            ])
        acciones = (tuple(
            nombre for nombre, accion in candidatas
            if (accion != Accion.SOBRETURNO_RESPONDER or profesional_activo == turno.profesional_id)
            and (principal.rol != RolUsuario.PROFESIONAL or accion not in (Accion.TURNO_ATENDIDO, Accion.TURNO_AUSENTE)
                 or profesional_activo == turno.profesional_id)
            and autorizar(principal, accion, turno, contexto).permitido
        ) if principal is not None and contexto is not None else None)
        return TurnoConsultado(
            id=turno.id, paciente_id=paciente.id, paciente_nombre=paciente.nombre,
            paciente_apellido=paciente.apellido, profesional_id=turno.profesional_id,
            box_id=turno.box_id, prestacion_id=prestacion.id, prestacion_nombre=prestacion.nombre,
            inicio=turno.inicio, fin=turno.fin, estado=turno.estado,
            es_sobreturno=turno.es_sobreturno, marcado_sin_confirmar_en=turno.marcado_sin_confirmar_en,
            acciones_permitidas=acciones,
            autorizacion_sobreturno=autorizacion,
        )

    async def _presentar_varios(self, unidad: UnidadDeTrabajo, turnos: list[Turno],
                                principal: Principal, contexto: ContextoAcceso) -> list[TurnoConsultado]:
        if not turnos:
            return []
        consultorio_id = principal.consultorio_id
        pacientes = await unidad.agenda.obtener_pacientes(consultorio_id, {t.paciente_id for t in turnos})
        prestaciones = await unidad.prestaciones.obtener_varios(consultorio_id, {t.prestacion_id for t in turnos})
        sobreturnos = {t.id for t in turnos if t.es_sobreturno} if principal.rol != RolUsuario.PACIENTE else set()
        autorizaciones = await unidad.sobreturnos.obtener_varios(consultorio_id, sobreturnos) if sobreturnos else {}
        profesional_activo = (await unidad.agenda.profesional_vinculado(consultorio_id, principal.usuario_id)
                              if principal.rol == RolUsuario.PROFESIONAL or autorizaciones else None)
        datos = DatosPresentacion(pacientes, prestaciones, autorizaciones, profesional_activo)
        return [await self._presentar(unidad, turno, principal, contexto, datos) for turno in turnos]

    async def detalle(self, principal: Principal, turno_id: int) -> TurnoConsultado:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            turno, contexto = await self._turno_autorizado(unidad, principal, turno_id, ahora)
            return await self._presentar(unidad, turno, principal, contexto)

    async def listar(self, principal: Principal, sin_confirmar: bool = False) -> list[TurnoConsultado]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            if sin_confirmar:
                self._autorizar(principal, Accion.TURNO_SIN_CONFIRMAR_VER,
                                None, ContextoAcceso(ahora=ahora))
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
                return await self._presentar_varios(unidad, turnos, principal, contexto)
            profesional_id = None
            vinculado = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                incluir_inactivos=True)
            recurso = await unidad.agenda.obtener_configuracion(principal.consultorio_id)
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = vinculado
                recurso = await unidad.profesionales.obtener(principal.consultorio_id, profesional_id,
                                                             incluir_inactivos=True)
            if recurso is None:
                self._rechazar(principal, Accion.AGENDA_VER, 404, "Agenda no encontrada")
            contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=vinculado)
            self._autorizar(principal, Accion.AGENDA_VER, recurso, contexto)
            turnos = await unidad.turnos.listar(principal.consultorio_id, profesional_id=profesional_id,
                                               sin_confirmar=sin_confirmar)
            return await self._presentar_varios(unidad, turnos, principal, contexto)

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
            return await self._presentar_varios(unidad, turnos, principal, contexto)

    async def de_paciente(self, principal: Principal, paciente_id: int, *, limit: int | None = None,
                          offset: int = 0) -> list[TurnoConsultado]:
        ahora = self._reloj.ahora()
        async with self._unidades() as unidad:
            profesional_id = None
            vinculado = await unidad.agenda.profesional_vinculado(principal.consultorio_id, principal.usuario_id,
                                                                incluir_inactivos=True)
            pacientes_permitidos = frozenset()
            if principal.rol == RolUsuario.PROFESIONAL:
                profesional_id = vinculado
                if profesional_id is not None:
                    pacientes_permitidos = await unidad.agenda.pacientes_de_profesional(principal.consultorio_id, profesional_id)
                # Un identificador de ficha fuera de la agenda se comporta como
                # inexistente: no se carga ni se revela su información (KB 11).
                if paciente_id not in pacientes_permitidos:
                    self._rechazar(principal, Accion.PACIENTE_VER, 404, "Ficha no encontrada")
            paciente = await unidad.agenda.obtener_paciente(principal.consultorio_id, paciente_id)
            if paciente is None:
                self._rechazar(principal, Accion.PACIENTE_VER, 404, "Ficha no encontrada")
            contexto = ContextoAcceso(ahora=ahora, profesional_vinculado_id=vinculado,
                turnos_del_profesional=pacientes_permitidos)
            self._autorizar(principal, Accion.PACIENTE_VER, paciente, contexto)
            turnos = await unidad.turnos.listar(principal.consultorio_id,
                profesional_id=profesional_id, paciente_id=paciente_id, limit=limit, offset=offset)
            return await self._presentar_varios(unidad, turnos, principal, contexto)
