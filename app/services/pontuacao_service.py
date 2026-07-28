# Este arquivo contém a lógica de cálculo de pontos do sistema Residuum.

def calcular_pontos_proporcionais(quantidade_registrada: float, quantidade_confirmada: float) -> int:
    """
    Calcula a pontuação final do cidadão baseada nas UNIDADES descartadas.
    Regra: O cidadão ganha 10 pontos por cada UNIDADE descartada (ex: 1 unidade = 10 pontos).
    """
    if quantidade_registrada <= 0 or quantidade_confirmada < 0:
        return 0
    
    PONTOS_POR_UNIDADE = 10
    
    pontos_finais = int(quantidade_confirmada * PONTOS_POR_UNIDADE)
    
    return pontos_finais