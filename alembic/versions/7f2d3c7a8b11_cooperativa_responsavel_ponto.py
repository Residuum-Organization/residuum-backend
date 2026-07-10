"""cooperativa_responsavel_ponto

Revision ID: 7f2d3c7a8b11
Revises: d9eaeed7d61a
Create Date: 2026-06-19 00:00:00.000000

"""
from typing import Sequence, Union
from datetime import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7f2d3c7a8b11"
down_revision: Union[str, None] = "d9eaeed7d61a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("ponto_coleta", sa.Column("cooperativa_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_ponto_coleta_cooperativa_id"), "ponto_coleta", ["cooperativa_id"], unique=False)
    op.create_foreign_key(
        "fk_ponto_coleta_cooperativa_id_usuario",
        "ponto_coleta",
        "usuario",
        ["cooperativa_id"],
        ["id"],
    )

    bind = op.get_bind()
    usuario = sa.table(
        "usuario",
        sa.column("id", sa.Integer()),
        sa.column("role", sa.String()),
    )
    ponto_coleta = sa.table(
        "ponto_coleta",
        sa.column("id", sa.Integer()),
        sa.column("ativo", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("data_final", sa.DateTime(timezone=True)),
        sa.column("cooperativa_id", sa.Integer()),
    )

    cooperativas = bind.execute(
        sa.select(usuario.c.id)
        .where(usuario.c.role == "cooperativa")
        .order_by(usuario.c.id)
    ).scalars().all()

    if len(cooperativas) == 1:
        bind.execute(
            sa.update(ponto_coleta)
            .where(ponto_coleta.c.cooperativa_id.is_(None))
            .values(cooperativa_id=cooperativas[0])
        )
    else:
        pontos_sem_cooperativa = bind.execute(
            sa.select(sa.func.count())
            .select_from(ponto_coleta)
            .where(ponto_coleta.c.cooperativa_id.is_(None))
            .where(ponto_coleta.c.ativo == 1)
            .where(ponto_coleta.c.status != "inativo")
            .where(
                sa.or_(
                    ponto_coleta.c.data_final.is_(None),
                    ponto_coleta.c.data_final > datetime.utcnow(),
                )
            )
        ).scalar_one()

        if pontos_sem_cooperativa:
            raise RuntimeError(
                "Migracao bloqueada: existem pontos de coleta ativos sem cooperativa responsavel e nao foi possivel fazer backfill automatico. Reatribua manualmente os pontos antes de aplicar esta migracao."
            )


def downgrade() -> None:
    op.drop_constraint("fk_ponto_coleta_cooperativa_id_usuario", "ponto_coleta", type_="foreignkey")
    op.drop_index(op.f("ix_ponto_coleta_cooperativa_id"), table_name="ponto_coleta")
    op.drop_column("ponto_coleta", "cooperativa_id")
