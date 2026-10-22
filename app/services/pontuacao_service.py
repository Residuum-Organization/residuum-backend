# Este arquivo contém a lógica de cálculo de pontos do sistema Residuum.

# Regra inicial informada pelo time em 2026-10-22: 1 descarte (unidade) = 5 pontos.
# Substitui os 10 pontos da V6 e do código anterior (AUD-002). Pontos já
# creditados não são recalculados.
PONTOS_POR_UNIDADE = 5


def calcular_pontos_proporcionais(quantidade_registrada: float, quantidade_confirmada: float) -> int:
    """
    Calcula a pontuação final do cidadão baseada nas UNIDADES descartadas.
    Regra: O cidadão ganha PONTOS_POR_UNIDADE pontos por cada UNIDADE descartada
    (hoje, 1 unidade = 5 pontos).
    """
    if quantidade_registrada <= 0 or quantidade_confirmada < 0:
        return 0

    pontos_finais = int(quantidade_confirmada * PONTOS_POR_UNIDADE)

    return pontos_finais
