"""add_ondelete_set_null_cooperativa

Revision ID: 1804368d1790
Revises: 24319d505859
Create Date: 2026-07-15 14:16:44.106520

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1804368d1790'
down_revision: Union[str, None] = '24319d505859'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint('fk_ponto_coleta_cooperativa_id_usuario', 'ponto_coleta', type_='foreignkey')
    op.create_foreign_key('fk_ponto_coleta_cooperativa_id_usuario', 'ponto_coleta', 'usuario', ['cooperativa_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_ponto_coleta_cooperativa_id_usuario', 'ponto_coleta', type_='foreignkey')
    op.create_foreign_key('fk_ponto_coleta_cooperativa_id_usuario', 'ponto_coleta', 'usuario', ['cooperativa_id'], ['id'])
