"""Adiciona PontoColeta e QRCodeToken, e atualiza Descarte

Revision ID: rf013_ponto_coleta_qrcode
Revises: 60d9ec0c960e
Create Date: 2026-05-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'rf013_ponto_coleta_qrcode'
down_revision: Union[str, None] = '60d9ec0c960e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Criar tabela ponto_coleta
    op.create_table('ponto_coleta',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('nome', sa.String(length=255), nullable=False),
    sa.Column('endereco', sa.String(length=500), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('raio_operacao', sa.Float(), server_default='1000.0', nullable=True),
    sa.Column('inventario', sa.JSON(), server_default='{}', nullable=True),
    sa.Column('data_criacao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('data_atualizacao', sa.DateTime(timezone=True), onupdate=sa.func.now(), server_default=sa.func.now(), nullable=True),
    sa.Column('ativo', sa.Integer(), server_default='1', nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ponto_coleta_id'), 'ponto_coleta', ['id'], unique=False)

    # Criar tabela qrcode_token
    op.create_table('qrcode_token',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('token', sa.String(length=36), nullable=False),
    sa.Column('ponto_coleta_id', sa.Integer(), nullable=False),
    sa.Column('data_geracao', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    sa.Column('data_expiracao', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ativo', sa.Integer(), server_default='1', nullable=True),
    sa.Column('descarte_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['ponto_coleta_id'], ['ponto_coleta.id'], ),
    sa.ForeignKeyConstraint(['descarte_id'], ['descarte.id_descarte'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )
    op.create_index(op.f('ix_qrcode_token_id'), 'qrcode_token', ['id'], unique=False)
    op.create_index(op.f('ix_qrcode_token_token'), 'qrcode_token', ['token'], unique=False)

    # Atualizar tabela descarte para adicionar colunas
    op.add_column('descarte', sa.Column('ponto_coleta_id', sa.Integer(), nullable=True))
    op.add_column('descarte', sa.Column('qrcode_token_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_descarte_ponto_coleta', 'descarte', 'ponto_coleta', ['ponto_coleta_id'], ['id'])
    op.create_foreign_key('fk_descarte_qrcode_token', 'descarte', 'qrcode_token', ['qrcode_token_id'], ['id'])


def downgrade() -> None:
    # Remover foreign keys e colunas da tabela descarte
    op.drop_constraint('fk_descarte_qrcode_token', 'descarte', type_='foreignkey')
    op.drop_constraint('fk_descarte_ponto_coleta', 'descarte', type_='foreignkey')
    op.drop_column('descarte', 'qrcode_token_id')
    op.drop_column('descarte', 'ponto_coleta_id')

    # Remover tabelas
    op.drop_index(op.f('ix_qrcode_token_token'), table_name='qrcode_token')
    op.drop_index(op.f('ix_qrcode_token_id'), table_name='qrcode_token')
    op.drop_table('qrcode_token')
    
    op.drop_index(op.f('ix_ponto_coleta_id'), table_name='ponto_coleta')
    op.drop_table('ponto_coleta')
