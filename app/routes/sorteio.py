"""Rotas de sorteios: consulta publica, cadastro, bilhetes e apuracao."""

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.decorators import public
from app.core.exceptions import raise_bad_request, raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role
from app.models.bilhete_sorteio import BilheteSorteio
from app.models.audit_log import AuditLog
from app.models.descarte import Descarte
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.sorteio import Sorteio
from app.models.usuario import Usuario
from app.schemas.sorteio import (
    BilheteSorteioResponse,
    SorteioCreate,
    SorteioUpdate,
    SorteioResponse,
)
from app.services.audit_service import registrar_acao

router = APIRouter(prefix="/sorteios", tags=["Sorteios"])


def _filtrar_ativos(query):
    agora = datetime.now(timezone.utc)
    return query.filter(
        Sorteio.status == "ativo",
        or_(Sorteio.data_inicio.is_(None), Sorteio.data_inicio <= agora),
        or_(Sorteio.data_fim.is_(None), Sorteio.data_fim >= agora),
    )


def _usuario_validou_descarte_por_gps(usuario_id: int, db: Session) -> bool:
    """Verifica se o usuário possui ao menos um descarte confirmado com
    presença validada por GPS (coordenadas registradas)."""
    return (
        db.query(Descarte.id_descarte)
        .filter(
            Descarte.usuario_id == usuario_id,
            Descarte.status == "confirmado",
            Descarte.usuario_lat.isnot(None),
            Descarte.usuario_long.isnot(None),
            Descarte.usuario_lat != 0,
            Descarte.usuario_long != 0,
        )
        .first()
        is not None
    )


def _obter_resultado(sorteio_id: int, db: Session):
    return (
        db.query(AuditLog)
        .filter(
            AuditLog.action == "sorteio.apurar",
            AuditLog.target_type == "sorteio",
            AuditLog.target_id == sorteio_id,
        )
        .order_by(AuditLog.created_at.desc())
        .first()
    )


@router.get("", response_model=list[SorteioResponse])
@public
def listar_sorteios(db: Session = Depends(get_db)):
    """Lista sorteios ativos por padrao."""
    return _filtrar_ativos(db.query(Sorteio)).order_by(Sorteio.criado_em.desc()).all()


