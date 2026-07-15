"""Rotas para solicitacao de cadastro de ponto de coleta."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_conflict
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.solicitacao_ponto_coleta import SolicitacaoPontoColeta
from app.models.usuario import Usuario
from app.schemas.solicitacao_ponto_coleta import (
    SolicitacaoPontoColetaCreate,
    SolicitacaoPontoColetaResponse,
)
from app.services.password_service import hash_senha

router = APIRouter()


STATUS_PENDENTE = "pendente"


def _normalizar_tipos_residuos(tipos: List[str]) -> List[str]:
    return [str(tipo).strip().lower() for tipo in tipos if str(tipo).strip()]


@router.post(
    "/solicitacoes-pontos-coleta",
    response_model=SolicitacaoPontoColetaResponse,
    tags=["Solicitacoes de Ponto de Coleta"],
)
@public
async def criar_solicitacao_ponto_coleta(
    obj_in: SolicitacaoPontoColetaCreate,
    db: Session = Depends(get_db),
):
    """Cria uma solicitacao publica sem criar uma conta de usuario."""
    usuario_existente = db.query(Usuario.id).filter(Usuario.email == obj_in.email).first()
    if usuario_existente:
        raise_conflict("Ja existe uma conta cadastrada com este e-mail.")
    solicitacao_pendente = (
        db.query(SolicitacaoPontoColeta.id)
        .filter(
            SolicitacaoPontoColeta.email == obj_in.email,
            SolicitacaoPontoColeta.status == STATUS_PENDENTE,
        )
        .first()
    )
    if solicitacao_pendente:
        raise_conflict("Ja existe uma solicitacao pendente para este e-mail.")

    solicitacao = SolicitacaoPontoColeta(
        usuario_id=None,
        tipo_solicitante=obj_in.tipo_solicitante,
        documento=obj_in.documento,
        responsavel_nome=obj_in.responsavel_nome,
        responsavel_telefone=obj_in.responsavel_telefone,
        email=obj_in.email,
        senha_hash=hash_senha(obj_in.senha),
        nome_ponto=obj_in.nome_ponto,
        endereco=obj_in.endereco,
        latitude=obj_in.latitude,
        longitude=obj_in.longitude,
        horario_funcionamento=obj_in.horario_funcionamento,
        tipos_residuos_aceitos=_normalizar_tipos_residuos(obj_in.tipos_residuos_aceitos),
        capacidade_maxima=obj_in.capacidade_maxima,
        status=STATUS_PENDENTE,
    )

    db.add(solicitacao)
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


@router.get(
    "/solicitacoes-pontos-coleta/minha",
    response_model=List[SolicitacaoPontoColetaResponse],
    tags=["Solicitacoes de Ponto de Coleta"],
)
async def listar_minhas_solicitacoes_pontos_coleta(
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """Lista somente as solicitacoes criadas pelo usuario autenticado."""
    return (
        db.query(SolicitacaoPontoColeta)
        .filter(SolicitacaoPontoColeta.usuario_id == usuario_atual.id)
        .order_by(SolicitacaoPontoColeta.criado_em.desc(), SolicitacaoPontoColeta.id.desc())
        .all()
    )
