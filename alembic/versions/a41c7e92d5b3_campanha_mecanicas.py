"""campanha_mecanicas

Revision ID: a41c7e92d5b3
Revises: 5d8e1a7b3c20
Create Date: 2026-10-21 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a41c7e92d5b3'
down_revision = '5d8e1a7b3c20'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'campanha_mecanica',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campanha_id', sa.Integer(), sa.ForeignKey('campanhas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('tipo', sa.String(length=30), nullable=False),
        sa.Column('ativa', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.UniqueConstraint('campanha_id', 'tipo', name='uq_campanha_mecanica_tipo'),
    )
    op.create_index('ix_campanha_mecanica_id', 'campanha_mecanica', ['id'])
    op.create_index('ix_campanha_mecanica_campanha_id', 'campanha_mecanica', ['campanha_id'])
    op.create_table(
        'campanha_bonus',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('inscricao_id', sa.Integer(), sa.ForeignKey('inscricao_campanha.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mecanica', sa.String(length=30), nullable=False),
        sa.Column('pontos', sa.Integer(), nullable=False),
        sa.Column('concedido_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('inscricao_id', 'mecanica', name='uq_campanha_bonus_inscricao_mecanica'),
    )
    op.create_index('ix_campanha_bonus_id', 'campanha_bonus', ['id'])
    op.create_index('ix_campanha_bonus_inscricao_id', 'campanha_bonus', ['inscricao_id'])


def downgrade() -> None:
    op.drop_index('ix_campanha_bonus_inscricao_id', table_name='campanha_bonus')
    op.drop_index('ix_campanha_bonus_id', table_name='campanha_bonus')
    op.drop_table('campanha_bonus')
    op.drop_index('ix_campanha_mecanica_campanha_id', table_name='campanha_mecanica')
    op.drop_index('ix_campanha_mecanica_id', table_name='campanha_mecanica')
    op.drop_table('campanha_mecanica')