@router.get("/admin", response_model=list[SorteioResponse])
def listar_todos_sorteios_admin(
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Lista sorteios de qualquer status para gestao administrativa."""
    return db.query(Sorteio).order_by(Sorteio.criado_em.desc()).all()


@router.get("/{sorteio_id}/resultado")
@public
def obter_resultado_sorteio(sorteio_id: int, db: Session = Depends(get_db)):
    sorteio = db.query(Sorteio).filter(Sorteio.id == sorteio_id).first()
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")
    resultado = _obter_resultado(sorteio_id, db)
    if not resultado:
        raise_not_found("Resultado ainda nao publicado.")
    return {**(resultado.payload or {}), "sorteado_em": resultado.created_at}


@router.post("/{sorteio_id}/sortear")
def sortear_vencedor(
    sorteio_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    sorteio = db.query(Sorteio).filter(Sorteio.id == sorteio_id).with_for_update().first()
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")
    if _obter_resultado(sorteio_id, db):
        raise_bad_request("Este sorteio ja possui um vencedor publicado.")

    agora = datetime.now(timezone.utc)
    if sorteio.status != "encerrado" and (sorteio.data_fim is None or sorteio.data_fim > agora):
        raise_bad_request("Encerre o sorteio ou aguarde a data final antes da apuracao.")

    bilhetes = db.query(BilheteSorteio).filter(BilheteSorteio.sorteio_id == sorteio.id).all()
    if not bilhetes:
        raise_bad_request("Nao existem bilhetes para apurar este sorteio.")

    vencedor = secrets.choice(bilhetes)
    payload = {
        "sorteio_id": sorteio.id,
        "titulo": sorteio.titulo,
        "premio": sorteio.premio,
        "bilhete_id": vencedor.id,
        "numero": vencedor.numero,
        "usuario_id": vencedor.usuario_id,
        "vencedor_nome": vencedor.usuario.nome if vencedor.usuario else None,
    }
    sorteio.status = "encerrado"
    registro = registrar_acao(
        db,
        admin_id=admin.id,
        action="sorteio.apurar",
        target_type="sorteio",
        target_id=sorteio.id,
        payload=payload,
    )
    db.commit()
    db.refresh(registro)
    return {**payload, "sorteado_em": registro.created_at}


@router.post("", response_model=SorteioResponse, status_code=201)
def criar_sorteio(
    payload: SorteioCreate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Cadastra um novo sorteio. Restrito a administradores."""
    sorteio = Sorteio(
        titulo=payload.titulo,
        descricao=payload.descricao,
        premio=payload.premio,
        custo_pontos=payload.custo_pontos,
        status=payload.status,
        data_inicio=payload.data_inicio,
        data_fim=payload.data_fim,
    )
    db.add(sorteio)
    db.commit()
    db.refresh(sorteio)
    return sorteio


@router.put("/{sorteio_id}", response_model=SorteioResponse)
def atualizar_sorteio(
    sorteio_id: int,
    payload: SorteioUpdate,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Atualiza um sorteio existente."""
    sorteio = db.query(Sorteio).filter(Sorteio.id == sorteio_id).first()
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")

    update_data = payload.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(sorteio, key, value)

    db.commit()
    db.refresh(sorteio)
    return sorteio


@router.delete("/{sorteio_id}", status_code=204)
def deletar_sorteio(
    sorteio_id: int,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_role("admin")),
):
    """Remove um sorteio."""
    sorteio = db.query(Sorteio).filter(Sorteio.id == sorteio_id).first()
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")

    db.delete(sorteio)
    db.commit()
    return None


@router.get("/meus-bilhetes", response_model=list[BilheteSorteioResponse])
def listar_meus_bilhetes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista os bilhetes de sorteio comprados pelo usuario autenticado."""
    bilhetes = (
        db.query(BilheteSorteio)
        .filter(BilheteSorteio.usuario_id == usuario.id)
        .order_by(BilheteSorteio.criado_em.desc())
        .all()
    )
    return [
        BilheteSorteioResponse(
            id=b.id,
            sorteio_id=b.sorteio_id,
            numero=b.numero,
            pontos_utilizados=b.pontos_utilizados,
            criado_em=b.criado_em,
            titulo=b.sorteio.titulo if b.sorteio else None,
            premio=b.sorteio.premio if b.sorteio else None,
        )
        for b in bilhetes
    ]


@router.post(
    "/{sorteio_id}/comprar-bilhete",
    response_model=BilheteSorteioResponse,
    status_code=201,
)
def comprar_bilhete(
    sorteio_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Compra um bilhete de sorteio.

    Regras:
    - somente 1 bilhete por usuário por sorteio;
    - o usuário precisa ter validado um descarte por presença (GPS);
    - o custo em pontos é debitado do saldo da carteira com segurança;
    - o bilhete recebe uma numeração sequencial dentro do sorteio.
    """
    # Bloqueia a linha do sorteio para serializar a numeração dos bilhetes.
    sorteio = (
        db.query(Sorteio)
        .filter(Sorteio.id == sorteio_id)
        .with_for_update()
        .first()
    )
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")

    agora = datetime.now(timezone.utc)
    if sorteio.status != "ativo":
        raise_bad_request("Sorteio indisponivel para participacao.")
    if sorteio.data_inicio is not None and sorteio.data_inicio > agora:
        raise_bad_request("Sorteio ainda nao esta aberto.")
    if sorteio.data_fim is not None and sorteio.data_fim < agora:
        raise_bad_request("Sorteio encerrado.")

    # Critério de participação: descarte validado por presença (GPS).
    if not _usuario_validou_descarte_por_gps(usuario.id, db):
        raise_bad_request("Você precisa ter um descarte confirmado com validação por presença (GPS) para participar.")
    # Regra: somente 1 bilhete por usuário por sorteio.
    ja_possui = (
        db.query(BilheteSorteio.id)
        .filter(
            BilheteSorteio.sorteio_id == sorteio.id,
            BilheteSorteio.usuario_id == usuario.id,
        )
        .first()
    )
    if ja_possui:
        raise_bad_request("Você já possui um bilhete neste sorteio.")

    saldo_atual = int(usuario.pontuacao_total or 0)
    if sorteio.custo_pontos > saldo_atual:
        raise_bad_request("Pontuacao insuficiente para comprar o bilhete.")

    # Numeração sequencial dentro do sorteio (linha do sorteio já bloqueada).
    maior_numero = (
        db.query(func.coalesce(func.max(BilheteSorteio.numero), 0))
        .filter(BilheteSorteio.sorteio_id == sorteio.id)
        .scalar()
    )
    numero = int(maior_numero) + 1

    # Debita pontos com segurança.
    usuario.pontuacao_total = saldo_atual - sorteio.custo_pontos

    bilhete = BilheteSorteio(
        sorteio_id=sorteio.id,
        usuario_id=usuario.id,
        numero=numero,
        pontos_utilizados=sorteio.custo_pontos,
    )
    db.add(bilhete)

    # Registra no extrato de pontos unificado.
    db.add(
        ResgatePontuacao(
            usuario_id=usuario.id,
            pontos_utilizados=sorteio.custo_pontos,
            descricao=f"Bilhete do sorteio: {sorteio.titulo}",
            referencia=f"sorteio:{sorteio.id}:bilhete:{numero}",
            status="resgatado",
        )
    )

    db.commit()
    db.refresh(bilhete)

    return BilheteSorteioResponse(
        id=bilhete.id,
        sorteio_id=bilhete.sorteio_id,
        numero=bilhete.numero,
        pontos_utilizados=bilhete.pontos_utilizados,
        criado_em=bilhete.criado_em,
        titulo=sorteio.titulo,
        premio=sorteio.premio,
    )


@router.get("/{sorteio_id}", response_model=SorteioResponse)
@public
def obter_sorteio(sorteio_id: int, db: Session = Depends(get_db)):
    """Retorna o detalhe de um sorteio."""
    sorteio = db.query(Sorteio).filter(Sorteio.id == sorteio_id).first()
    if not sorteio:
        raise_not_found("Sorteio nao encontrado.")

    return sorteio
