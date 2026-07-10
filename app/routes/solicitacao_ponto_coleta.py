"""Rotas para solicitacao de cadastro de ponto de coleta."""

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.solicitacao_ponto_coleta import SolicitacaoPontoColeta
from app.models.usuario import Usuario
from app.schemas.solicitacao_ponto_coleta import (
    SolicitacaoPontoColetaCreate,
    SolicitacaoPontoColetaResponse,
)

router = APIRouter()


STATUS_PENDENTE = "pendente"


def _normalizar_tipos_residuos(tipos: List[str]) -> List[str]:
    return [str(tipo).strip().lower() for tipo in tipos if str(tipo).strip()]


@router.post(
    "/solicitacoes-pontos-coleta",
    response_model=SolicitacaoPontoColetaResponse,
    tags=["Solicitacoes de Ponto de Coleta"],
)
async def criar_solicitacao_ponto_coleta(
    obj_in: SolicitacaoPontoColetaCreate,
    db: Session = Depends(get_db),
    usuario_atual: Usuario = Depends(get_current_user),
):
    """Cria uma solicitacao pendente sem ativar um ponto de coleta."""
    solicitacao = SolicitacaoPontoColeta(
        usuario_id=usuario_atual.id,
        tipo_solicitante=obj_in.tipo_solicitante,
        documento=obj_in.documento,
        responsavel_nome=obj_in.responsavel_nome,
        responsavel_telefone=obj_in.responsavel_telefone,
        email=obj_in.email,
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
