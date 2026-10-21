"""add_condicoes_to_campanhas

Revision ID: 3b1f6d2a9c47
Revises: c8b2c451f28b
Create Date: 2026-10-21 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b1f6d2a9c47'
down_revision = 'c8b2c451f28b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('campanhas', sa.Column('produto_elegivel', sa.String(length=255), nullable=True))
    op.add_column('campanhas', sa.Column('meta_quantidade', sa.Integer(), nullable=True))
    op.add_column('campanhas', sa.Column('condicoes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('campanhas', 'condicoes')
    op.drop_column('campanhas', 'meta_quantidade')
    op.drop_column('campanhas', 'produto_elegivel')
