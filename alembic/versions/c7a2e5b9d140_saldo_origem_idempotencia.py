"""saldo_origem_idempotencia

Revision ID: c7a2e5b9d140
Revises: a41c7e92d5b3
Create Date: 2026-10-22 09:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c7a2e5b9d140'
down_revision = 'a41c7e92d5b3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'resgate_pontuacao',
        sa.Column('origem', sa.String(length=20), nullable=False, server_default='resgate'),
    )
    # Eventos antigos: a origem sai do texto que as rotas ja gravavam.
    op.execute(
        "UPDATE resgate_pontuacao SET origem = 'sorteio' "
        "WHERE referencia LIKE 'sorteio:%'"
    )
    op.execute(
        "UPDATE resgate_pontuacao SET origem = 'voucher' "
        "WHERE descricao LIKE 'Resgate de voucher:%'"
    )

    op.add_column(
        'resgate_voucher',
        sa.Column('chave_idempotencia', sa.String(length=80), nullable=True),
    )
    op.create_unique_constraint(
        'uq_resgate_voucher_chave', 'resgate_voucher', ['usuario_id', 'chave_idempotencia']
    )

    op.add_column(
        'bilhete_sorteio',
        sa.Column('chave_idempotencia', sa.String(length=80), nullable=True),
    )
    op.create_unique_constraint(
        'uq_bilhete_sorteio_chave', 'bilhete_sorteio', ['usuario_id', 'chave_idempotencia']
    )


def downgrade() -> None:
    op.drop_constraint('uq_bilhete_sorteio_chave', 'bilhete_sorteio', type_='unique')
    op.drop_column('bilhete_sorteio', 'chave_idempotencia')
    op.drop_constraint('uq_resgate_voucher_chave', 'resgate_voucher', type_='unique')
    op.drop_column('resgate_voucher', 'chave_idempotencia')
    op.drop_column('resgate_pontuacao', 'origem')
