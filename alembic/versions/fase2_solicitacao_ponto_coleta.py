"""fase2_solicitacao_ponto_coleta

Revision ID: fase2_solicitacao_ponto_coleta
Revises: fase1_sorteios_vouchers
Create Date: 2026-07-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fase2_solicitacao_ponto_coleta"
down_revision: Union[str, Sequence[str], None] = "fase1_sorteios_vouchers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "solicitacao_ponto_coleta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_solicitante", sa.String(length=50), nullable=False),
        sa.Column("documento", sa.String(length=30), nullable=False),
        sa.Column("responsavel_nome", sa.String(length=255), nullable=False),
        sa.Column("responsavel_telefone", sa.String(length=30), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("nome_ponto", sa.String(length=255), nullable=False),
        sa.Column("endereco", sa.String(length=500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("horario_funcionamento", sa.String(length=255), nullable=True),
        sa.Column("tipos_residuos_aceitos", sa.JSON(), nullable=False),
        sa.Column("capacidade_maxima", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pendente", nullable=False),
        sa.Column("motivo_rejeicao", sa.String(length=500), nullable=True),
        sa.Column("observacao_admin", sa.String(length=500), nullable=True),
        sa.Column("ponto_coleta_id", sa.Integer(), nullable=True),
        sa.Column("revisado_por_id", sa.Integer(), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("revisado_em", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["ponto_coleta_id"], ["ponto_coleta.id"]),
        sa.ForeignKeyConstraint(["revisado_por_id"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.CheckConstraint(
            "status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada')",
            name="ck_solicitacao_ponto_coleta_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_solicitacao_ponto_coleta_id"), "solicitacao_ponto_coleta", ["id"], unique=False)
    op.create_index("ix_solicitacao_ponto_coleta_usuario_id", "solicitacao_ponto_coleta", ["usuario_id"], unique=False)
    op.create_index("ix_solicitacao_ponto_coleta_status", "solicitacao_ponto_coleta", ["status"], unique=False)
    op.create_index("ix_solicitacao_ponto_coleta_ponto_coleta_id", "solicitacao_ponto_coleta", ["ponto_coleta_id"], unique=False)
    op.create_index("ix_solicitacao_ponto_coleta_revisado_por_id", "solicitacao_ponto_coleta", ["revisado_por_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_solicitacao_ponto_coleta_revisado_por_id", table_name="solicitacao_ponto_coleta")
    op.drop_index("ix_solicitacao_ponto_coleta_ponto_coleta_id", table_name="solicitacao_ponto_coleta")
    op.drop_index("ix_solicitacao_ponto_coleta_status", table_name="solicitacao_ponto_coleta")
    op.drop_index("ix_solicitacao_ponto_coleta_usuario_id", table_name="solicitacao_ponto_coleta")
    op.drop_index(op.f("ix_solicitacao_ponto_coleta_id"), table_name="solicitacao_ponto_coleta")
    op.drop_table("solicitacao_ponto_coleta")
