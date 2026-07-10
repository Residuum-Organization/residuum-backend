"""Rotas de metricas/analytics do proprio usuario autenticado."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.descarte import Descarte
from app.models.usuario import Usuario

router = APIRouter(prefix="/usuario", tags=["Métricas do Usuário"])


@router.get("/metricas")
def metricas_usuario(
    ano: int = Query(
        default_factory=lambda: datetime.utcnow().year,
        ge=2000,
        le=2100,
        description="Ano de referência para o gráfico de entregas.",
    ),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Consolida os descartes confirmados do usuário para o dashboard.

    Retorna a soma de kg confirmados por mês (todos os 12 meses do ano,
    preenchidos com zero quando não houver entregas) para alimentar o
    gráfico de "Entregas do Ano" na tela inicial do morador.
    """
    linhas = (
        db.query(
            extract("month", Descarte.data_desc).label("mes"),
            func.coalesce(func.sum(Descarte.quantidade_confirmada), 0).label("kg"),
            func.count(Descarte.id_descarte).label("qtd"),
        )
        .filter(
            Descarte.usuario_id == usuario.id,
            Descarte.status == "confirmado",
            extract("year", Descarte.data_desc) == ano,
        )
        .group_by(extract("month", Descarte.data_desc))
        .all()
    )

    por_mes_map = {int(mes): (float(kg or 0), int(qtd)) for mes, kg, qtd in linhas}
    por_mes = [
        {
            "mes": mes,
            "kg": round(por_mes_map.get(mes, (0.0, 0))[0], 3),
            "descartes": por_mes_map.get(mes, (0.0, 0))[1],
        }
        for mes in range(1, 13)
    ]

    total_kg_ano = round(sum(item["kg"] for item in por_mes), 3)
    total_descartes_ano = sum(item["descartes"] for item in por_mes)

    return {
        "ano": ano,
        "total_kg_ano": total_kg_ano,
        "total_descartes_ano": total_descartes_ano,
        "pontuacao_total": usuario.pontuacao_total or 0,
        "por_mes": por_mes,
    }
