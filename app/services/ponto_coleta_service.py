"""Regras compartilhadas de ponto de coleta."""

from datetime import datetime
import unicodedata

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


def _normalizar_tipo_residuo(tipo_residuo: str) -> str:
    texto = unicodedata.normalize("NFKD", str(tipo_residuo or ""))
    return "".join(caractere for caractere in texto if not unicodedata.combining(caractere)).strip().lower()


def validar_residuo_aceito_no_ponto(ponto: PontoColeta, tipo_residuo: str) -> None:
    """Impede transferências de materiais fora da lista configurada pelo ponto."""
    tipos_aceitos = {
        _normalizar_tipo_residuo(tipo)
        for tipo in (ponto.tipos_residuos_aceitos or [])
        if str(tipo or "").strip()
    }
    if tipos_aceitos and _normalizar_tipo_residuo(tipo_residuo) not in tipos_aceitos:
        raise_conflict("O ponto de coleta selecionado não aceita este tipo de resíduo.")
