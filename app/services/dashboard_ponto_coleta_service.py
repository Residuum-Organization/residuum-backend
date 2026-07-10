"""Consolidacao de dados para dashboard operacional de ponto de coleta."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.descarte import Descarte
from app.models.ponto_coleta import PontoColeta
from app.services.ponto_coleta_service import status_ponto_coleta, total_inventario_ponto


def _float_seguro(valor) -> float:
    try:
        return float(valor or 0)
    except (TypeError, ValueError):
        return 0.0


def _status_capacidade(percentual_ocupacao: float, capacidade_maxima: float | None) -> str:
    if not capacidade_maxima or capacidade_maxima <= 0:
        return "sem_capacidade_definida"
    if percentual_ocupacao >= 100:
        return "cheio"
    if percentual_ocupacao >= 80:
        return "quase_cheio"
    if percentual_ocupacao >= 60:
        return "atencao"
    return "normal"


def montar_dashboard_ponto_coleta(db: Session, ponto: PontoColeta) -> dict:
    """Monta o retorno consolidado do dashboard com dados seguros para o frontend."""
    inventario = ponto.inventario or {}
    quantidade_total = total_inventario_ponto(ponto)
    capacidade_maxima = _float_seguro(ponto.capacidade_maxima)
    percentual_ocupacao = 0.0

    if capacidade_maxima > 0:
        percentual_ocupacao = round((quantidade_total / capacidade_maxima) * 100, 2)

    volume_por_tipo = [
        {
            "tipo_residuo": str(tipo),
            "quantidade": _float_seguro(quantidade),
        }
        for tipo, quantidade in sorted(inventario.items())
    ]

    usuarios_atendidos = (
        db.query(func.count(func.distinct(Descarte.usuario_id)))
        .filter(
            Descarte.ponto_coleta_id == ponto.id,
            Descarte.status == "confirmado",
            Descarte.usuario_id.is_not(None),
        )
        .scalar()
        or 0
    )

    descartes_pendentes = (
        db.query(func.count(Descarte.id_descarte))
        .filter(
            Descarte.ponto_coleta_id == ponto.id,
            Descarte.status == "pendente",
        )
        .scalar()
        or 0
    )

    descartes_recentes = (
        db.query(Descarte)
        .filter(
            Descarte.ponto_coleta_id == ponto.id,
            Descarte.status == "confirmado",
        )
        .order_by(Descarte.data_desc.desc())
        .limit(10)
        .all()
    )

    historico_recente = [
        {
            "id": descarte.id_descarte,
            "usuario_id": descarte.usuario_id,
            "tipo_residuo": descarte.tipo_residuo,
            "quantidade": _float_seguro(descarte.quantidade_confirmada or descarte.quantidade),
            "status": descarte.status,
            "data": descarte.data_desc,
        }
        for descarte in descartes_recentes
    ]

    return {
        "ponto_id": ponto.id,
        "nome": ponto.nome,
        "endereco": ponto.endereco,
        "status": status_ponto_coleta(ponto),
        "capacidade_maxima": ponto.capacidade_maxima,
        "quantidade_total": round(quantidade_total, 3),
        "percentual_ocupacao": percentual_ocupacao,
        "status_capacidade": _status_capacidade(percentual_ocupacao, capacidade_maxima),
        "volume_por_tipo": volume_por_tipo,
        "usuarios_atendidos": int(usuarios_atendidos),
        "descartes_pendentes": int(descartes_pendentes),
        "historico_recente": historico_recente,
    }
