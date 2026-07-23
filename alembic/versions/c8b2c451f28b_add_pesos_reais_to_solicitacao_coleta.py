"""add_pesos_reais_to_solicitacao_coleta

Revision ID: c8b2c451f28b
Revises: 9556f237a055
Create Date: 2026-07-23 10:55:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c8b2c451f28b'
down_revision = '9556f237a055'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('solicitacao_coleta', sa.Column('pesos_reais', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('solicitacao_coleta', 'pesos_reais')
