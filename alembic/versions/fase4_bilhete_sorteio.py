"""fase4_bilhete_sorteio

Revision ID: fase4_bilhete_sorteio
Revises: fase3_resgate_voucher
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fase4_bilhete_sorteio"
down_revision: Union[str, Sequence[str], None] = "fase3_resgate_voucher"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bilhete_sorteio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("sorteio_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("pontos_utilizados", sa.Integer(), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["sorteio_id"], ["sorteios.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sorteio_id", "usuario_id", name="uq_bilhete_sorteio_usuario"),
        sa.UniqueConstraint("sorteio_id", "numero", name="uq_bilhete_sorteio_numero"),
    )
    op.create_index(op.f("ix_bilhete_sorteio_id"), "bilhete_sorteio", ["id"], unique=False)
    op.create_index("ix_bilhete_sorteio_sorteio_id", "bilhete_sorteio", ["sorteio_id"], unique=False)
    op.create_index("ix_bilhete_sorteio_usuario_id", "bilhete_sorteio", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bilhete_sorteio_usuario_id", table_name="bilhete_sorteio")
    op.drop_index("ix_bilhete_sorteio_sorteio_id", table_name="bilhete_sorteio")
    op.drop_index(op.f("ix_bilhete_sorteio_id"), table_name="bilhete_sorteio")
    op.drop_table("bilhete_sorteio")
