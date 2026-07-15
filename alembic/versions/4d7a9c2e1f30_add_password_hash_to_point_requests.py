"""add password hash to collection point requests

Revision ID: 4d7a9c2e1f30
Revises: 1804368d1790
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d7a9c2e1f30"
down_revision: Union[str, None] = "1804368d1790"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "solicitacao_ponto_coleta",
        sa.Column("senha_hash", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("solicitacao_ponto_coleta", "senha_hash")
