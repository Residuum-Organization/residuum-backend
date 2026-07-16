"""Rotas de campanhas: consulta publica, cadastro (admin) e inscricao (usuario)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_bad_request, raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.campanha import Campanha, InscricaoCampanha
from app.models.pontuacao import Pontuacao
from app.models.usuario import Usuario
from app.schemas.campanha import (
    CampanhaCreate,
    CampanhaUpdate,
    CampanhaResponse,
    InscricaoCampanhaResponse,
)

router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


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
    campanha = Campanha(
        titulo=payload.titulo,
        descricao=payload.descricao,
        patrocinador=payload.patrocinador,
        patrocinador_logo_url=payload.patrocinador_logo_url,
        pontos_recompensa=payload.pontos_recompensa,
        status=payload.status,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
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
    """Atualiza uma campanha existente."""
    campanha = db.query(Campanha).filter(Campanha.id == campanha_id).first()
    if not campanha:
        raise_not_found("Campanha não encontrada.")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(campanha, key, value)

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
    """Inscreve o usuário na campanha, acumulando os pontos de recompensa."""
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

    ja_inscrito = (
        db.query(InscricaoCampanha.id)
        .filter(
            InscricaoCampanha.campanha_id == campanha.id,
            InscricaoCampanha.usuario_id == usuario.id,
        )
        .first()
    )
    if ja_inscrito:
        raise_bad_request("Você já participa desta campanha.")

    pontos = int(campanha.pontos_recompensa or 0)

    inscricao = InscricaoCampanha(
        campanha_id=campanha.id,
        usuario_id=usuario.id,
        pontos_concedidos=pontos,
    )
    db.add(inscricao)

    # Acumula os pontos da campanha na carteira do usuário.
    if pontos > 0:
        usuario.pontuacao_total = int(usuario.pontuacao_total or 0) + pontos
        db.add(Pontuacao(pontos=pontos, usuario_id=usuario.id))

    db.commit()
    db.refresh(inscricao)

    return InscricaoCampanhaResponse(
        id=inscricao.id,
        campanha_id=inscricao.campanha_id,
        pontos_concedidos=inscricao.pontos_concedidos,
        criado_em=inscricao.criado_em,
        titulo=campanha.titulo,
        patrocinador=campanha.patrocinador,
    )
