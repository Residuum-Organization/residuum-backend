# Este arquivo contém a lógica de cálculo de pontos do sistema Residuum.

def calcular_pontos_proporcionais(quantidade_registrada: float, quantidade_confirmada: float) -> int:
    """
    Calcula a pontuação final baseada na conferência da cooperativa.
    Regra: O usuário ganha 10 pontos por kg confirmado.
    Se a cooperativa confirmar menos do que o usuário declarou, 
    os pontos são gerados apenas sobre o peso real (confirmado).
    """
    if quantidade_registrada <= 0 or quantidade_confirmada < 0:
        return 0
    
    # Se a cooperativa confirmar mais do que o registrado, limitamos ao registrado
    # ou usamos o confirmado como base real (depende da regra de negócio).
    # Aqui usaremos a quantidade confirmada como a verdade absoluta.
    
    PONTOS_POR_KG = 10 # Regra de exemplo: 10 pontos para cada 1kg de PET
    
    pontos_finais = int(quantidade_confirmada * PONTOS_POR_KG)
    
    return pontos_finais