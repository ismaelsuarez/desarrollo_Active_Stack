from enum import StrEnum


class Accion(StrEnum):
    """Catálogo canónico de acciones del sistema sujetas a políticas de acceso (KB 11)."""

    AGENDA_VER = "agenda.ver"
    TURNO_VER = "turno.ver"
    TURNO_SIN_CONFIRMAR_VER = "turno.sin_confirmar_ver"
    TURNO_CREAR = "turno.crear"
    TURNO_REPROGRAMAR = "turno.reprogramar"
    TURNO_CANCELAR = "turno.cancelar"
    TURNO_CONFIRMAR = "turno.confirmar"
    TURNO_ATENDIDO = "turno.atendido"
    TURNO_AUSENTE = "turno.ausente"
    TURNO_CORREGIR_AUSENTE = "turno.corregir_ausente"
    TURNO_LIBERAR = "turno.liberar"
    SOBRETURNO_AUTORIZAR = "sobreturno.autorizar"
    SOBRETURNO_RESPONDER = "sobreturno.responder"
    PACIENTE_VER = "paciente.ver"
    PACIENTE_EDITAR = "paciente.editar"
    PACIENTE_VINCULAR = "paciente.vincular"
    PACIENTE_DESVINCULAR = "paciente.desvincular"
    PACIENTE_REACTIVAR = "paciente.reactivar"
    CONFIGURACION_GESTIONAR = "configuracion.gestionar"
    NOTIFICACION_GESTIONAR = "notificacion.gestionar"
    INDICADOR_AUSENTISMO = "indicador.ausentismo"
