"""adiciona snapshot do inventario na solicitacao de coleta

Revision ID: snapshot_inventario_coleta
Revises: separa_role_ponto_coleta
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "snapshot_inventario_coleta"
down_revision: Union[str, None] = "separa_role_ponto_coleta"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "solicitacao_coleta",
        sa.Column("inventario_solicitado", sa.JSON(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE solicitacao_coleta "
            "SET inventario_solicitado = '{}' "
            "WHERE inventario_solicitado IS NULL"
        )
    )
    op.alter_column("solicitacao_coleta", "inventario_solicitado", nullable=False)


def downgrade() -> None:
    op.drop_column("solicitacao_coleta", "inventario_solicitado")