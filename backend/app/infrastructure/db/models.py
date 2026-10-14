from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
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
