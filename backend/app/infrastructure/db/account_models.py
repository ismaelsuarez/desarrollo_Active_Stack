"""Persistencia de cuenta y comunicaciones (C-05)."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import (BigInteger, CheckConstraint, DateTime, ForeignKey,
                        Identity, Index, Integer, Text, UniqueConstraint)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid

from app.infrastructure.db.base import Base


class SolicitudVinculacionModel(Base):
    __tablename__ = 'solicitud_vinculacion'
    __table_args__ = (
        CheckConstraint("estado IN ('pendiente', 'vinculada', 'rechazada')", name='estado_valido'),
        CheckConstraint("dni_declarado ~ '^[0-9]+$'", name='dni_numerico'),
        Index('ix_solicitud_consultorio_estado_fecha', 'consultorio_id', 'estado', 'creada_en'),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey('consultorio.id'), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey('usuario.id'), unique=True)
    dni_declarado: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text)
    paciente_id: Mapped[int | None] = mapped_column(ForeignKey('paciente.id'), index=True)
    resuelta_por_id: Mapped[int | None] = mapped_column(ForeignKey('usuario.id'), index=True)
    resuelta_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_rechazo: Mapped[str | None] = mapped_column(Text)
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


TIPOS_NOTIFICACION = (
    'verificacion_email', 'recuperacion_password', 'vinculacion_rechazada',
    'solicitud_confirmacion', 'recordatorio', 'liberacion',
    'cancelacion_por_personal', 'reprogramacion_por_personal',
    'resumen_reserva', 'cancelacion_por_paciente',
)
TIPOS_CUENTA = TIPOS_NOTIFICACION[:3]


class NotificacionModel(Base):
    __tablename__ = 'notificacion'
    __table_args__ = (
        UniqueConstraint('turno_id', 'tipo', 'canal', 'ciclo', name='uq_notificacion_turno_tipo_canal_ciclo'),
        CheckConstraint(f"tipo IN {TIPOS_NOTIFICACION!r}", name='tipo_valido'),
        CheckConstraint("canal IN ('email', 'whatsapp')", name='canal_valido'),
        CheckConstraint("estado IN ('programada','enviando','enviada','fallida','preparada','enviada_manual','omitida')", name='estado_valido'),
        CheckConstraint("(estado = 'enviando') = (reclamada_en IS NOT NULL)", name='reclamacion_consistente'),
        CheckConstraint('intentos >= 0', name='intentos_no_negativos'),
        Index('ix_notificacion_estado_programada', 'estado', 'programada_para'),
        Index('ix_notificacion_estado_reclamada', 'estado', 'reclamada_en'),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey('consultorio.id'), index=True)
    turno_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey('turno.id'), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey('usuario.id'), index=True)
    tipo: Mapped[str] = mapped_column(Text)
    canal: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(Text)
    destinatario: Mapped[str] = mapped_column(Text)
    ciclo: Mapped[int | None] = mapped_column(Integer)
    programada_para: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reclamada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    enviada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    ultimo_error: Mapped[str | None] = mapped_column(Text)
    mensaje: Mapped[str | None] = mapped_column(Text)
    enlace_whatsapp: Mapped[str | None] = mapped_column(Text)
    marcada_enviada_por_id: Mapped[int | None] = mapped_column(ForeignKey('usuario.id'), index=True)


class IntentoRegistroModel(Base):
    __tablename__ = 'intento_registro'
    __table_args__ = (
        Index('ix_intento_registro_origen', 'consultorio_id', 'origen_hash', 'creado_en'),
        Index('ix_intento_registro_creado_en', 'creado_en'),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey('consultorio.id'), index=True)
    origen_hash: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IntentoCorreoCuentaModel(Base):
    __tablename__ = 'intento_correo_cuenta'
    __table_args__ = (
        Index('ix_intento_correo_cuenta_origen', 'consultorio_id', 'origen_hash', 'creado_en'),
        Index('ix_intento_correo_cuenta_creado_en', 'creado_en'),
    )
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    consultorio_id: Mapped[int] = mapped_column(ForeignKey('consultorio.id'), index=True)
    origen_hash: Mapped[str | None] = mapped_column(Text)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class BarridoEstadoModel(Base):
    """Última ejecución iniciada; metadatos técnicos sin datos personales."""
    __tablename__ = 'barrido_estado'
    __table_args__ = (
        CheckConstraint("estado IN ('en_curso','exitoso','error')", name='estado_valido'),
        CheckConstraint("(estado = 'en_curso') = (finalizado_en IS NULL)", name='fin_consistente'),
        CheckConstraint("finalizado_en IS NULL OR finalizado_en >= iniciado_en", name='fechas_ordenadas'),
        CheckConstraint("reclamadas >= 0 AND enviadas >= 0 AND reintentadas >= 0 AND omitidas >= 0 AND fallidas >= 0", name='conteos_no_negativos'),
    )
    consultorio_id: Mapped[int] = mapped_column(ForeignKey('consultorio.id'), primary_key=True)
    ejecucion_id: Mapped[UUID] = mapped_column(Uuid)
    iniciado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finalizado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estado: Mapped[str] = mapped_column(Text)
    reclamadas: Mapped[int] = mapped_column(Integer, default=0)
    enviadas: Mapped[int] = mapped_column(Integer, default=0)
    reintentadas: Mapped[int] = mapped_column(Integer, default=0)
    omitidas: Mapped[int] = mapped_column(Integer, default=0)
    fallidas: Mapped[int] = mapped_column(Integer, default=0)
