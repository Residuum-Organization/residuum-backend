"""Adiciona detalhes e filtros para pontos de coleta

Revision ID: task8_task9_pontos_detalhes_filtros
Revises: task11_inventario_usuario
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "task8_task9_pontos"
down_revision: Union[str, None] = "task11_inventario_usuario"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ponto_coleta", sa.Column("capacidade_maxima", sa.Float(), nullable=True))
    op.add_column("ponto_coleta", sa.Column("tipos_residuos_aceitos", sa.JSON(), nullable=True))
    op.add_column("ponto_coleta", sa.Column("horario_funcionamento", sa.String(length=255), nullable=True))
    op.add_column("ponto_coleta", sa.Column("status", sa.String(length=20), server_default="ativo", nullable=True))

    # Mantém pontos antigos compatíveis com a nova estrutura.
    op.execute("UPDATE ponto_coleta SET tipos_residuos_aceitos = '[\"plastico\", \"papel\", \"papelao\", \"metal\", \"vidro\", \"aluminio\", \"cobre\", \"pilhas\", \"baterias\"]'::json WHERE tipos_residuos_aceitos IS NULL")
    op.execute("UPDATE ponto_coleta SET status = CASE WHEN ativo = 0 THEN 'inativo' ELSE 'ativo' END WHERE status IS NULL")


def downgrade() -> None:
    op.drop_column("ponto_coleta", "status")
    op.drop_column("ponto_coleta", "horario_funcionamento")
    op.drop_column("ponto_coleta", "tipos_residuos_aceitos")
    op.drop_column("ponto_coleta", "capacidade_maxima")
