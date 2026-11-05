from typing import Any
from app.domain.entities.auth import Principal, RolUsuario
from app.domain.value_objects.accion import Accion
from app.domain.value_objects.contexto_acceso import ContextoAcceso
from app.domain.value_objects.decision import Decision
from app.domain.value_objects.estado_turno import EstadoTurno
from app.domain.policies.consultorio import mismo_consultorio
from app.domain.policies.turno import (
    es_dueno_de_agenda,
    es_titular_del_turno,
    turno_es_modificable,
    dentro_de_ventana_paciente,
    hora_de_inicio_alcanzada,
    puede_liberar_turno,
)
from app.domain.policies.sobreturno import (
    puede_autorizar_sobreturno,
    puede_responder_sobreturno,
)
from app.domain.policies.paciente import (
    puede_ver_paciente,
    puede_editar_paciente,
    puede_vincular_paciente,
    puede_desvincular_paciente,
    puede_reactivar_paciente,
)
from app.domain.policies.indicadores import puede_ver_ausentismo


def autorizar(
    usuario: Principal | None,
    accion: Accion,
    recurso: Any = None,
    contexto: ContextoAcceso | None = None,
) -> Decision:
    """Punto de entrada unificado para autorización ABAC con denegación por defecto (default-deny)."""
    # 0. Validación de usuario autenticado
    if usuario is None:
        return Decision(permitido=False, motivo="no_autenticado", codigo_http=401)

    # 1. Rol administrativo no posee permisos funcionales en la v1 (reservado)
    if usuario.rol == RolUsuario.ADMINISTRATIVO:
        return Decision(permitido=False, motivo="rol_administrativo_reservado", codigo_http=403)

    # 2. A2 - Aislamiento estricto por consultorio (evaluado siempre y primero si el recurso tiene consultorio_id)
    if recurso is not None and hasattr(recurso, "consultorio_id"):
        if not mismo_consultorio(usuario, recurso):
            return Decision(permitido=False, motivo="consultorio_ajeno", codigo_http=404)

    # Variables de contexto seguras
    ctx = contexto
    ficha_vigente_id = ctx.ficha_vigente_id if ctx else None
    profesional_id = ctx.profesional_vinculado_id if ctx else None
    ficha_usuario_id = ctx.ficha_usuario_id if ctx else None
    turnos_del_prof = ctx.turnos_del_profesional if ctx else frozenset()
    ahora = ctx.ahora if ctx else None
    horas_limite = ctx.horas_limite_cancelacion if ctx else 24
    modo_manual = ctx.consultorio_modo_manual if ctx else False
    sin_confirmar = ctx.turno_sin_confirmar if ctx else False

    # 3. Evaluación de acciones según matriz de decisión
    if accion == Accion.TURNO_SIN_CONFIRMAR_VER:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.AGENDA_VER:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            return Decision(permitido=True)
        if usuario.rol == RolUsuario.PROFESIONAL:
            # recurso puede ser profesional_id o un objeto con id
            target_prof_id = getattr(recurso, "id", recurso)
            if profesional_id is not None and target_prof_id == profesional_id:
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="agenda_ajena", codigo_http=403)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.TURNO_VER:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            return Decision(permitido=True)
        if usuario.rol == RolUsuario.PROFESIONAL:
            if es_dueno_de_agenda(usuario, recurso, profesional_id=profesional_id):
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="turno_ajeno", codigo_http=404)
        if usuario.rol == RolUsuario.PACIENTE:
            if es_titular_del_turno(usuario, recurso, ficha_vigente_id=ficha_vigente_id):
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="turno_ajeno", codigo_http=404)

    elif accion == Accion.TURNO_CREAR:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            return Decision(permitido=True)
        if usuario.rol == RolUsuario.PACIENTE:
            if ctx is not None and not ctx.correo_verificado:
                return Decision(permitido=False, motivo="correo_no_verificado", codigo_http=403)
            if ficha_vigente_id is not None:
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="paciente_sin_ficha_vigente", codigo_http=403)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion in (Accion.TURNO_REPROGRAMAR, Accion.TURNO_CANCELAR):
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            if turno_es_modificable(recurso):
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="turno_no_modificable", codigo_http=403)
        if usuario.rol == RolUsuario.PACIENTE:
            if not es_titular_del_turno(usuario, recurso, ficha_vigente_id=ficha_vigente_id):
                return Decision(permitido=False, motivo="turno_ajeno", codigo_http=404)
            if not turno_es_modificable(recurso):
                return Decision(permitido=False, motivo="turno_no_modificable", codigo_http=403)
            if ahora is not None and not dentro_de_ventana_paciente(recurso, ahora=ahora, horas_limite=horas_limite):
                return Decision(permitido=False, motivo="fuera_de_ventana_paciente", codigo_http=403)
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.TURNO_CONFIRMAR:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            if recurso is not None and recurso.estado == EstadoTurno.PENDIENTE:
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="estado_no_pendiente", codigo_http=403)
        if usuario.rol == RolUsuario.PACIENTE:
            if not es_titular_del_turno(usuario, recurso, ficha_vigente_id=ficha_vigente_id):
                return Decision(permitido=False, motivo="turno_ajeno", codigo_http=404)
            if recurso is not None and recurso.estado == EstadoTurno.PENDIENTE:
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="estado_no_pendiente", codigo_http=403)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion in (Accion.TURNO_ATENDIDO, Accion.TURNO_AUSENTE):
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION, RolUsuario.PROFESIONAL):
            if usuario.rol == RolUsuario.PROFESIONAL:
                if not es_dueno_de_agenda(usuario, recurso, profesional_id=profesional_id):
                    return Decision(permitido=False, motivo="turno_ajeno", codigo_http=404)
            if recurso is None or recurso.estado not in (EstadoTurno.PENDIENTE, EstadoTurno.CONFIRMADO):
                return Decision(permitido=False, motivo="estado_invalido_para_atendido_o_ausente", codigo_http=403)
            if ahora is not None and not hora_de_inicio_alcanzada(recurso, ahora=ahora):
                return Decision(permitido=False, motivo="hora_inicio_no_alcanzada", codigo_http=403)
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.TURNO_CORREGIR_AUSENTE:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            if recurso is not None and recurso.estado == EstadoTurno.AUSENTE:
                return Decision(permitido=True)
            return Decision(permitido=False, motivo="turno_no_ausente", codigo_http=403)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.TURNO_LIBERAR:
        if puede_liberar_turno(usuario, recurso, modo_manual=modo_manual, sin_confirmar=sin_confirmar):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="liberacion_no_permitida", codigo_http=403)

    elif accion == Accion.SOBRETURNO_AUTORIZAR:
        if puede_autorizar_sobreturno(usuario):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.SOBRETURNO_RESPONDER:
        if puede_responder_sobreturno(usuario, recurso, profesional_id=profesional_id):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="sobreturno_responder_denegado", codigo_http=403)

    elif accion == Accion.PACIENTE_VER:
        paciente_id = getattr(recurso, "id", recurso)
        if puede_ver_paciente(usuario, paciente_id, ficha_usuario_id=ficha_usuario_id, turnos_del_profesional=turnos_del_prof):
            return Decision(permitido=True)
        if usuario.rol == RolUsuario.PACIENTE:
            return Decision(permitido=False, motivo="paciente_ajeno", codigo_http=404)
        if usuario.rol == RolUsuario.PROFESIONAL:
            return Decision(permitido=False, motivo="paciente_no_asignado", codigo_http=404)
        return Decision(permitido=False, motivo="paciente_no_asignado", codigo_http=403)

    elif accion == Accion.PACIENTE_EDITAR:
        paciente_id = getattr(recurso, "id", recurso)
        if puede_editar_paciente(usuario, paciente_id, ficha_usuario_id=ficha_usuario_id):
            return Decision(permitido=True)
        if usuario.rol == RolUsuario.PACIENTE:
            return Decision(permitido=False, motivo="paciente_ajeno", codigo_http=404)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.PACIENTE_VINCULAR:
        if puede_vincular_paciente(usuario):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.PACIENTE_DESVINCULAR:
        if puede_desvincular_paciente(usuario):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.PACIENTE_REACTIVAR:
        if puede_reactivar_paciente(usuario):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.CONFIGURACION_GESTIONAR:
        if usuario.rol == RolUsuario.ADMINISTRADOR:
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.NOTIFICACION_GESTIONAR:
        if usuario.rol in (RolUsuario.ADMINISTRADOR, RolUsuario.RECEPCION):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    elif accion == Accion.INDICADOR_AUSENTISMO:
        if puede_ver_ausentismo(usuario):
            return Decision(permitido=True)
        return Decision(permitido=False, motivo="rol_no_autorizado", codigo_http=403)

    # Denegación por defecto final
    return Decision(permitido=False, motivo="accion_no_permitida", codigo_http=403)
