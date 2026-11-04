"""Completar turno e historial conservando el legado de C-00.

Revision ID: 0008_turnos_core
Revises: 0007_agenda_config
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008_turnos_core"
down_revision = "0007_agenda_config"
branch_labels = None
depends_on = None

REFERENCIAS_TURNO = (
    ("consultorio_id", "consultorio"), ("paciente_id", "paciente"), ("box_id", "box"),
    ("creado_por_id", "usuario"), ("cancelado_por_id", "usuario"),
)
INDICES = (
    ("turno", "ix_turno_consultorio_profesional_inicio", ["consultorio_id", "profesional_id", "inicio"]),
    ("turno", "ix_turno_consultorio_paciente_inicio", ["consultorio_id", "paciente_id", "inicio"]),
    ("turno", "ix_turno_estado_inicio", ["estado", "inicio"]),
    ("turno_historial", "ix_turno_historial_turno_fecha", ["turno_id", "ocurrido_en"]),
    ("turno_historial", "ix_turno_historial_consultorio_fecha", ["consultorio_id", "ocurrido_en"]),
)


def upgrade() -> None:
    conexion = op.get_bind()
    for columna, destino in REFERENCIAS_TURNO[:3]:
        huerfanos = conexion.scalar(sa.text(f"SELECT count(*) FROM turno t WHERE NOT EXISTS (SELECT 1 FROM {destino} d WHERE d.id=t.{columna})"))
        if huerfanos:
            raise RuntimeError(f"C-07: turno.{columna} contiene referencias huerfanas; corregir antes del upgrade")
    for tabla in ("token_usuario", "notificacion"):
        huerfanos = conexion.scalar(sa.text(f"SELECT count(*) FROM {tabla} t WHERE turno_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM turno WHERE id=t.turno_id)"))
        if huerfanos:
            raise RuntimeError(f"C-07: {tabla}.turno_id contiene referencias huerfanas; corregir antes del upgrade")
    op.add_column("turno", sa.Column("ciclo_confirmacion", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("turno", sa.Column("origen", sa.Text(), nullable=True))
    op.add_column("turno", sa.Column("creado_por_id", sa.BigInteger(), nullable=True))
    op.add_column("turno", sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True))
    for columna in ("confirmacion_solicitada_en", "recordatorio_enviado_en", "confirmado_en",
                    "marcado_sin_confirmar_en", "liberado_en", "cancelado_en", "reprogramado_de_inicio"):
        op.add_column("turno", sa.Column(columna, sa.DateTime(timezone=True), nullable=True))
    op.add_column("turno", sa.Column("cancelado_por_id", sa.BigInteger(), nullable=True))
    op.add_column("turno", sa.Column("motivo_cancelacion", sa.Text(), nullable=True))
    op.add_column("turno", sa.Column("notas", sa.Text(), nullable=True))
    op.create_check_constraint(op.f("ck_turno_origen_valido"), "turno", "origen IN ('online','recepcion')")
    op.create_check_constraint(op.f("ck_turno_ciclo_positivo"), "turno", "ciclo_confirmacion >= 1")
    op.alter_column("turno", "creado_en", server_default=None)
    op.create_table(
        "turno_historial",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("consultorio_id", sa.BigInteger(), sa.ForeignKey("consultorio.id"), nullable=False),
        sa.Column("turno_id", sa.BigInteger(), sa.ForeignKey("turno.id"), nullable=False),
        sa.Column("usuario_id", sa.BigInteger(), sa.ForeignKey("usuario.id"), nullable=True),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("estado_anterior", sa.Text(), nullable=True),
        sa.Column("estado_nuevo", sa.Text(), nullable=False),
        sa.Column("detalle", JSONB(), nullable=True),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("accion IN ('crear','confirmar','cancelar','liberar','atendido','ausente','reprogramar','sobreturno','marcar_sin_confirmar','corregir')", name=op.f("ck_turno_historial_accion_valida")),
        sa.CheckConstraint("estado_anterior IN ('pendiente','confirmado','ausente','atendido','cancelado','liberado')", name=op.f("ck_turno_historial_estado_anterior_valido")),
        sa.CheckConstraint("estado_nuevo IN ('pendiente','confirmado','ausente','atendido','cancelado','liberado')", name=op.f("ck_turno_historial_estado_nuevo_valido")),
    )
    for tabla in ("token_usuario", "notificacion"):
        op.create_foreign_key(f"fk_{tabla}_turno_id_turno", tabla, "turno", ["turno_id"], ["id"])
    for columna, destino in REFERENCIAS_TURNO:
        op.create_foreign_key(f"fk_turno_{columna}_{destino}", "turno", destino, [columna], ["id"])
    for tabla, nombre, columnas in INDICES:
        op.create_index(nombre, tabla, columnas)


def downgrade() -> None:
    op.drop_constraint(op.f("ck_turno_origen_valido"), "turno", type_="check")
    op.drop_constraint(op.f("ck_turno_ciclo_positivo"), "turno", type_="check")
    for tabla, nombre, _ in reversed(INDICES):
        op.drop_index(nombre, table_name=tabla)
    for columna, destino in REFERENCIAS_TURNO:
        op.drop_constraint(f"fk_turno_{columna}_{destino}", "turno", type_="foreignkey")
    for tabla in ("token_usuario", "notificacion"):
        op.drop_constraint(f"fk_{tabla}_turno_id_turno", tabla, type_="foreignkey")
    op.drop_table("turno_historial")
    op.alter_column("turno", "creado_en", server_default=sa.text("now()"))
    for columna in ("notas", "motivo_cancelacion", "cancelado_por_id", "reprogramado_de_inicio",
                    "cancelado_en", "liberado_en", "marcado_sin_confirmar_en", "confirmado_en",
                    "recordatorio_enviado_en", "confirmacion_solicitada_en", "actualizado_en",
                    "creado_por_id", "origen", "ciclo_confirmacion"):
        op.drop_column("turno", columna)
