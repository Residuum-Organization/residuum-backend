"""fase5_campanhas

Revision ID: fase5_campanhas
Revises: fase4_bilhete_sorteio
Create Date: 2026-07-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "fase5_campanhas"
down_revision: Union[str, Sequence[str], None] = "fase4_bilhete_sorteio"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "campanhas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column("patrocinador", sa.String(length=255), nullable=False),
        sa.Column("patrocinador_logo_url", sa.String(length=500), nullable=True),
        sa.Column("pontos_recompensa", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=30), server_default="ativa", nullable=False),
        sa.Column("data_inicio", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_fim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("atualizado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campanhas_id"), "campanhas", ["id"], unique=False)
    op.create_index("ix_campanhas_status", "campanhas", ["status"], unique=False)

    op.create_table(
        "inscricao_campanha",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("campanha_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("pontos_concedidos", sa.Integer(), server_default="0", nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["campanha_id"], ["campanhas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campanha_id", "usuario_id", name="uq_inscricao_campanha_usuario"),
    )
    op.create_index(op.f("ix_inscricao_campanha_id"), "inscricao_campanha", ["id"], unique=False)
    op.create_index("ix_inscricao_campanha_campanha_id", "inscricao_campanha", ["campanha_id"], unique=False)
    op.create_index("ix_inscricao_campanha_usuario_id", "inscricao_campanha", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_inscricao_campanha_usuario_id", table_name="inscricao_campanha")
    op.drop_index("ix_inscricao_campanha_campanha_id", table_name="inscricao_campanha")
    op.drop_index(op.f("ix_inscricao_campanha_id"), table_name="inscricao_campanha")
    op.drop_table("inscricao_campanha")

    op.drop_index("ix_campanhas_status", table_name="campanhas")
    op.drop_index(op.f("ix_campanhas_id"), table_name="campanhas")
    op.drop_table("campanhas")
