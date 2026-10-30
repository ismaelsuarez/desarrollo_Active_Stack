from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.value_objects.estado_turno import EstadoTurno
from app.infrastructure.db.base import Base

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
        Index("ix_token_usuario_usuario_id_tipo", "usuario_id", "tipo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("consultorio.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("usuario.id"))
    ciclo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    turno_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
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
    __table_args__ = (UniqueConstraint("box_id", name="profesional_box_unico"),)

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger, index=True)
    box_id: Mapped[int] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(Text)
    apellido: Mapped[str] = mapped_column(Text)


class PrestacionModel(Base):
    __tablename__ = "prestacion"
    __table_args__ = (
        UniqueConstraint("consultorio_id", "nombre", name="prestacion_nombre_unico"),
        CheckConstraint("duracion_min > 0", name="prestacion_duracion_positiva"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(BigInteger)
    nombre: Mapped[str] = mapped_column(Text)
    duracion_min: Mapped[int] = mapped_column(Integer)


class TurnoModel(Base):
    __tablename__ = "turno"
    __table_args__ = (
        CheckConstraint("inicio < fin", name="turno_inicio_antes_de_fin"),
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
    consultorio_id: Mapped[int] = mapped_column(BigInteger)
    paciente_id: Mapped[int] = mapped_column(BigInteger)
    profesional_id: Mapped[int] = mapped_column(ForeignKey("profesional.id"))
    box_id: Mapped[int] = mapped_column(BigInteger)
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
    creado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
