"""Rotas de vouchers: consulta publica, cadastro (admin) e resgate (usuario)."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_bad_request, raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.resgate_voucher import ResgateVoucher
from app.models.usuario import Usuario
from app.models.voucher import Voucher
from app.schemas.voucher import (
    ResgateVoucherResponse,
    VoucherCreate,
    VoucherResponse,
)

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


def _gerar_codigo_promocional() -> str:
    """Gera um codigo promocional legivel e unico por resgate."""
    return f"RSDM-{secrets.token_hex(4).upper()}"


@router.get("", response_model=list[VoucherResponse])
@public
def listar_vouchers(db: Session = Depends(get_db)):
    """Lista vouchers ativos e com quantidade disponivel."""
    agora = datetime.now(timezone.utc)
    return (
        db.query(Voucher)
        .filter(
            Voucher.status == "ativo",
            Voucher.quantidade_disponivel > 0,
            or_(Voucher.data_inicio.is_(None), Voucher.data_inicio <= agora),
            or_(Voucher.data_fim.is_(None), Voucher.data_fim >= agora),
        )
        .order_by(Voucher.criado_em.desc())
        .all()
    )


@router.post("", response_model=VoucherResponse, status_code=201)
def criar_voucher(
    payload: VoucherCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Cadastra um novo voucher. Restrito a administradores."""
    voucher = Voucher(
        titulo=payload.titulo,
        descricao=payload.descricao,
        parceiro=payload.parceiro,
        custo_pontos=payload.custo_pontos,
        quantidade_disponivel=payload.quantidade_disponivel,
        status=payload.status,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
    )
    db.add(voucher)
    db.commit()
    db.refresh(voucher)
    return voucher


@router.post("/{voucher_id}/resgatar", response_model=ResgateVoucherResponse, status_code=201)
def resgatar_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Resgata um voucher: debita os pontos e devolve um codigo promocional."""
    # Bloqueia a linha do voucher para evitar corrida na quantidade disponivel.
    voucher = (
        db.query(Voucher)
        .filter(Voucher.id == voucher_id)
        .with_for_update()
        .first()
    )
    if not voucher:
        raise_not_found("Voucher nao encontrado.")

    agora = datetime.now(timezone.utc)
    if voucher.status != "ativo":
        raise_bad_request("Voucher indisponivel para resgate.")
    if voucher.data_inicio is not None and voucher.data_inicio > agora:
        raise_bad_request("Voucher ainda nao esta disponivel.")
    if voucher.data_fim is not None and voucher.data_fim < agora:
        raise_bad_request("Voucher expirado.")
    if (voucher.quantidade_disponivel or 0) <= 0:
        raise_bad_request("Voucher esgotado.")

    saldo_atual = int(usuario.pontuacao_total or 0)
    if voucher.custo_pontos > saldo_atual:
        raise_bad_request("Pontuacao insuficiente para resgatar este voucher.")

    # Debita pontos e decrementa o estoque do voucher.
    usuario.pontuacao_total = saldo_atual - voucher.custo_pontos
    voucher.quantidade_disponivel = voucher.quantidade_disponivel - 1

    codigo = _gerar_codigo_promocional()
    resgate = ResgateVoucher(
        voucher_id=voucher.id,
        usuario_id=usuario.id,
        codigo=codigo,
        pontos_utilizados=voucher.custo_pontos,
        status="ativo",
    )
    db.add(resgate)

    # Registra no extrato de pontos unificado.
    db.add(
        ResgatePontuacao(
            usuario_id=usuario.id,
            pontos_utilizados=voucher.custo_pontos,
            descricao=f"Resgate de voucher: {voucher.titulo}",
            referencia=codigo,
            status="resgatado",
        )
    )

    db.commit()
    db.refresh(resgate)

    return ResgateVoucherResponse(
        id=resgate.id,
        voucher_id=resgate.voucher_id,
        codigo=resgate.codigo,
        pontos_utilizados=resgate.pontos_utilizados,
        status=resgate.status,
        criado_em=resgate.criado_em,
        titulo=voucher.titulo,
        parceiro=voucher.parceiro,
    )


@router.get("/meus-resgates", response_model=list[ResgateVoucherResponse])
def listar_meus_resgates_voucher(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista os vouchers resgatados pelo usuario autenticado, com seus codigos."""
    resgates = (
        db.query(ResgateVoucher)
        .filter(ResgateVoucher.usuario_id == usuario.id)
        .order_by(ResgateVoucher.criado_em.desc())
        .all()
    )
    return [
        ResgateVoucherResponse(
            id=r.id,
            voucher_id=r.voucher_id,
            codigo=r.codigo,
            pontos_utilizados=r.pontos_utilizados,
            status=r.status,
            criado_em=r.criado_em,
            titulo=r.voucher.titulo if r.voucher else None,
            parceiro=r.voucher.parceiro if r.voucher else None,
        )
        for r in resgates
    ]
