"""Persistir autorizaciones de sobreturno.

Revision ID: 0011_overbooking_authorization
Revises: 0010_confirmation_tokens
"""
import sqlalchemy as sa
from alembic import op

revision = "0011_overbooking_authorization"
down_revision = "0010_confirmation_tokens"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint("uq_turno_consultorio_id", "turno", ["consultorio_id", "id"])
    op.create_table(
        "autorizacion_sobreturno",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("consultorio_id", sa.BigInteger(), nullable=False),
        sa.Column("turno_id", sa.BigInteger(), nullable=False),
        sa.Column("autorizado_por_id", sa.BigInteger(), nullable=False),
        sa.Column("autorizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("avisado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("respuesta", sa.Text(), nullable=True),
        sa.Column("respondido_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("respondido_por_id", sa.BigInteger(), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.UniqueConstraint("turno_id", name="uq_autorizacion_sobreturno_turno"),
        sa.CheckConstraint("length(btrim(motivo)) > 0", name="motivo_no_vacio"),
        sa.CheckConstraint("respuesta IN ('aprobado', 'rechazado')", name="respuesta_valida"),
        sa.ForeignKeyConstraint(["consultorio_id", "turno_id"], ["turno.consultorio_id", "turno.id"]),
        sa.ForeignKeyConstraint(["consultorio_id", "autorizado_por_id"], ["usuario.consultorio_id", "usuario.id"]),
        sa.ForeignKeyConstraint(["consultorio_id", "respondido_por_id"], ["usuario.consultorio_id", "usuario.id"]),
    )


def downgrade() -> None:
    op.drop_table("autorizacion_sobreturno")
    op.drop_constraint("uq_turno_consultorio_id", "turno", type_="unique")
