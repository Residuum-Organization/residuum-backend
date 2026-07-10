import math

# Este arquivo contém a lógica para verificar a proximidade do usuário ao ponto de coleta.

def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula a distância geodésica entre dois pontos na superfície da Terra
    (especificados em latitude e longitude) em metros.
    """
    # Raio médio da Terra em metros
    R = 6371000.0

    # Conversão de graus para radianos
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Fórmula de Haversine
    a = math.sin(delta_phi / 2) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    # Distância em metros
    return R * c

def validar_localizacao(user_lat: float, user_long: float, ponto_lat: float, ponto_long: float, raio_metros: float = 1000.0) -> bool:
    """
    Verifica se o usuário está próximo o suficiente do ponto de coleta para descartar.
    Usa a distância de Haversine para precisão real em metros.
    O raio padrão é de 1000 metros (1km).
    """
    distancia_metros = calcular_distancia_haversine(user_lat, user_long, ponto_lat, ponto_long)
    return distancia_metros <= raio_metros
