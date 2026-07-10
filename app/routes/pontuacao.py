"""Rotas de extrato e resgate de pontos."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions import raise_bad_request
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.usuario import Usuario
from app.schemas.pontuacao import (
    ExtratoPontosResponse,
    PontuacaoResgateCreate,
    ResgatePontuacaoResponse,
)
from app.services.extrato_pontos_service import montar_extrato_pontos_usuario
from app.services.serializacao_service import serializar_resgate_pontuacao

router = APIRouter(prefix="/pontuacao", tags=["Pontuação"])


@router.get("/extrato", response_model=ExtratoPontosResponse)
def obter_extrato_pontos(
    limit: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Retorna o extrato consolidado com descartes e resgates do usuario."""
    return montar_extrato_pontos_usuario(usuario, db, limit=limit)


@router.get("/resgates", response_model=list[ResgatePontuacaoResponse])
def listar_resgates_pontos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista os resgates de pontos do usuario autenticado."""
    resgates = (
        db.query(ResgatePontuacao)
        .filter(ResgatePontuacao.usuario_id == usuario.id)
        .order_by(ResgatePontuacao.data_resgate.desc())
        .all()
    )
    return [serializar_resgate_pontuacao(resgate) for resgate in resgates]


@router.post("/resgates", response_model=ResgatePontuacaoResponse)
def registrar_resgate_pontos(
    payload: PontuacaoResgateCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Consome pontos do usuario e registra um evento com status `resgatado`."""
    saldo_atual = int(usuario.pontuacao_total or 0)
    if payload.pontos > saldo_atual:
        raise_bad_request("Pontuação insuficiente para concluir o resgate.")

    usuario.pontuacao_total = saldo_atual - payload.pontos

    resgate = ResgatePontuacao(
        usuario_id=usuario.id,
        pontos_utilizados=payload.pontos,
        descricao=payload.descricao,
        referencia=payload.referencia,
        status="resgatado",
    )
    db.add(resgate)
    db.commit()
    db.refresh(resgate)

    return serializar_resgate_pontuacao(resgate)
