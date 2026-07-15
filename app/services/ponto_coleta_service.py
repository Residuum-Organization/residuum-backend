"""Regras compartilhadas de ponto de coleta."""

from datetime import datetime

from app.core.exceptions import raise_conflict
from app.models.ponto_coleta import PontoColeta


def total_inventario_ponto(ponto: PontoColeta) -> float:
    """Soma o inventário numérico armazenado no ponto."""
    total = 0.0
    for valor in (ponto.inventario or {}).values():
        try:
            total += float(valor or 0)
        except (TypeError, ValueError):
            continue
    return total


def status_ponto_coleta(ponto: PontoColeta) -> str:
    """Calcula o status operacional visível do ponto."""
    if ponto.ativo == 0 or ponto.status == "inativo":
        return "inativo"

    if ponto.data_final and ponto.data_final.replace(tzinfo=None) < datetime.utcnow():
        return "inativo"

    total = total_inventario_ponto(ponto)
    if ponto.status == "cheio":
        return "cheio"

    if ponto.capacidade_maxima and ponto.capacidade_maxima > 0 and total >= float(ponto.capacidade_maxima):
        return "cheio"

    return ponto.status or "ativo"


def validar_ponto_disponivel_para_descarte(ponto: PontoColeta) -> None:
    """Bloqueia descarte em ponto fora de operação."""
    status_atual = status_ponto_coleta(ponto)
    if status_atual == "inativo":
        if ponto.data_final and ponto.data_final.replace(tzinfo=None) < datetime.utcnow():
            raise_conflict("Ponto de coleta expirado para descarte.")
        raise_conflict("Ponto de coleta inativo para descarte.")

    if status_atual == "cheio":
        raise_conflict("Ponto de coleta cheio no momento.")
