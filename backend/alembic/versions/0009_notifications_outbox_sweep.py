"""Ciclo de las comunicaciones y estado operativo del barrido.

Revision ID: 0009_notifications_outbox_sweep
Revises: 0008_turnos_core
"""
import sqlalchemy as sa
from alembic import op

revision = "0009_notifications_outbox_sweep"
down_revision = "0008_turnos_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notificacion", sa.Column("ciclo", sa.Integer(), nullable=True))
    op.create_unique_constraint("uq_notificacion_turno_tipo_canal_ciclo", "notificacion", ["turno_id", "tipo", "canal", "ciclo"])
    op.create_table(
        "barrido_estado",
        sa.Column("consultorio_id", sa.BigInteger(), sa.ForeignKey("consultorio.id"), primary_key=True),
        sa.Column("ejecucion_id", sa.Uuid(), nullable=False),
        sa.Column("iniciado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estado", sa.Text(), nullable=False),
        *(sa.Column(nombre, sa.Integer(), nullable=False, server_default="0")
          for nombre in ("reclamadas", "enviadas", "reintentadas", "omitidas", "fallidas")),
        sa.CheckConstraint("estado IN ('en_curso','exitoso','error')", name=op.f("ck_barrido_estado_estado_valido")),
        sa.CheckConstraint("(estado = 'en_curso') = (finalizado_en IS NULL)", name=op.f("ck_barrido_estado_fin_consistente")),
        sa.CheckConstraint("finalizado_en IS NULL OR finalizado_en >= iniciado_en", name=op.f("ck_barrido_estado_fechas_ordenadas")),
        sa.CheckConstraint("reclamadas >= 0 AND enviadas >= 0 AND reintentadas >= 0 AND omitidas >= 0 AND fallidas >= 0", name=op.f("ck_barrido_estado_conteos_no_negativos")),
    )


def downgrade() -> None:
    op.drop_table("barrido_estado")
    op.drop_constraint("uq_notificacion_turno_tipo_canal_ciclo", "notificacion", type_="unique")
    op.drop_column("notificacion", "ciclo")
