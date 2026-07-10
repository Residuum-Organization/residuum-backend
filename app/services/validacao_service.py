# Este arquivo contém as regras de validação para os dados de entrada do sistema.
TIPOS_RESIDUOS_ACEITOS = {
    "papelao",
    "plastico",
    "metal",
    "papel",
    "cobre",
    "vidro",
    "pilhas",
    "baterias",
    "aluminio"
}

QUANTIDADE_MINIMA = 1
QUANTIDADE_MAXIMA = 1000

def validar_quantidade(quantidade: float) -> bool:
    """
    Valida se a quantidade informada pelo usuário é válida.
    Regras: 
    - Não pode ser zero.
    - Não pode ser negativa.
    - Definimos um limite 'absurdo' de 1000kg para o MVP.
    """
    if quantidade < QUANTIDADE_MINIMA:
        return False
    
    if quantidade > QUANTIDADE_MAXIMA: # Exemplo de valor 'absurdo' para controle manual
        return False
        
    return True

def validar_residuo(tipo_residuo: str) -> bool:
    """
    Valida se o tipo de resíduo é aceito pelo sistema no estágio atual (MVP).
    
    Os tipos aceitos seguem o ENUM definido no banco de dados.
    """
    if not tipo_residuo:
        return False
    
    residuo_formatado = tipo_residuo.strip().lower()
    return residuo_formatado in TIPOS_RESIDUOS_ACEITOS