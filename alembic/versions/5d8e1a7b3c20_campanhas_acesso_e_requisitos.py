"""campanhas_acesso_e_requisitos

Revision ID: 5d8e1a7b3c20
Revises: 3b1f6d2a9c47
Create Date: 2026-10-21 16:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5d8e1a7b3c20'
down_revision = '3b1f6d2a9c47'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Substituídos pelos requisitos estruturados (campanha_requisito).
    op.drop_column('campanhas', 'produto_elegivel')
    op.drop_column('campanhas', 'meta_quantidade')
    op.add_column(
        'campanhas',
        sa.Column('acesso', sa.String(length=20), nullable=False, server_default='publica'),
    )
    op.add_column(
        'inscricao_campanha',
        sa.Column('recompensa_concedida_em', sa.DateTime(timezone=True), nullable=True),
    )
    # Adesões antigas já receberam os pontos na hora: marcar como pagas evita pagar de novo.
    op.execute(
        "UPDATE inscricao_campanha SET recompensa_concedida_em = criado_em "
        "WHERE pontos_concedidos > 0"
    )
    op.create_table(
        'campanha_requisito',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('campanha_id', sa.Integer(), sa.ForeignKey('campanhas.id', ondelete='CASCADE'), nullable=False),
        sa.Column('papel', sa.String(length=20), nullable=False),
        sa.Column('descricao', sa.String(length=255), nullable=True),
        sa.Column('tipo_residuo', sa.String(length=50), nullable=True),
        sa.Column('codigos_barras', sa.JSON(), nullable=True),
        sa.Column('quantidade', sa.Integer(), nullable=False),
    )
    op.create_index('ix_campanha_requisito_id', 'campanha_requisito', ['id'])
    op.create_index('ix_campanha_requisito_campanha_id', 'campanha_requisito', ['campanha_id'])


def downgrade() -> None:
    op.drop_index('ix_campanha_requisito_campanha_id', table_name='campanha_requisito')
    op.drop_index('ix_campanha_requisito_id', table_name='campanha_requisito')
    op.drop_table('campanha_requisito')
    op.drop_column('inscricao_campanha', 'recompensa_concedida_em')
    op.drop_column('campanhas', 'acesso')
    op.add_column('campanhas', sa.Column('meta_quantidade', sa.Integer(), nullable=True))
    op.add_column('campanhas', sa.Column('produto_elegivel', sa.String(length=255), nullable=True))
