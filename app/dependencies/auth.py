"""
Dependências de Autenticação

Este módulo define dependências para autenticação no FastAPI.
Inclui funções para obter o usuário atual a partir do token JWT.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.exceptions import raise_forbidden, raise_not_found
from app.database import get_db
from app.models.ponto_coleta import PontoColeta
from app.models.usuario import Usuario
from app.core.security import verificar_token

# Esquema de segurança Bearer para autenticação
security = HTTPBearer()

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Dependência para obter o usuário atual autenticado.

    Extrai o token do cabeçalho, valida e busca o usuário no banco.
    Lança erro se o token for inválido ou o usuário não existir.
    """
    token = credentials.credentials  # Token do cabeçalho Authorization

    # Verifica e decodifica o token
    payload = verificar_token(token)

    # Refresh tokens não autenticam rotas normais; só servem para renovar acesso.
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido para esta operação",
        )

    # Extrai o ID do usuário do payload
    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    # Busca o usuário no banco de dados
    usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado"
        )

    return usuario


def require_role(*roles: str):
    """
    Fábrica de dependência: garante que o usuário autenticado tenha
    um dos papéis informados. Use como Depends(require_role("admin")).
    """
    allowed = set(roles)

    def _checker(usuario: Usuario = Depends(get_current_user)) -> Usuario:
        if usuario.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão insuficiente",
            )
        return usuario

    return _checker


def validar_acesso_operacional_ao_ponto(usuario: Usuario, ponto: PontoColeta | None) -> PontoColeta:
    """Garante que apenas admin ou a cooperativa designada operem um ponto."""
    if not ponto:
        raise_not_found("Ponto de coleta não encontrado.")

    if usuario.role == "admin":
        return ponto

    if usuario.role == "cooperativa" and ponto.cooperativa_id == usuario.id:
        return ponto

    raise_forbidden("Permissão insuficiente para operar este ponto de coleta")
