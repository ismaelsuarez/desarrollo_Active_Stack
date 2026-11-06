from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    Text,
    Time,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.base import Base
from app.infrastructure.db.account_models import SolicitudVinculacionModel, NotificacionModel, IntentoRegistroModel

RESTRICCION_SIN_SOLAPAMIENTO = "turno_sin_solapamiento"


class ConsultorioModel(Base):
    __tablename__ = "consultorio"
    __table_args__ = (
        CheckConstraint(
            "horas_confirmacion > horas_recordatorio "
            "AND horas_recordatorio > horas_liberacion "
            "AND horas_liberacion > 0 "
            "AND horas_limite_paciente > 0",
            name="ck_consultorio_horas_orden",
        ),
        CheckConstraint(
            "minutos_granularidad BETWEEN 5 AND 120",
            name="ck_consultorio_granularidad_valida",
        ),
        CheckConstraint(
            "dias_anticipacion_maxima >= 1",
            name="ck_consultorio_anticipacion_positiva",
        ),
        CheckConstraint(
            "max_turnos_activos_paciente >= 1",
            name="ck_consultorio_max_turnos_positivo",
        ),
        CheckConstraint(
            "modo_liberacion IN ('automatico', 'manual')",
            name="ck_consultorio_modo_liberacion_valido",
        ),
        CheckConstraint(
            "telefono IS NULL OR length(btrim(telefono)) BETWEEN 1 AND 40",
            name="ck_consultorio_telefono_valido",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    nombre: Mapped[str] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(Text, nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    zona_horaria: Mapped[str] = mapped_column(Text, default="America/Argentina/Buenos_Aires")
    modo_liberacion: Mapped[str] = mapped_column(Text, default="automatico")
    horas_confirmacion: Mapped[int] = mapped_column(Integer)
    horas_recordatorio: Mapped[int] = mapped_column(Integer)
    horas_liberacion: Mapped[int] = mapped_column(Integer)
    horas_limite_paciente: Mapped[int] = mapped_column(Integer)
    minutos_granularidad: Mapped[int] = mapped_column(Integer)
    dias_anticipacion_maxima: Mapped[int] = mapped_column(Integer)
    max_turnos_activos_paciente: Mapped[int] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UsuarioModel(Base):
    __tablename__ = "usuario"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "nombre_usuario", name="uq_usuario_consultorio_nombre_usuario"),
        UniqueConstraint("consultorio_id", "email", name="uq_usuario_consultorio_email"),
        UniqueConstraint("consultorio_id", "id", name="uq_usuario_consultorio_id"),
        CheckConstraint("nombre_usuario = lower(btrim(nombre_usuario))", name="ck_usuario_nombre_usuario_normalizado"),
        CheckConstraint("email = lower(btrim(email))", name="ck_usuario_email_normalizado"),
        CheckConstraint(
            "rol IN ('administrador', 'recepcion', 'profesional', 'paciente', 'administrativo')",
            name="ck_usuario_rol_valido",
        ),
        CheckConstraint(
            "(aviso_privacidad_aceptado_en IS NULL) = (aviso_privacidad_version IS NULL)",
            name="ck_usuario_aviso_privacidad_consistente",
        ),
        CheckConstraint(
            "rol <> 'paciente' OR aviso_privacidad_aceptado_en IS NOT NULL",
            name="ck_usuario_paciente_aviso_privacidad",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    nombre_usuario: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    rol: Mapped[str] = mapped_column(Text)
    email_verificado: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verificado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aviso_privacidad_aceptado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aviso_privacidad_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    ultimo_ingreso_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PacienteModel(Base):
    __tablename__ = "paciente"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "dni", name="uq_paciente_consultorio_dni"),
        UniqueConstraint("usuario_id", name="uq_paciente_usuario_id"),
        CheckConstraint("dni ~ '^[0-9]+$'", name="ck_paciente_dni_numerico"),
        CheckConstraint("email IS NULL OR email = lower(btrim(email))", name="ck_paciente_email_normalizado"),
        Index("ix_paciente_consultorio_apellido_nombre", "consultorio_id", "apellido", "nombre"),
        Index("ix_paciente_consultorio_telefono", "consultorio_id", "telefono"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    nombre: Mapped[str] = mapped_column(Text)
    apellido: Mapped[str] = mapped_column(Text)
    telefono: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    dni: Mapped[str] = mapped_column(Text)
    obra_social: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TokenUsuarioModel(Base):
    __tablename__ = "token_usuario"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_token_usuario_token_hash"),
        CheckConstraint(
            "tipo IN ('verificar_email', 'recuperar_password', 'confirmar_turno')",
            name="ck_token_usuario_tipo_valido",
        ),
        CheckConstraint(
            "(tipo = 'confirmar_turno' AND turno_id IS NOT NULL AND ciclo IS NOT NULL AND ciclo > 0) "
            "OR (tipo <> 'confirmar_turno' AND usuario_id IS NOT NULL)",
            name="proposito_coherente",
        ),
        Index("ix_token_usuario_usuario_id_tipo", "usuario_id", "tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"), nullable=True)
    ciclo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turno_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("turno.id"), nullable=True)
    tipo: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class RefreshTokenModel(Base):
    __tablename__ = "refresh_token"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_refresh_token_token_hash"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id"), index=True)
    token_hash: Mapped[str] = mapped_column(Text)
    expira_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revocado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reemplazado_por_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("refresh_token.id"), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntentoIngresoModel(Base):
    __tablename__ = "intento_ingreso"
    __table_args__ = (
        Index("ix_intento_ingreso_par", "consultorio_id", "identificador_hash", "origen_hash", "creado_en"),
        Index("ix_intento_ingreso_origen", "consultorio_id", "origen_hash", "creado_en"),
        Index("ix_intento_ingreso_creado_en", "creado_en"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    identificador_hash: Mapped[str] = mapped_column(Text)
    origen_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ProfesionalModel(Base):
    __tablename__ = "profesional"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "id", name="uq_profesional_consultorio_id"),
        UniqueConstraint("usuario_id", name="uq_profesional_usuario"),
        UniqueConstraint("box_id", name="profesional_box_unico"),
        ForeignKeyConstraint(["consultorio_id", "usuario_id"], ["usuario.consultorio_id", "usuario.id"]),
        ForeignKeyConstraint(["consultorio_id", "box_id"], ["box.consultorio_id", "box.id"]),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    usuario_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    box_id: Mapped[int] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(Text)
    apellido: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class BoxModel(Base):
    __tablename__ = "box"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "nombre", name="uq_box_consultorio_nombre"),
        UniqueConstraint("consultorio_id", "id", name="uq_box_consultorio_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    nombre: Mapped[str] = mapped_column(Text)
    activo: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class HorarioSemanalModel(Base):
    __tablename__ = "horario_semanal"
    __table_args__ = (
        CheckConstraint("dia_semana BETWEEN 1 AND 7", name="horario_semanal_dia_valido"),
        CheckConstraint("hora_inicio < hora_fin", name="horario_semanal_intervalo_valido"),
        ForeignKeyConstraint(["consultorio_id", "profesional_id"], ["profesional.consultorio_id", "profesional.id"]),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, index=True)
    profesional_id: Mapped[int] = mapped_column(BigInteger, index=True)
    dia_semana: Mapped[int] = mapped_column(Integer)
    hora_inicio: Mapped[time] = mapped_column(Time)
    hora_fin: Mapped[time] = mapped_column(Time)


class BloqueoAgendaModel(Base):
    __tablename__ = "bloqueo_agenda"
    __table_args__ = (
        CheckConstraint("inicio < fin", name="bloqueo_agenda_intervalo_valido"),
        CheckConstraint("tipo IN ('feriado', 'vacaciones', 'ausencia', 'bloqueo')", name="bloqueo_agenda_tipo_valido"),
        ForeignKeyConstraint(["consultorio_id", "profesional_id"], ["profesional.consultorio_id", "profesional.id"]),
        ForeignKeyConstraint(["consultorio_id", "creado_por_id"], ["usuario.consultorio_id", "usuario.id"]),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, index=True)
    profesional_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    tipo: Mapped[str] = mapped_column(Text)
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_por_id: Mapped[int] = mapped_column(BigInteger)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class PrestacionModel(Base):
    __tablename__ = "prestacion"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "nombre", name="prestacion_nombre_unico"),
        CheckConstraint("duracion_min > 0", name="prestacion_duracion_positiva"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    nombre: Mapped[str] = mapped_column(Text)
    duracion_min: Mapped[int] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    sugerida: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))


