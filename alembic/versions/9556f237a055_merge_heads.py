"""merge heads

Revision ID: 9556f237a055
Revises: a12f7c9d3e44, snapshot_inventario_coleta
Create Date: 2026-07-23 10:53:53.306276

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9556f237a055'
down_revision: Union[str, None] = ('a12f7c9d3e44', 'snapshot_inventario_coleta')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
