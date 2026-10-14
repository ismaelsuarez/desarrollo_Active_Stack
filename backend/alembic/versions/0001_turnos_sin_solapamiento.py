"""Turnos sin solapamiento por profesional.

Revision ID: 0001_turnos_sin_solapamiento
Revises:
Create Date: 2026-10-13

Revisión escrita a mano: el autogenerate de Alembic no detecta la
restricción de exclusión.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001_turnos_sin_solapamiento"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    op.execute(
        """
        CREATE TYPE estado_turno AS ENUM (
            'pendiente', 'confirmado', 'ausente', 'atendido', 'cancelado', 'liberado'
        )
        """
    )

    op.execute(
        """
        CREATE TABLE profesional (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            consultorio_id bigint NOT NULL,
            box_id bigint NOT NULL,
            nombre text NOT NULL,
            apellido text NOT NULL,
            CONSTRAINT profesional_box_unico UNIQUE (box_id)
        )
        """
    )
    op.execute("CREATE INDEX ix_profesional_consultorio ON profesional (consultorio_id)")

    op.execute(
        """
        CREATE TABLE prestacion (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            consultorio_id bigint NOT NULL,
            nombre text NOT NULL,
            duracion_min integer NOT NULL,
            CONSTRAINT prestacion_nombre_unico UNIQUE (consultorio_id, nombre),
            CONSTRAINT prestacion_duracion_positiva CHECK (duracion_min > 0)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE turno (
            id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            consultorio_id bigint NOT NULL,
            paciente_id bigint NOT NULL,
            profesional_id bigint NOT NULL REFERENCES profesional (id),
            box_id bigint NOT NULL,
            prestacion_id bigint NOT NULL REFERENCES prestacion (id),
            inicio timestamptz NOT NULL,
            fin timestamptz NOT NULL,
            estado estado_turno NOT NULL DEFAULT 'pendiente',
            es_sobreturno boolean NOT NULL DEFAULT false,
            creado_en timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT turno_inicio_antes_de_fin CHECK (inicio < fin)
        )
        """
    )

    # No solapamiento por profesional (RN-17, DD-08). El rango semiabierto
    # permite turnos contiguos; cancelados, liberados y sobreturnos no cuentan.
    op.execute(
        """
        ALTER TABLE turno ADD CONSTRAINT turno_sin_solapamiento
          EXCLUDE USING gist (
            consultorio_id WITH =,
            profesional_id WITH =,
            tstzrange(inicio, fin, '[)') WITH &&
          )
          WHERE (es_sobreturno = false
                 AND estado IN ('pendiente', 'confirmado', 'atendido', 'ausente'))
        """
    )


def downgrade() -> None:
    # La extensión btree_gist se conserva: puede existir antes de esta revisión.
    op.execute("DROP TABLE turno")
    op.execute("DROP TABLE prestacion")
    op.execute("DROP TABLE profesional")
    op.execute("DROP TYPE estado_turno")
