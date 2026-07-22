"""cria solicitacao de coleta admin cooperativa

Revision ID: coleta_solicitacao_admin
Revises: 4d7a9c2e1f30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "coleta_solicitacao_admin"
down_revision: Union[str, None] = "4d7a9c2e1f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "solicitacao_coleta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_id", sa.Integer(), nullable=False),
        sa.Column("cooperativa_id", sa.Integer(), nullable=False),
        sa.Column("ponto_coleta_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="solicitada", nullable=False),
        sa.Column("percentual_ocupacao", sa.Float(), nullable=True),
        sa.Column("quantidade_inventario", sa.Float(), nullable=False),
        sa.Column("quantidade_coletada", sa.Float(), nullable=True),
        sa.Column("capacidade_maxima", sa.Float(), nullable=True),
        sa.Column("observacao", sa.Text(), nullable=True),
        sa.Column("motivo_recusa", sa.Text(), nullable=True),
        sa.Column("data_solicitacao", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("data_aceite", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_conclusao", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["admin_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["cooperativa_id"], ["usuario.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ponto_coleta_id"], ["ponto_coleta.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solicitacao_coleta_id", "solicitacao_coleta", ["id"], unique=False)
    op.create_index("ix_solicitacao_coleta_admin_id", "solicitacao_coleta", ["admin_id"], unique=False)
    op.create_index("ix_solicitacao_coleta_cooperativa_id", "solicitacao_coleta", ["cooperativa_id"], unique=False)
    op.create_index("ix_solicitacao_coleta_ponto_coleta_id", "solicitacao_coleta", ["ponto_coleta_id"], unique=False)
    op.create_index("ix_solicitacao_coleta_status", "solicitacao_coleta", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_solicitacao_coleta_status", table_name="solicitacao_coleta")
    op.drop_index("ix_solicitacao_coleta_ponto_coleta_id", table_name="solicitacao_coleta")
    op.drop_index("ix_solicitacao_coleta_cooperativa_id", table_name="solicitacao_coleta")
    op.drop_index("ix_solicitacao_coleta_admin_id", table_name="solicitacao_coleta")
    op.drop_index("ix_solicitacao_coleta_id", table_name="solicitacao_coleta")
    op.drop_table("solicitacao_coleta")
