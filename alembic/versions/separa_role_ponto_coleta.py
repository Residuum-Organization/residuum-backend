"""separa contas de pontos de coleta e cooperativas

Revision ID: separa_role_ponto_coleta
Revises: coleta_solicitacao_admin
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "separa_role_ponto_coleta"
down_revision: Union[str, None] = "coleta_solicitacao_admin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    usuario = sa.table(
        "usuario",
        sa.column("id", sa.Integer()),
        sa.column("role", sa.String()),
    )
    ponto_coleta = sa.table(
        "ponto_coleta",
        sa.column("cooperativa_id", sa.Integer()),
    )

    # Contas antigas promovidas como cooperativa para representar um ponto
    # passam a ter o role correto. Cooperativas sem ponto permanecem intactas.
    ids_dos_pontos = sa.select(ponto_coleta.c.cooperativa_id).where(
        ponto_coleta.c.cooperativa_id.is_not(None)
    )
    bind.execute(
        sa.update(usuario)
        .where(usuario.c.id.in_(ids_dos_pontos))
        .where(usuario.c.role == "cooperativa")
        .values(role="ponto_coleta")
    )


def downgrade() -> None:
    bind = op.get_bind()
    usuario = sa.table(
        "usuario",
        sa.column("id", sa.Integer()),
        sa.column("role", sa.String()),
    )
    ponto_coleta = sa.table(
        "ponto_coleta",
        sa.column("cooperativa_id", sa.Integer()),
    )
    ids_dos_pontos = sa.select(ponto_coleta.c.cooperativa_id).where(
        ponto_coleta.c.cooperativa_id.is_not(None)
    )
    bind.execute(
        sa.update(usuario)
        .where(usuario.c.id.in_(ids_dos_pontos))
        .where(usuario.c.role == "ponto_coleta")
        .values(role="cooperativa")
    )