"""Add residue identification, GPS accuracy and transfer batches.

Revision ID: a12f7c9d3e44
Revises: 4d7a9c2e1f30
Create Date: 2026-07-17 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a12f7c9d3e44"
down_revision: Union[str, None] = "4d7a9c2e1f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("inventario_usuario", sa.Column("codigo_barras", sa.String(length=64), nullable=True))
    op.add_column(
        "inventario_usuario",
        sa.Column("sem_rotulo", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.execute(
        sa.text(
            "UPDATE inventario_usuario "
            "SET sem_rotulo = true "
            "WHERE codigo_barras IS NULL"
        )
    )
    op.create_check_constraint(
        "ck_inventario_usuario_identificacao",
        "inventario_usuario",
        "(sem_rotulo = true AND codigo_barras IS NULL) OR "
        "(sem_rotulo = false AND codigo_barras IS NOT NULL AND length(trim(codigo_barras)) > 0)",
    )

    op.create_table(
        "transferencia_lote",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("ponto_coleta_id", sa.Integer(), nullable=False),
        sa.Column("chave_idempotencia", sa.String(length=128), nullable=False),
        sa.Column("usuario_lat", sa.Float(), nullable=False),
        sa.Column("usuario_long", sa.Float(), nullable=False),
        sa.Column("usuario_precisao", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="pendente", nullable=False),
        sa.Column("total_itens", sa.Integer(), nullable=False),
        sa.Column("peso_total", sa.Float(), nullable=False),
        sa.Column("pontos_estimados", sa.Integer(), nullable=False),
        sa.Column("data_criacao", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["ponto_coleta_id"], ["ponto_coleta.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "usuario_id",
            "chave_idempotencia",
            name="uq_transferencia_lote_usuario_idempotencia",
        ),
    )
    op.create_index(
        op.f("ix_transferencia_lote_usuario_id"),
        "transferencia_lote",
        ["usuario_id"],
        unique=False,
    )

    op.alter_column(
        "descarte",
        "observacao",
        existing_type=sa.String(length=50),
        type_=sa.String(length=500),
        existing_nullable=True,
    )
    op.add_column("descarte", sa.Column("usuario_precisao", sa.Float(), nullable=True))
    op.add_column("descarte", sa.Column("codigo_barras_validado", sa.String(length=64), nullable=True))
    op.add_column(
        "descarte",
        sa.Column("sem_rotulo_validado", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column("descarte", sa.Column("identificacao_manual", sa.String(length=255), nullable=True))
    op.add_column("descarte", sa.Column("identificado_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("descarte", sa.Column("identificado_por_id", sa.Integer(), nullable=True))
    op.add_column("descarte", sa.Column("transferencia_lote_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_descarte_identificado_por",
        "descarte",
        "usuario",
        ["identificado_por_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_descarte_transferencia_lote",
        "descarte",
        "transferencia_lote",
        ["transferencia_lote_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_descarte_transferencia_lote_id"),
        "descarte",
        ["transferencia_lote_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_descarte_transferencia_lote_id"), table_name="descarte")
    op.drop_constraint("fk_descarte_transferencia_lote", "descarte", type_="foreignkey")
    op.drop_constraint("fk_descarte_identificado_por", "descarte", type_="foreignkey")
    op.drop_column("descarte", "transferencia_lote_id")
    op.drop_column("descarte", "identificado_por_id")
    op.drop_column("descarte", "identificado_em")
    op.drop_column("descarte", "identificacao_manual")
    op.drop_column("descarte", "sem_rotulo_validado")
    op.drop_column("descarte", "codigo_barras_validado")
    op.drop_column("descarte", "usuario_precisao")
    op.alter_column(
        "descarte",
        "observacao",
        existing_type=sa.String(length=500),
        type_=sa.String(length=50),
        existing_nullable=True,
    )

    op.drop_index(op.f("ix_transferencia_lote_usuario_id"), table_name="transferencia_lote")
    op.drop_table("transferencia_lote")
    op.drop_constraint(
        "ck_inventario_usuario_identificacao",
        "inventario_usuario",
        type_="check",
    )
    op.drop_column("inventario_usuario", "sem_rotulo")
    op.drop_column("inventario_usuario", "codigo_barras")
