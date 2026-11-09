"""Limitar solicitudes públicas de correo de cuenta por origen.

Revision ID: 0012_account_request_limit
Revises: 0011_overbooking_authorization
"""
import sqlalchemy as sa
from alembic import op

revision = '0012_account_request_limit'
down_revision = '0011_overbooking_authorization'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'intento_correo_cuenta',
        sa.Column('id', sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column('consultorio_id', sa.BigInteger(), sa.ForeignKey('consultorio.id'), nullable=False),
        sa.Column('origen_hash', sa.Text(), nullable=True),
        sa.Column('creado_en', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_intento_correo_cuenta_consultorio_id', 'intento_correo_cuenta', ['consultorio_id'])
    op.create_index('ix_intento_correo_cuenta_origen', 'intento_correo_cuenta', ['consultorio_id', 'origen_hash', 'creado_en'])
    op.create_index('ix_intento_correo_cuenta_creado_en', 'intento_correo_cuenta', ['creado_en'])


def downgrade() -> None:
    op.drop_table('intento_correo_cuenta')
