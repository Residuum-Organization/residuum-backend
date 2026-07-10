"""Adiciona inventário de resíduos do usuário

Revision ID: task11_inventario_usuario
Revises: rf013_ponto_coleta_qrcode
Create Date: 2026-05-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "task11_inventario_usuario"
down_revision: Union[str, None] = "rf013_ponto_coleta_qrcode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inventario_usuario",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("tipo_residuo", sa.String(length=50), nullable=False),
        sa.Column("quantidade", sa.Float(), server_default="0", nullable=False),
        sa.Column("quantidade_reservada", sa.Float(), server_default="0", nullable=False),
        sa.Column("descricao", sa.String(length=255), nullable=True),
        sa.Column("observacao", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="disponivel", nullable=False),
        sa.Column("data_cadastro", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column("data_atualizacao", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inventario_usuario_id"), "inventario_usuario", ["id"], unique=False)
    op.create_index(op.f("ix_inventario_usuario_usuario_id"), "inventario_usuario", ["usuario_id"], unique=False)

    op.add_column("descarte", sa.Column("inventario_usuario_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_descarte_inventario_usuario",
        "descarte",
        "inventario_usuario",
        ["inventario_usuario_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_descarte_inventario_usuario", "descarte", type_="foreignkey")
    op.drop_column("descarte", "inventario_usuario_id")

    op.drop_index(op.f("ix_inventario_usuario_usuario_id"), table_name="inventario_usuario")
    op.drop_index(op.f("ix_inventario_usuario_id"), table_name="inventario_usuario")
    op.drop_table("inventario_usuario")
