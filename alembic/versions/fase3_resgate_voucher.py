"""fase3_resgate_voucher

Revision ID: fase3_resgate_voucher
Revises: fase2_solicitacao_ponto_coleta
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fase3_resgate_voucher"
down_revision: Union[str, Sequence[str], None] = "fase2_solicitacao_ponto_coleta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resgate_voucher",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voucher_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("codigo", sa.String(length=40), nullable=False),
        sa.Column("pontos_utilizados", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="ativo", nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["voucher_id"], ["vouchers.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resgate_voucher_id"), "resgate_voucher", ["id"], unique=False)
    op.create_index("ix_resgate_voucher_voucher_id", "resgate_voucher", ["voucher_id"], unique=False)
    op.create_index("ix_resgate_voucher_usuario_id", "resgate_voucher", ["usuario_id"], unique=False)
    op.create_index("ix_resgate_voucher_codigo", "resgate_voucher", ["codigo"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_resgate_voucher_codigo", table_name="resgate_voucher")
    op.drop_index("ix_resgate_voucher_usuario_id", table_name="resgate_voucher")
    op.drop_index("ix_resgate_voucher_voucher_id", table_name="resgate_voucher")
    op.drop_index(op.f("ix_resgate_voucher_id"), table_name="resgate_voucher")
    op.drop_table("resgate_voucher")
