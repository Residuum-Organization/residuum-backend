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
from app.models.voucher import Voucher, VoucherCodigo
from app.schemas.voucher import (
    ResgateVoucherResponse,
    VoucherCodigosCreate,
    VoucherCodigosResponse,
    VoucherCreate,
    VoucherDetalheResponse,
    VoucherUpdate,
    VoucherResponse,
)
from app.services.voucher_service import (
    calcular_validade,
    montar_instrucoes,
    status_do_resgate,
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


def _usa_codigos_do_parceiro(db: Session, voucher_id: int) -> bool:
    return db.query(VoucherCodigo.id).filter(VoucherCodigo.voucher_id == voucher_id).first() is not None


def _resposta_resgate(resgate: ResgateVoucher, voucher: Voucher | None) -> ResgateVoucherResponse:
    return ResgateVoucherResponse(
        id=resgate.id,
        voucher_id=resgate.voucher_id,
        codigo=resgate.codigo,
        pontos_utilizados=resgate.pontos_utilizados,
        status=status_do_resgate(resgate),
        criado_em=resgate.criado_em,
        valido_ate=resgate.valido_ate,
        instrucoes_uso=montar_instrucoes(voucher, resgate.valido_ate) if voucher else None,
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
        instrucoes=payload.instrucoes,
        validade_codigo_dias=payload.validade_codigo_dias,
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

    # Voucher com codigos do parceiro entrega um deles; sem codigos cadastrados,
    # o sistema gera um codigo proprio (comportamento anterior).
    codigo_parceiro = None
    if _usa_codigos_do_parceiro(db, voucher.id):
        codigo_parceiro = (
            db.query(VoucherCodigo)
            .filter(VoucherCodigo.voucher_id == voucher.id, VoucherCodigo.status == "disponivel")
            .order_by(VoucherCodigo.id)
            .first()
        )
        if codigo_parceiro is None:
            raise_bad_request("Voucher esgotado.")
    codigo = codigo_parceiro.codigo if codigo_parceiro else _gerar_codigo_promocional()

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
        valido_ate=calcular_validade(voucher, agora),
    )
    db.add(resgate)
    if codigo_parceiro is not None:
        db.flush()
        codigo_parceiro.status = "resgatado"
        codigo_parceiro.resgate_id = resgate.id

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


@router.get("/{voucher_id}", response_model=VoucherDetalheResponse)
@public
def obter_voucher(voucher_id: int, db: Session = Depends(get_db)):
    """Detalhe de um voucher, com as instrucoes de uso."""
    agora = datetime.now(timezone.utc)
    voucher = (
        db.query(Voucher)
        .filter(
            Voucher.id == voucher_id,
            Voucher.status == "ativo",
            or_(Voucher.data_inicio.is_(None), Voucher.data_inicio <= agora),
            or_(Voucher.data_fim.is_(None), Voucher.data_fim >= agora),
        )
        .first()
    )
    if not voucher:
        raise_not_found("Voucher nao encontrado.")
    base = VoucherResponse.model_validate(voucher).model_dump()
    return VoucherDetalheResponse(**base, instrucoes_uso=montar_instrucoes(voucher))


@router.get("/{voucher_id}/codigos", response_model=VoucherCodigosResponse)
def listar_codigos_voucher(
    voucher_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Codigos do parceiro cadastrados no voucher, com o que ja foi entregue."""
    if not db.query(Voucher.id).filter(Voucher.id == voucher_id).first():
        raise_not_found("Voucher nao encontrado.")
    codigos = (
        db.query(VoucherCodigo)
        .filter(VoucherCodigo.voucher_id == voucher_id)
        .order_by(VoucherCodigo.id)
        .all()
    )
    return VoucherCodigosResponse(
        disponiveis=sum(1 for c in codigos if c.status == "disponivel"),
        resgatados=sum(1 for c in codigos if c.status == "resgatado"),
        codigos=codigos,
    )


@router.post("/{voucher_id}/codigos", response_model=VoucherCodigosResponse, status_code=201)
def adicionar_codigos_voucher(
    voucher_id: int,
    payload: VoucherCodigosCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Cadastra os codigos enviados pelo parceiro. Cada codigo soma 1 ao estoque."""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).with_for_update().first()
    if not voucher:
        raise_not_found("Voucher nao encontrado.")

    novos = []
    for bruto in payload.codigos:
        codigo = bruto.strip()
        if not codigo:
            continue
        if len(codigo) > 40:
            raise_bad_request(f"Codigo maior que 40 caracteres: {codigo[:20]}...")
        if codigo not in novos:
            novos.append(codigo)
    if not novos:
        raise_bad_request("Nenhum codigo informado.")

    existentes = {
        c
        for (c,) in db.query(VoucherCodigo.codigo).filter(VoucherCodigo.codigo.in_(novos)).all()
    } | {
        c
        for (c,) in db.query(ResgateVoucher.codigo).filter(ResgateVoucher.codigo.in_(novos)).all()
    }
    if existentes:
        raise_conflict("Codigos ja cadastrados: " + ", ".join(sorted(existentes)[:10]))

    for codigo in novos:
        db.add(VoucherCodigo(voucher_id=voucher.id, codigo=codigo, status="disponivel"))
    voucher.quantidade_disponivel = (voucher.quantidade_disponivel or 0) + len(novos)
    db.commit()
    return listar_codigos_voucher(voucher_id, db, admin)


@router.delete("/{voucher_id}/codigos/{codigo_id}", status_code=204)
def remover_codigo_voucher(
    voucher_id: int,
    codigo_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Remove um codigo que ainda nao foi entregue e tira 1 do estoque."""
    voucher = db.query(Voucher).filter(Voucher.id == voucher_id).with_for_update().first()
    if not voucher:
        raise_not_found("Voucher nao encontrado.")
    codigo = (
        db.query(VoucherCodigo)
        .filter(VoucherCodigo.id == codigo_id, VoucherCodigo.voucher_id == voucher_id)
        .first()
    )
    if not codigo:
        raise_not_found("Codigo nao encontrado.")
    if codigo.status != "disponivel":
        raise_bad_request("Este codigo ja foi entregue a um morador.")

    db.delete(codigo)
    voucher.quantidade_disponivel = max((voucher.quantidade_disponivel or 0) - 1, 0)
    db.commit()
    return None
