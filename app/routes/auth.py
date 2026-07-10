"""
Rotas de Autenticação

Este módulo define as rotas para autenticação: cadastro de usuários, login e perfil do usuário logado.
Usa hashing de senha com bcrypt e JWT para tokens.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from app.database import get_db
from app.models.usuario import Usuario
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.schemas.usuario import UsuarioCreate, UsuarioUpdate
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    TokenResponse,
)

from app.core.security import criar_refresh_token, criar_token, verificar_token
from app.core.decorators import public
from app.dependencies.auth import get_current_user
from app.services.serializacao_service import (
    serializar_usuario_basico,
    serializar_inventario_item,
    serializar_descarte,
)
from app.services.extrato_pontos_service import montar_extrato_pontos_usuario

# Roteador para agrupar as rotas de autenticação
router = APIRouter(tags=["Autenticação"])

# Contexto para hashing de senhas usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str):
    """
    Gera um hash seguro para a senha usando bcrypt.
    Limita a senha a 72 caracteres para compatibilidade.
    """
    return pwd_context.hash(senha[:72])


def verificar_senha(senha: str, hash: str):
    """
    Verifica se a senha corresponde ao hash armazenado.
    """
    return pwd_context.verify(senha[:72], hash)


# ========================
# CADASTRO DE USUÁRIO
# ========================
@router.post("/usuarios")
@public
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """
    Cria um novo usuário no sistema apenas com credenciais e dados pessoais.

    O endereço é cadastrado posteriormente via PUT /me/endereco.
    """
    usuario_existente = db.query(Usuario).filter(Usuario.email == usuario.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo_usuario = Usuario(
        nome=usuario.nome,
        email=usuario.email,
        telefone=usuario.telefone,
        senha_hash=hash_senha(usuario.senha),
    )

    db.add(novo_usuario)
    db.commit()
    db.refresh(novo_usuario)

    return {"msg": "Usuário criado com sucesso"}


# ========================
# LOGIN
# ========================
@router.post("/login", response_model=TokenResponse)
@public
def login(dados: LoginRequest = Body(...), db: Session = Depends(get_db)):
    """
    Realiza o login do usuário.

    Verifica email e senha, e retorna um token JWT se válido.
    """
    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()

    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )

    if not verificar_senha(dados.senha, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )

    dados_token = {
        "sub": str(usuario.id),
        "email": usuario.email,
    }
    token = criar_token(dados_token)
    refresh = criar_refresh_token({"sub": str(usuario.id)})

    return {
        "access_token": token,
        "refresh_token": refresh,
        "token_type": "bearer",
        "usuario_id": usuario.id,
    }


# ========================
# REFRESH TOKEN
# ========================
@router.post("/refresh", response_model=RefreshResponse)
@public
def refresh_token(dados: RefreshRequest = Body(...), db: Session = Depends(get_db)):
    """
    Renova o token de acesso a partir de um refresh token válido.

    Suporta a função "Lembre de mim" do app, mantendo o usuário logado sem
    exigir novo login. Faz rotação do refresh token a cada renovação.
    """
    payload = verificar_token(dados.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
        )

    usuario = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    novo_access = criar_token({"sub": str(usuario.id), "email": usuario.email})
    novo_refresh = criar_refresh_token({"sub": str(usuario.id)})

    return {
        "access_token": novo_access,
        "refresh_token": novo_refresh,
        "token_type": "bearer",
    }


# ========================
# PERFIL DO USUÁRIO LOGADO
# ========================
@router.get("/me")
def get_me(usuario: Usuario = Depends(get_current_user)):
    """
    Retorna os dados básicos do usuário autenticado.

    Requer token válido no cabeçalho Authorization.
    """
    return serializar_usuario_basico(usuario)


@router.put("/me")
def atualizar_me(
    dados: UsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Atualiza apenas os dados basicos do usuario autenticado.

    Nao altera endereco, senha, role, ID ou pontuacao.
    """
    if dados.email is not None and dados.email != usuario.email:
        email_existente = (
            db.query(Usuario)
            .filter(Usuario.email == dados.email, Usuario.id != usuario.id)
            .first()
        )
        if email_existente:
            raise HTTPException(status_code=400, detail="Email ja cadastrado")
        usuario.email = dados.email

    if dados.nome is not None:
        usuario.nome = dados.nome

    if dados.telefone is not None:
        usuario.telefone = dados.telefone

    db.commit()
    db.refresh(usuario)

    return serializar_usuario_basico(usuario)


@router.get("/perfil")
def get_perfil(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    RF006 - Perfil completo do usuário autenticado.

    Retorna em uma única resposta:
    - dados pessoais e endereço;
    - pontuação total;
    - resíduos cadastrados no inventário;
    - histórico resumido de descartes;
    - descartes pendentes.
    """
    inventario_ativo = (
        db.query(InventarioUsuario)
        .filter(
            InventarioUsuario.usuario_id == usuario.id,
            InventarioUsuario.status != "cancelado",
        )
        .order_by(InventarioUsuario.data_cadastro.desc())
        .all()
    )

    historico_resumido = (
        db.query(Descarte)
        .filter(Descarte.usuario_id == usuario.id)
        .order_by(Descarte.data_desc.desc())
        .limit(5)
        .all()
    )

    descartes_pendentes = (
        db.query(Descarte)
        .filter(
            Descarte.usuario_id == usuario.id,
            Descarte.status == "pendente",
        )
        .order_by(Descarte.data_desc.desc())
        .all()
    )

    total_itens_inventario = len(inventario_ativo)
    quantidade_total_inventario = sum(float(item.quantidade or 0) for item in inventario_ativo)
    quantidade_disponivel_inventario = sum(
        max(float(item.quantidade or 0) - float(item.quantidade_reservada or 0), 0)
        for item in inventario_ativo
    )
    quantidade_reservada_inventario = sum(
        float(item.quantidade_reservada or 0) for item in inventario_ativo
    )

    return {
        **serializar_usuario_basico(usuario),
        "usuario": serializar_usuario_basico(usuario),
        "resumo": {
            "pontuacao_total": usuario.pontuacao_total or 0,
            "total_itens_inventario": total_itens_inventario,
            "quantidade_total_inventario": quantidade_total_inventario,
            "quantidade_disponivel_inventario": quantidade_disponivel_inventario,
            "quantidade_reservada_inventario": quantidade_reservada_inventario,
            "total_descartes_resumidos": len(historico_resumido),
            "total_descartes_pendentes": len(descartes_pendentes),
        },
        "inventario": [serializar_inventario_item(item) for item in inventario_ativo],
        "historico_resumido": [serializar_descarte(descarte, db) for descarte in historico_resumido],
        "descartes_pendentes": [serializar_descarte(descarte, db) for descarte in descartes_pendentes],
        "extrato_pontos_resumido": montar_extrato_pontos_usuario(usuario, db, limit=5)["itens"],
    }
