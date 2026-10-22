"""Rotas de notificações operacionais."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role, validar_acesso_operacional_ao_ponto
from app.models.notificacao import Notificacao
from app.models.ponto_coleta import PontoColeta
from app.models.usuario import Usuario

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("/minhas")
def listar_minhas_notificacoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Avisos do morador (por exemplo, resultado de sorteio), do mais novo ao mais antigo."""
    return (
        db.query(Notificacao)
        .filter(Notificacao.usuario_id == usuario.id)
        .order_by(Notificacao.criado_em.desc(), Notificacao.id.desc())
        .limit(50)
        .all()
    )


@router.patch("/minhas/{notificacao_id}/lida")
def marcar_minha_notificacao_como_lida(
    notificacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    notificacao = (
        db.query(Notificacao)
        .filter(Notificacao.id == notificacao_id, Notificacao.usuario_id == usuario.id)
        .first()
    )
    if not notificacao:
        raise_not_found("Notificação não encontrada.")
    notificacao.lida = True
    db.commit()
    return {"status": "Notificação marcada como lida"}


@router.get("/")
def listar_notificacoes_nao_lidas(
    ponto_id: Optional[int] = Query(None, description="Filtrar por ID do Ponto de Coleta"),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    if ponto_id is not None:
        ponto = db.query(PontoColeta).filter(PontoColeta.id == ponto_id).first()
        validar_acesso_operacional_ao_ponto(usuario, ponto)

    query = db.query(Notificacao).filter(
        Notificacao.lida.is_(False), Notificacao.usuario_id.is_(None)
    )
    if usuario.role == "cooperativa":
        query = query.join(PontoColeta, Notificacao.ponto_coleta_id == PontoColeta.id).filter(
            PontoColeta.cooperativa_id == usuario.id
        )
    if ponto_id:
        query = query.filter(Notificacao.ponto_coleta_id == ponto_id)

    return query.order_by(Notificacao.criado_em.desc()).all()


@router.patch("/{notificacao_id}/lida")
def marcar_como_lida(
    notificacao_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    """
    Marca um alerta como lido para que ele suma do painel.
    """
    notificacao = db.query(Notificacao).filter(Notificacao.id == notificacao_id).first()

    if not notificacao or notificacao.usuario_id is not None:
        raise_not_found("Notificação não encontrada.")

    if usuario.role == "cooperativa":
        ponto = db.query(PontoColeta).filter(PontoColeta.id == notificacao.ponto_coleta_id).first()
        validar_acesso_operacional_ao_ponto(usuario, ponto)

    notificacao.lida = True
    db.commit()

    return {"status": "Notificação marcada como lida"}
