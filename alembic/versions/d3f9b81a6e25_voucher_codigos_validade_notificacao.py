"""voucher_codigos_validade_notificacao

Revision ID: d3f9b81a6e25
Revises: c7a2e5b9d140
Create Date: 2026-10-22 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd3f9b81a6e25'
down_revision = 'c7a2e5b9d140'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('vouchers', sa.Column('instrucoes', sa.Text(), nullable=True))
    op.add_column('vouchers', sa.Column('validade_codigo_dias', sa.Integer(), nullable=True))

    op.add_column(
        'resgate_voucher',
        sa.Column('valido_ate', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'voucher_codigo',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('voucher_id', sa.Integer(), sa.ForeignKey('vouchers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('codigo', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='disponivel'),
        sa.Column('resgate_id', sa.Integer(), sa.ForeignKey('resgate_voucher.id'), nullable=True),
        sa.Column('criado_em', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_voucher_codigo_id', 'voucher_codigo', ['id'])
    op.create_index('ix_voucher_codigo_voucher_id', 'voucher_codigo', ['voucher_id'])
    op.create_index('ix_voucher_codigo_codigo', 'voucher_codigo', ['codigo'], unique=True)

    op.add_column('notificacoes', sa.Column('usuario_id', sa.Integer(), sa.ForeignKey('usuario.id'), nullable=True))
    op.create_index('ix_notificacoes_usuario_id', 'notificacoes', ['usuario_id'])


def downgrade() -> None:
    op.drop_index('ix_notificacoes_usuario_id', table_name='notificacoes')
    op.drop_column('notificacoes', 'usuario_id')
    op.drop_index('ix_voucher_codigo_codigo', table_name='voucher_codigo')
    op.drop_index('ix_voucher_codigo_voucher_id', table_name='voucher_codigo')
    op.drop_index('ix_voucher_codigo_id', table_name='voucher_codigo')
    op.drop_table('voucher_codigo')
    op.drop_column('resgate_voucher', 'valido_ate')
    op.drop_column('vouchers', 'validade_codigo_dias')
    op.drop_column('vouchers', 'instrucoes')
