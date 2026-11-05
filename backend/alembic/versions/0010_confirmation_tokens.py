"""Permitir confirmación por enlace para fichas sin cuenta.

Revision ID: 0010_confirmation_tokens
Revises: 0009_notifications_outbox_sweep
"""
import sqlalchemy as sa
from alembic import op

revision = "0010_confirmation_tokens"
down_revision = "0009_notifications_outbox_sweep"
branch_labels = None
depends_on = None


def upgrade() -> None:
    incompatibles = op.get_bind().scalar(sa.text(
        "SELECT EXISTS (SELECT 1 FROM token_usuario WHERE tipo = 'confirmar_turno' "
        "AND (turno_id IS NULL OR ciclo IS NULL OR ciclo <= 0))"
    ))
    if incompatibles:
        raise RuntimeError("Existen tokens de confirmación históricos incompatibles; revisar antes de migrar")
    op.alter_column("token_usuario", "usuario_id", existing_type=sa.BigInteger(), nullable=True)
    op.create_check_constraint(
        "ck_token_usuario_proposito_coherente", "token_usuario",
        "(tipo = 'confirmar_turno' AND turno_id IS NOT NULL AND ciclo IS NOT NULL AND ciclo > 0) "
        "OR (tipo <> 'confirmar_turno' AND usuario_id IS NOT NULL)",
    )


def downgrade() -> None:
    if op.get_bind().scalar(sa.text("SELECT EXISTS (SELECT 1 FROM token_usuario WHERE usuario_id IS NULL)")):
        raise RuntimeError("No se puede bajar: existen tokens de confirmación sin cuenta")
    op.drop_constraint("ck_token_usuario_proposito_coherente", "token_usuario", type_="check")
    op.alter_column("token_usuario", "usuario_id", existing_type=sa.BigInteger(), nullable=False)
