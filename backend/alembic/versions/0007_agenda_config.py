"""Persist agenda configuration for C-06.

Revision ID: 0007_agenda_config
Revises: 0006_intento_registro
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_agenda_config"
down_revision: str | None = "0006_intento_registro"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_consultorio_telefono_valido",
        "consultorio",
        "telefono IS NULL OR length(btrim(telefono)) BETWEEN 1 AND 40",
    )
    op.create_unique_constraint("uq_usuario_consultorio_id", "usuario", ["consultorio_id", "id"])
    op.create_table(
        "box",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("consultorio_id", sa.BigInteger(), sa.ForeignKey("consultorio.id"), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.UniqueConstraint("consultorio_id", "nombre", name="uq_box_consultorio_nombre"),
        sa.UniqueConstraint("consultorio_id", "id", name="uq_box_consultorio_id"),
    )
    op.create_index("ix_box_consultorio_id", "box", ["consultorio_id"])
    op.add_column("profesional", sa.Column("usuario_id", sa.BigInteger(), nullable=True))
    op.add_column("profesional", sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.create_unique_constraint("uq_profesional_consultorio_id", "profesional", ["consultorio_id", "id"])
    op.create_unique_constraint("uq_profesional_usuario", "profesional", ["usuario_id"])
    op.create_foreign_key("fk_profesional_consultorio", "profesional", "consultorio", ["consultorio_id"], ["id"])
    op.create_foreign_key("fk_profesional_consultorio_usuario", "profesional", "usuario", ["consultorio_id", "usuario_id"], ["consultorio_id", "id"])
    op.create_foreign_key("fk_profesional_consultorio_box", "profesional", "box", ["consultorio_id", "box_id"], ["consultorio_id", "id"])
    op.create_table(
        "horario_semanal",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("consultorio_id", sa.BigInteger(), nullable=False),
        sa.Column("profesional_id", sa.BigInteger(), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_inicio", sa.Time(), nullable=False),
        sa.Column("hora_fin", sa.Time(), nullable=False),
        sa.CheckConstraint("dia_semana BETWEEN 1 AND 7", name="ck_horario_semanal_dia_valido"),
        sa.CheckConstraint("hora_inicio < hora_fin", name="ck_horario_semanal_intervalo_valido"),
        sa.ForeignKeyConstraint(["consultorio_id", "profesional_id"], ["profesional.consultorio_id", "profesional.id"], name="fk_horario_semanal_consultorio_profesional"),
    )
    op.create_index("ix_horario_semanal_consultorio_id", "horario_semanal", ["consultorio_id"])
    op.create_index("ix_horario_semanal_profesional_dia", "horario_semanal", ["profesional_id", "dia_semana"])
    op.create_table(
        "bloqueo_agenda",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), primary_key=True),
        sa.Column("consultorio_id", sa.BigInteger(), nullable=False),
        sa.Column("profesional_id", sa.BigInteger(), nullable=True),
        sa.Column("tipo", sa.Text(), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("creado_por_id", sa.BigInteger(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("inicio < fin", name="ck_bloqueo_agenda_intervalo_valido"),
        sa.CheckConstraint("tipo IN ('feriado', 'vacaciones', 'ausencia', 'bloqueo')", name="ck_bloqueo_agenda_tipo_valido"),
        sa.ForeignKeyConstraint(["consultorio_id", "profesional_id"], ["profesional.consultorio_id", "profesional.id"], name="fk_bloqueo_agenda_consultorio_profesional"),
        sa.ForeignKeyConstraint(["consultorio_id", "creado_por_id"], ["usuario.consultorio_id", "usuario.id"], name="fk_bloqueo_agenda_consultorio_actor"),
    )
    op.create_index("ix_bloqueo_agenda_consultorio_id", "bloqueo_agenda", ["consultorio_id"])
    op.create_index("ix_bloqueo_agenda_intervalo", "bloqueo_agenda", ["consultorio_id", "inicio", "fin"])
    op.add_column("prestacion", sa.Column("activa", sa.Boolean(), server_default=sa.text("true"), nullable=False))
    op.add_column("prestacion", sa.Column("sugerida", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    op.create_foreign_key("fk_prestacion_consultorio", "prestacion", "consultorio", ["consultorio_id"], ["id"])
    op.create_index("ix_prestacion_consultorio_id", "prestacion", ["consultorio_id"])


def downgrade() -> None:
    op.drop_constraint("ck_consultorio_telefono_valido", "consultorio", type_="check")
    op.drop_table("bloqueo_agenda")
    op.drop_table("horario_semanal")
    op.drop_index("ix_prestacion_consultorio_id", table_name="prestacion")
    op.drop_constraint("fk_prestacion_consultorio", "prestacion", type_="foreignkey")
    op.drop_column("prestacion", "sugerida")
    op.drop_column("prestacion", "activa")
    op.drop_constraint("fk_profesional_consultorio_box", "profesional", type_="foreignkey")
    op.drop_constraint("fk_profesional_consultorio_usuario", "profesional", type_="foreignkey")
    op.drop_constraint("fk_profesional_consultorio", "profesional", type_="foreignkey")
    op.drop_constraint("uq_profesional_usuario", "profesional", type_="unique")
    op.drop_constraint("uq_profesional_consultorio_id", "profesional", type_="unique")
    op.drop_column("profesional", "activo")
    op.drop_column("profesional", "usuario_id")
    op.drop_table("box")
    op.drop_constraint("uq_usuario_consultorio_id", "usuario", type_="unique")
