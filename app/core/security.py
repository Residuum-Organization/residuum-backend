"""
Módulo de Segurança

Este módulo gerencia a autenticação e autorização da aplicação usando JWT (JSON Web Tokens).
Ele fornece funções para criar, verificar tokens e obter o usuário atual a partir do token.
"""

from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import HTTPException, Request, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações para JWT
SECRET_KEY = os.getenv("SECRET_KEY")  # Chave secreta para assinar os tokens
ALGORITHM = "HS256"  # Algoritmo de criptografia usado
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # Tempo de expiração do token de acesso em minutos
# Expiração do refresh token (usado pela função "Lembre de mim" do app).
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

# Valida se a SECRET_KEY foi definida, evitando erros silenciosos
if not SECRET_KEY:
    raise ValueError("SECRET_KEY não foi definida no arquivo .env")

# Esquema de autenticação Bearer para extrair tokens do cabeçalho Authorization
security = HTTPBearer(auto_error=True)


def criar_token(data: dict):
    """
    Cria um token JWT de acesso com os dados fornecidos.

    Adiciona uma data de expiração ao payload e codifica usando a chave secreta.
    Útil para gerar tokens de acesso após login bem-sucedido.
    """
    to_encode = data.copy()  # Copia os dados para não modificar o original

    # Define a expiração e o tipo do token
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})

    # Codifica o payload em um token JWT
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def criar_refresh_token(data: dict):
    """
    Cria um refresh token JWT de longa duração.

    Usado pela função "Lembre de mim" do app: permite renovar o token de
    acesso sem exigir novo login enquanto o refresh token for válido.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verificar_token(token: str):
    """
    Verifica e decodifica um token JWT.

    Retorna o payload se o token for válido, ou lança uma exceção se inválido/expirado.
    Essencial para validar tokens em endpoints protegidos.
    """
    try:
        # Decodifica o token usando a chave secreta
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Lança erro se o token for inválido ou expirado
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )


# Variante opcional do Bearer: não levanta 403 quando o header está ausente,
# permitindo que rotas marcadas com @public passem sem token.
optional_security = HTTPBearer(auto_error=False)


def require_auth_unless_public(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(optional_security),
):
    """
    Dependência global: exige JWT válido em todas as rotas, exceto naquelas
    cujo endpoint foi marcado com o decorator @public.
    """
    endpoint = request.scope.get("endpoint")
    if endpoint is not None and getattr(endpoint, "_is_public", False):
        return None

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação ausente",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verificar_token(credentials.credentials)
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido para esta operação",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Extrai e valida o usuário atual a partir do token JWT no cabeçalho Authorization.

    Dependência do FastAPI para proteger rotas que requerem autenticação.
    Retorna o payload do token se válido, contendo informações do usuário.
    """
    token = credentials.credentials  # Extrai o token das credenciais

    # Verifica o token e obtém o payload
    payload = verificar_token(token)

    # Extrai o ID do usuário do payload (campo 'sub' é padrão para subject)
    user_id = payload.get("sub")

    if user_id is None:
        # Lança erro se o token não contiver o ID do usuário
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    return payload