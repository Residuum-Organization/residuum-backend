"""Rotas de campanhas: consulta publica, cadastro (admin), adesao e recompensa (usuario)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_bad_request, raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.campanha import Campanha, CampanhaRequisito, InscricaoCampanha
from app.models.usuario import Usuario
from app.schemas.campanha import (
    CampanhaCreate,
    CampanhaProgressoResponse,
    CampanhaUpdate,
    CampanhaResponse,
    InscricaoCampanhaResponse,
)
from app.services import campanha_service

router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


def _montar_requisitos(requisitos) -> list[CampanhaRequisito]:
    return [CampanhaRequisito(**item.model_dump()) for item in requisitos]


def _inscricao_response(inscricao: InscricaoCampanha, campanha: Campanha) -> InscricaoCampanhaResponse:
    return InscricaoCampanhaResponse(
        id=inscricao.id,
        campanha_id=inscricao.campanha_id,
        pontos_concedidos=inscricao.pontos_concedidos,
        criado_em=inscricao.criado_em,
        titulo=campanha.titulo,
        patrocinador=campanha.patrocinador,
    )


@router.get("", response_model=list[CampanhaResponse])
@public
def listar_campanhas(db: Session = Depends(get_db)):
    """Lista campanhas ativas dentro da janela de vigência."""
    agora = datetime.now(timezone.utc)
    return (
        db.query(Campanha)
        .filter(
            Campanha.status == "ativa",
            or_(Campanha.data_inicio.is_(None), Campanha.data_inicio <= agora),
            or_(Campanha.data_fim.is_(None), Campanha.data_fim >= agora),
        )
        .order_by(Campanha.criado_em.desc())
        .all()
    )


@router.get("/admin", response_model=list[CampanhaResponse])
def listar_todas_campanhas_admin(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Lista todas as campanhas, independente do status (restrito a administradores)."""
    return db.query(Campanha).order_by(Campanha.criado_em.desc()).all()


@router.post("", response_model=CampanhaResponse, status_code=201)
def criar_campanha(
    payload: CampanhaCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Cadastra uma nova campanha. Restrito a administradores."""
    campanha_service.validar_definicao(payload.acesso, payload.pontos_recompensa, payload.requisitos)
    campanha = Campanha(
        titulo=payload.titulo,
        descricao=payload.descricao,
        patrocinador=payload.patrocinador,
        patrocinador_logo_url=payload.patrocinador_logo_url,
        pontos_recompensa=payload.pontos_recompensa,
        acesso=payload.acesso,
        condicoes=payload.condicoes,
        status=payload.status,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
        requisitos=_montar_requisitos(payload.requisitos),
    )
    db.add(campanha)
    db.commit()
    db.refresh(campanha)
    return campanha


@router.put("/{campanha_id}", response_model=CampanhaResponse)
def atualizar_campanha(
    campanha_id: int,
    payload: CampanhaUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Atualiza uma campanha existente. `requisitos`, quando enviado, substitui a lista."""
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha:
        raise_not_found("Campanha não encontrada.")

    dados = payload.dict(exclude_unset=True)
    dados.pop("requisitos", None)

    acesso = dados.get("acesso", campanha.acesso)
    pontos = dados.get("pontos_recompensa", campanha.pontos_recompensa)
    requisitos = payload.requisitos if payload.requisitos is not None else campanha.requisitos
    # Só revalida quando a definição muda: não trava edição de campanhas antigas.
    if payload.requisitos is not None or "acesso" in dados or "pontos_recompensa" in dados:
        campanha_service.validar_definicao(acesso, pontos, requisitos)

    for key, value in dados.items():
        setattr(campanha, key, value)
    if payload.requisitos is not None:
        campanha.requisitos = _montar_requisitos(payload.requisitos)

    db.commit()
    db.refresh(campanha)
    return campanha


@router.delete("/{campanha_id}", status_code=204)
def deletar_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Remove uma campanha (ou encerra logicamente se for uma escolha de arquitetura, mas aqui faremos delete)."""
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha:
        raise_not_found("Campanha não encontrada.")

    db.delete(campanha)
    db.commit()
    return None


@router.get("/minhas-inscricoes", response_model=list[InscricaoCampanhaResponse])
def listar_minhas_inscricoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista as campanhas em que o usuario autenticado se inscreveu."""
    inscricoes = (
        db.query(InscricaoCampanha)
        .filter(InscricaoCampanha.usuario_id == usuario.id)
        .order_by(InscricaoCampanha.criado_em.desc())
        .all()
    )
    return [
        InscricaoCampanhaResponse(
            id=i.id,
            campanha_id=i.campanha_id,
            pontos_concedidos=i.pontos_concedidos,
            criado_em=i.criado_em,
            titulo=i.campanha.titulo if i.campanha else None,
            patrocinador=i.campanha.patrocinador if i.campanha else None,
        )
        for i in inscricoes
    ]


@router.post(
    "/{campanha_id}/participar",
    response_model=InscricaoCampanhaResponse,
    status_code=201,
)
def participar_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Registra a participacao (gratuita, inclusive nas privadas).

    Sem participar nao ha bonus nem progresso: nenhum descarte conta antes da
    adesao. Aderir nao credita pontos.
    """
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha:
        raise_not_found("Campanha nao encontrada.")

    agora = datetime.now(timezone.utc)
    if campanha.status != "ativa":
        raise_bad_request("Campanha indisponivel para participacao.")
    if campanha.data_inicio is not None and campanha.data_inicio > agora:
        raise_bad_request("Campanha ainda nao esta aberta.")
    if campanha.data_fim is not None and campanha.data_fim < agora:
        raise_bad_request("Campanha encerrada.")

    inscricao = campanha_service.aderir(db, campanha, usuario)
    return _inscricao_response(inscricao, campanha)


@router.get("/{campanha_id}/progresso", response_model=CampanhaProgressoResponse)
def progresso_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Progresso do usuario nos requisitos de entrada e nas missoes da campanha."""
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha or campanha.status != "ativa":
        raise_not_found("Campanha nao encontrada.")
    return campanha_service.avaliar(db, campanha, usuario)


@router.post("/{campanha_id}/recompensa", response_model=InscricaoCampanhaResponse)
def receber_recompensa_campanha(
    campanha_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Credita a recompensa (uma vez) a quem participa e concluiu todas as missoes."""
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha or campanha.status != "ativa":
        raise_not_found("Campanha nao encontrada.")
    inscricao = campanha_service.conceder_recompensa(db, campanha, usuario)
    return _inscricao_response(inscricao, campanha)


# Declarada por último para não capturar /admin nem /minhas-inscricoes.
@router.get("/{campanha_id}", response_model=CampanhaResponse)
@public
def obter_campanha(campanha_id: int, db: Session = Depends(get_db)):
    """Detalhe de uma campanha consultável (ativa e dentro da vigência)."""
    agora = datetime.now(timezone.utc)
    campanha = (
        db.query(Campanha)
        .filter(
            Campanha.id == campanha_id,
            Campanha.status == "ativa",
            or_(Campanha.data_inicio.is_(None), Campanha.data_inicio <= agora),
            or_(Campanha.data_fim.is_(None), Campanha.data_fim >= agora),
        )
        .first()
    )
    if not campanha:
        raise_not_found("Campanha nao encontrada.")
    return campanha
