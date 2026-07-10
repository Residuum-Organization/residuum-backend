"""fase1_sorteios_vouchers

Revision ID: fase1_sorteios_vouchers
Revises: 9c4a8e21b7f3, 910ca4b3facc
Create Date: 2026-07-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fase1_sorteios_vouchers"
down_revision: Union[str, Sequence[str], None] = ("9c4a8e21b7f3", "910ca4b3facc")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sorteios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("premio", sa.String(length=255), nullable=False),
        sa.Column("custo_pontos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="ativo", nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_sorteios_id"), "sorteios", ["id"], unique=False)
    op.create_index("ix_sorteios_status", "sorteios", ["status"], unique=False)

    op.create_table(
        "vouchers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("parceiro", sa.String(length=255), nullable=False),
        sa.Column("custo_pontos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("quantidade_disponivel", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="ativo", nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_vouchers_id"), "vouchers", ["id"], unique=False)
    op.create_index("ix_vouchers_status", "vouchers", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_vouchers_status", table_name="vouchers")
    op.drop_index(op.f("ix_vouchers_id"), table_name="vouchers")
    op.drop_table("vouchers")

    op.drop_index("ix_sorteios_status", table_name="sorteios")
    op.drop_index(op.f("ix_sorteios_id"), table_name="sorteios")
    op.drop_table("sorteios")
