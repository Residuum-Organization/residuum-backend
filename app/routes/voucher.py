"""Rotas de vouchers: consulta publica, cadastro (admin) e resgate (usuario)."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_bad_request, raise_conflict, raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.resgate_voucher import ResgateVoucher
from app.models.usuario import Usuario
from app.models.voucher import Voucher
from app.schemas.voucher import (
    ResgateVoucherResponse,
    VoucherCreate,
    VoucherUpdate,
    VoucherResponse,
)
from app.services.saldo_service import (
    ORIGEM_VOUCHER,
    SaldoInsuficiente,
    debitar_pontos,
    travar_usuario,
)

router = APIRouter(prefix="/vouchers", tags=["Vouchers"])


def _gerar_codigo_promocional() -> str:
    """Gera um codigo promocional legivel e unico por resgate."""
    return f"RSDM-{secrets.token_hex(4).upper()}"


def _resposta_resgate(resgate: ResgateVoucher, voucher: Voucher | None) -> ResgateVoucherResponse:
    return ResgateVoucherResponse(
        id=resgate.id,
        voucher_id=resgate.voucher_id,
        codigo=resgate.codigo,
        pontos_utilizados=resgate.pontos_utilizados,
        status=resgate.status,
        criado_em=resgate.criado_em,
        titulo=voucher.titulo if voucher else None,
        parceiro=voucher.parceiro if voucher else None,
    )


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


@router.get("/admin", response_model=list[VoucherResponse])
def listar_todos_vouchers_admin(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Lista vouchers de qualquer status e estoque para gestao administrativa."""
    return db.query(Voucher).order_by(Voucher.criado_em.desc()).all()


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


@router.put("/{voucher_id}", response_model=VoucherResponse)
def atualizar_voucher(
    voucher_id: int,
    payload: VoucherUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Atualiza um voucher existente."""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise_not_found("Voucher nao encontrado.")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(voucher, key, value)

    db.commit()
    db.refresh(voucher)
    return voucher


@router.delete("/{voucher_id}", status_code=204)
def deletar_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Remove um voucher."""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
    if not voucher:
        raise_not_found("Voucher nao encontrado.")

    db.delete(voucher)
    db.commit()
    return None


@router.post("/{voucher_id}/resgatar", response_model=ResgateVoucherResponse, status_code=201)
def resgatar_voucher(
    voucher_id: int,
    response: Response,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
    chave: str | None = Header(default=None, alias="Idempotency-Key", max_length=80),
):
    """Resgata um voucher: debita os pontos e devolve um codigo promocional.

    Com o cabecalho Idempotency-Key, reenviar o mesmo pedido devolve o resgate
    ja feito (200) em vez de debitar de novo.
    """
    # Bloqueia a linha do voucher para evitar corrida na quantidade disponivel.
    voucher = (
        db.query(Voucher)
        .filter(Voucher.id == voucher_id)
        .with_for_update()
        .first()
    )
    if not voucher:
        raise_not_found("Voucher nao encontrado.")

    # Trava o usuario antes de olhar a chave: pedidos paralelos do mesmo
    # morador passam um de cada vez.
    travar_usuario(db, usuario.id)
    if chave:
        anterior = (
            db.query(ResgateVoucher)
            .filter(
                ResgateVoucher.usuario_id == usuario.id,
                ResgateVoucher.chave_idempotencia == chave,
            )
            .first()
        )
        if anterior:
            if anterior.voucher_id != voucher.id:
                raise_conflict("Chave de idempotencia ja usada em outro resgate.")
            response.status_code = 200
            return _resposta_resgate(anterior, voucher)

    agora = datetime.now(timezone.utc)
    if voucher.status != "ativo":
        raise_bad_request("Voucher indisponivel para resgate.")
    if voucher.data_inicio is not None and voucher.data_inicio > agora:
        raise_bad_request("Voucher ainda nao esta disponivel.")
    if voucher.data_fim is not None and voucher.data_fim < agora:
        raise_bad_request("Voucher expirado.")
    if (voucher.quantidade_disponivel or 0) <= 0:
        raise_bad_request("Voucher esgotado.")

    codigo = _gerar_codigo_promocional()
    # Debita pontos (saldo travado) e registra no extrato com a origem.
    try:
        debitar_pontos(
            db,
            usuario.id,
            voucher.custo_pontos,
            origem=ORIGEM_VOUCHER,
            descricao=f"Resgate de voucher: {voucher.titulo}",
            referencia=codigo,
        )
    except SaldoInsuficiente:
        raise_bad_request("Pontuacao insuficiente para resgatar este voucher.")

    voucher.quantidade_disponivel = voucher.quantidade_disponivel - 1
    resgate = ResgateVoucher(
        voucher_id=voucher.id,
        usuario_id=usuario.id,
        codigo=codigo,
        pontos_utilizados=voucher.custo_pontos,
        status="ativo",
        chave_idempotencia=chave or None,
    )
    db.add(resgate)

    db.commit()
    db.refresh(resgate)

    return _resposta_resgate(resgate, voucher)


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
    return [_resposta_resgate(r, r.voucher) for r in resgates]
