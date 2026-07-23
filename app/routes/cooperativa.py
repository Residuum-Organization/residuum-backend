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
from app.core.decorators import public
from app.schemas.usuario import CooperativaCreate
from app.services.password_service import hash_senha
from pydantic import BaseModel

router = APIRouter(
    prefix="/cooperativa",
    tags=["Cooperativa"],
)

class LancamentoAvulsoRequest(BaseModel):
    ponto_coleta_id: int
    material: str
    peso_kg: float

@router.post("/lancamento-avulso")
def lancamento_avulso(
    payload: LancamentoAvulsoRequest,
    db: Session = Depends(get_db),
    cooperativa: Usuario = Depends(require_role("cooperativa")),
):
    """Lança o peso coletado de forma direta, abatendo o inventário do ponto."""
    ponto = db.query(PontoColeta).filter(
        PontoColeta.id == payload.ponto_coleta_id,
        PontoColeta.cooperativa_id == cooperativa.id
    ).first()

    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto de coleta não encontrado ou não pertence a esta cooperativa")

    inventario_atual = dict(ponto.inventario or {})
    unidades = inventario_atual.pop(payload.material, 0)
    ponto.inventario = inventario_atual

    # Criamos um registro na SolicitacaoColeta para constar nos relatórios do sistema
    solicitacao = SolicitacaoColeta(
        admin_id=cooperativa.id, # usando a propria cooperativa como admin requester por simplicidade
        cooperativa_id=cooperativa.id,
        ponto_coleta_id=ponto.id,
        status="concluida",
        quantidade_inventario=float(unidades),
        inventario_solicitado={payload.material: unidades},
        quantidade_coletada=payload.peso_kg,
        pesos_reais={payload.material: payload.peso_kg},
        data_aceite=datetime.utcnow(),
        data_conclusao=datetime.utcnow()
    )
    db.add(solicitacao)
    db.commit()
    return {"msg": "Lançamento registrado com sucesso", "unidades_abatidas": unidades}

@router.post("/cadastro-cooperativa", status_code=status.HTTP_201_CREATED)
@public
def cadastrar_cooperativa(
    payload: CooperativaCreate,
    db: Session = Depends(get_db),
):
    """
    Endpoint para cadastro de uma nova cooperativa.
    """
    usuario_existente = db.query(Usuario).filter(Usuario.email == payload.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    nova_cooperativa = Usuario(
        nome=payload.nome,
        email=payload.email,
        telefone=payload.telefone,
        senha_hash=hash_senha(payload.senha),
        role="cooperativa",
    )
    db.add(nova_cooperativa)
    db.commit()
    db.refresh(nova_cooperativa)

    return {"id": nova_cooperativa.id, "nome": nova_cooperativa.nome, "email": nova_cooperativa.email, "msg" : "Cooperativa cadastrada com sucesso"}



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
    ponto_coleta: Usuario = Depends(require_role("cooperativa")),
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
            "horarios": ponto.horarios if hasattr(ponto, 'horarios') else [],
        }
        for ponto in pontos
    ]


@router.post("/descartes/{id_descarte}/rejeitar")
def rejeitar_descarte_cooperativa(
    id_descarte: int,
    payload: RejeitarDescarteRequest,
    db: Session = Depends(get_db),
    ponto_coleta: Usuario = Depends(require_role("cooperativa")),
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
