from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import require_role, validar_acesso_operacional_ao_ponto
from app.models.descarte import Descarte
from app.models.ponto_coleta import PontoColeta
from app.models.solicitacao_coleta import SolicitacaoColeta
from app.models.usuario import Usuario
from app.schemas.admin import RejeitarDescarteRequest
from app.schemas.solicitacao_coleta import (
    SolicitacaoColetaRecusar,
    SolicitacaoColetaResponse,
    SolicitacaoColetaConcluir,
)
from app.services.descarte_service import rejeitar_descarte_pendente


router = APIRouter(
    prefix="/cooperativa",
    tags=["Cooperativa"],
)


@router.get("/solicitacoes-coleta", response_model=list[SolicitacaoColetaResponse])
def listar_solicitacoes_coleta(
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    """Lista solicitações encaminhadas à cooperativa autenticada."""
    return (
        db.query(SolicitacaoColeta)
        .filter(SolicitacaoColeta.cooperativa_id == cooperativa.id)
        .order_by(SolicitacaoColeta.data_solicitacao.desc())
        .all()
    )


@router.post(
    "/solicitacoes-coleta/{solicitacao_id}/aceitar",
    response_model=SolicitacaoColetaResponse,
)
def aceitar_solicitacao_coleta(
    solicitacao_id: int,
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    solicitacao = (
        db.query(SolicitacaoColeta)
        .filter(
            SolicitacaoColeta.id == solicitacao_id,
            SolicitacaoColeta.cooperativa_id == cooperativa.id,
        )
        .first()
    )
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação de coleta não encontrada")
    if solicitacao.status != "solicitada":
        raise HTTPException(status_code=409, detail="A solicitação não está disponível para aceite")

    solicitacao.status = "aceita"
    solicitacao.data_aceite = datetime.utcnow()
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


@router.post(
    "/solicitacoes-coleta/{solicitacao_id}/concluir",
    response_model=SolicitacaoColetaResponse,
)
def concluir_solicitacao_coleta(
    solicitacao_id: int,
    payload: SolicitacaoColetaConcluir,
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    """Conclui a retirada integral do inventário capturado na solicitação, recebendo o peso real."""
    solicitacao = (
        db.query(SolicitacaoColeta)
        .filter(
            SolicitacaoColeta.id == solicitacao_id,
            SolicitacaoColeta.cooperativa_id == cooperativa.id,
        )
        .first()
    )
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação de coleta não encontrada")
    if solicitacao.status != "aceita":
        raise HTTPException(status_code=409, detail="A solicitação precisa ser aceita antes da conclusão")

    ponto = solicitacao.ponto_coleta
    inventario_atual = dict(ponto.inventario or {})
    inventario_solicitado = solicitacao.inventario_solicitado or {}
    
    quantidade_coletada = sum(max(float(peso), 0.0) for peso in payload.pesos_reais.values())

    # Zera as unidades do Ponto de Coleta referentes ao material coletado
    for tipo_residuo in inventario_solicitado.keys():
        inventario_atual.pop(tipo_residuo, None)

    ponto.inventario = inventario_atual
    ponto.status = "ativo"
    solicitacao.quantidade_coletada = quantidade_coletada
    solicitacao.pesos_reais = payload.pesos_reais
    solicitacao.status = "concluida"
    solicitacao.data_conclusao = datetime.utcnow()
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


@router.post(
    "/solicitacoes-coleta/{solicitacao_id}/recusar",
    response_model=SolicitacaoColetaResponse,
)
def recusar_solicitacao_coleta(
    solicitacao_id: int,
    payload: SolicitacaoColetaRecusar,
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    solicitacao = (
        db.query(SolicitacaoColeta)
        .filter(
            SolicitacaoColeta.id == solicitacao_id,
            SolicitacaoColeta.cooperativa_id == cooperativa.id,
        )
        .first()
    )
    if not solicitacao:
        raise HTTPException(status_code=404, detail="Solicitação de coleta não encontrada")
    if solicitacao.status != "solicitada":
        raise HTTPException(status_code=409, detail="A solicitação não está disponível para recusa")

    solicitacao.status = "recusada"
    solicitacao.motivo_recusa = payload.motivo
    db.commit()
    db.refresh(solicitacao)
    return solicitacao


@router.get("/pontos-coleta")
def listar_pontos_da_cooperativa(
    db: Session = Depends(get_db),
    ponto_coleta: Usuario = Depends(require_role("ponto_coleta")),
):
    """Lista o ponto vinculado à conta de ponto de coleta autenticada."""
    pontos = (
        db.query(PontoColeta)
        .filter(PontoColeta.cooperativa_id == ponto_coleta.id)
        .order_by(PontoColeta.nome)
        .all()
    )
    return [
        {
            "id": ponto.id,
            "nome": ponto.nome,
            "endereco": ponto.endereco,
            "latitude": ponto.latitude,
            "longitude": ponto.longitude,
            "raio_operacao": ponto.raio_operacao,
            "capacidade_maxima": ponto.capacidade_maxima,
            "tipos_residuos_aceitos": ponto.tipos_residuos_aceitos or [],
            "horario_funcionamento": ponto.horario_funcionamento,
            "status": ponto.status,
            "inventario": ponto.inventario or {},
        }
        for ponto in pontos
    ]


@router.post("/descartes/{id_descarte}/rejeitar")
def rejeitar_descarte_cooperativa(
    id_descarte: int,
    payload: RejeitarDescarteRequest,
    db: Session = Depends(get_db),
    ponto_coleta: Usuario = Depends(require_role("ponto_coleta")),
):
    """Rejeita descarte pendente vinculado a ponto da cooperativa autenticada."""
    descarte = (
        db.query(Descarte).filter(Descarte.id_descarte == id_descarte).first()
    )
    if not descarte:
        raise HTTPException(status_code=404, detail="Descarte nao encontrado")

    validar_acesso_operacional_ao_ponto(ponto_coleta, descarte.ponto_coleta)
    rejeitar_descarte_pendente(db, descarte, ponto_coleta, payload.motivo)

    db.commit()
    db.refresh(descarte)
    return {
        "id": descarte.id_descarte,
        "status": descarte.status,
        "motivo_rejeicao": payload.motivo,
    }