class TurnoModel(Base):
    __tablename__ = "turno"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "id", name="uq_turno_consultorio_id"),
        CheckConstraint("inicio < fin", name="turno_inicio_antes_de_fin"),
        CheckConstraint("origen IN ('online','recepcion')", name="origen_valido"),
        CheckConstraint("ciclo_confirmacion >= 1", name="ciclo_positivo"),
        Index("ix_turno_consultorio_profesional_inicio", "consultorio_id", "profesional_id", "inicio"),
        Index("ix_turno_consultorio_paciente_inicio", "consultorio_id", "paciente_id", "inicio"),
        Index("ix_turno_estado_inicio", "estado", "inicio"),
        # La restricción real la crea a mano la migración; se declara acá para
        # que el modelo documente el esquema (RN-17, DD-08).
        ExcludeConstraint(
            ("consultorio_id", "="),
            ("profesional_id", "="),
            (text("tstzrange(inicio, fin, '[)')"), "&&"),
            where=text(
                "es_sobreturno = false "
                "AND estado IN ('pendiente', 'confirmado', 'atendido', 'ausente')"
            ),
            using="gist",
            name=RESTRICCION_SIN_SOLAPAMIENTO,
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"))
    paciente_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("paciente.id"))
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesional.id"))
    box_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("box.id"))
    prestacion_id: Mapped[int] = mapped_column(ForeignKey("prestacion.id"))
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    estado: Mapped[EstadoTurno] = mapped_column(
        Enum(
            EstadoTurno,
            name="estado_turno",
            values_callable=lambda estados: [estado.value for estado in estados],
            create_type=False,
        ),
        server_default=EstadoTurno.PENDIENTE.value,
    )
    es_sobreturno: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    origen: Mapped[str | None] = mapped_column(Text)
    ciclo_confirmacion: Mapped[int] = mapped_column(Integer, server_default="1")
    confirmacion_solicitada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recordatorio_enviado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    marcado_sin_confirmar_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    liberado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_por_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    motivo_cancelacion: Mapped[str | None] = mapped_column(Text)
    reprogramado_de_inicio: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notas: Mapped[str | None] = mapped_column(Text)
    creado_por_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actualizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AutorizacionSobreturnoModel(Base):
    __tablename__ = "autorizacion_sobreturno"
    __table_args__ = (
        UniqueConstraint("turno_id", name="uq_autorizacion_sobreturno_turno"),
        CheckConstraint("length(btrim(motivo)) > 0", name="motivo_no_vacio"),
        CheckConstraint("respuesta IN ('aprobado', 'rechazado')", name="respuesta_valida"),
        ForeignKeyConstraint(["consultorio_id", "turno_id"], ["turno.consultorio_id", "turno.id"]),
        ForeignKeyConstraint(["consultorio_id", "autorizado_por_id"], ["usuario.consultorio_id", "usuario.id"]),
        ForeignKeyConstraint(["consultorio_id", "respondido_por_id"], ["usuario.consultorio_id", "usuario.id"]),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger)
    turno_id: Mapped[int] = mapped_column(BigInteger)
    autorizado_por_id: Mapped[int] = mapped_column(BigInteger)
    autorizado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    motivo: Mapped[str] = mapped_column(Text)
    avisado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    respuesta: Mapped[str | None] = mapped_column(Text)
    respondido_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    respondido_por_id: Mapped[int | None] = mapped_column(BigInteger)
    comentario: Mapped[str | None] = mapped_column(Text)


class TurnoHistorialModel(Base):
    __tablename__ = "turno_historial"
    __table_args__ = (
        Index("ix_turno_historial_turno_fecha", "turno_id", "ocurrido_en"),
        Index("ix_turno_historial_consultorio_fecha", "consultorio_id", "ocurrido_en"),
        CheckConstraint("accion IN ('crear','confirmar','cancelar','liberar','atendido','ausente','reprogramar','sobreturno','marcar_sin_confirmar','corregir')", name="accion_valida"),
        CheckConstraint("estado_anterior IN ('pendiente','confirmado','ausente','atendido','cancelado','liberado')", name="estado_anterior_valido"),
        CheckConstraint("estado_nuevo IN ('pendiente','confirmado','ausente','atendido','cancelado','liberado')", name="estado_nuevo_valido"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey("consultorio.id"))
    turno_id: Mapped[int] = mapped_column(ForeignKey("turno.id"))
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"))
    accion: Mapped[str] = mapped_column(Text)
    estado_anterior: Mapped[str | None] = mapped_column(Text)
    estado_nuevo: Mapped[str] = mapped_column(Text)
    detalle: Mapped[dict | None] = mapped_column(JSONB)
    ocurrido_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
