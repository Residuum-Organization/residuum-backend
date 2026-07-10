"""Regras compartilhadas de ponto de coleta."""

from datetime import datetime

from app.core.exceptions import (
    raise_bad_request,
    raise_conflict,
)
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


def validar_ponto_ativo_com_cooperativa(status_ponto: str, cooperativa_id: int | None) -> None:
    """Impede ponto ativo/cheio sem cooperativa responsável."""
    if status_ponto in {"ativo", "cheio"} and cooperativa_id is None:
        raise_bad_request("Pontos ativos precisam ter uma cooperativa responsável designada.")


def validar_ponto_disponivel_para_descarte(ponto: PontoColeta) -> None:
    """Bloqueia descarte em ponto sem cooperativa ou fora de operação."""
    if ponto.cooperativa_id is None:
        raise_conflict("Ponto de coleta indisponível para descarte até a designação de uma cooperativa responsável.")

    status_atual = status_ponto_coleta(ponto)
    if status_atual == "inativo":
        if ponto.data_final and ponto.data_final.replace(tzinfo=None) < datetime.utcnow():
            raise_conflict("Ponto de coleta expirado para descarte.")
        raise_conflict("Ponto de coleta inativo para descarte.")

    if status_atual == "cheio":
        raise_conflict("Ponto de coleta cheio no momento.")
