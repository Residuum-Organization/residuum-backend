"""extrato_pontos_resgatado

Revision ID: 9c4a8e21b7f3
Revises: 7f2d3c7a8b11
Create Date: 2026-06-19 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c4a8e21b7f3"
down_revision: Union[str, None] = "7f2d3c7a8b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "resgate_pontuacao",
        sa.Column("id_resgate", sa.Integer(), nullable=False),
        sa.Column("pontos_utilizados", sa.Integer(), nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=False),
        sa.Column("referencia", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="resgatado", nullable=False),
        sa.Column("data_resgate", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id_resgate"),
    )
    op.create_index(op.f("ix_resgate_pontuacao_id_resgate"), "resgate_pontuacao", ["id_resgate"], unique=False)
    op.create_index(op.f("ix_resgate_pontuacao_usuario_id"), "resgate_pontuacao", ["usuario_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_resgate_pontuacao_usuario_id"), table_name="resgate_pontuacao")
    op.drop_index(op.f("ix_resgate_pontuacao_id_resgate"), table_name="resgate_pontuacao")
    op.drop_table("resgate_pontuacao")
