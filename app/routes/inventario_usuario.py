"""
Rotas do Inventário do Usuário - Task 11.

Permite cadastrar, consultar, atualizar e transferir resíduos que o usuário
possui antes da confirmação em um ponto de coleta.
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.exceptions import raise_not_found
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.usuario import Usuario
from app.models.inventario_usuario import InventarioUsuario
from app.models.descarte import Descarte
from app.models.ponto_coleta import PontoColeta
from app.models.qrcode_token import QRCodeToken
from app.schemas.inventario_usuario import (
    InventarioUsuarioCreate,
    InventarioUsuarioUpdate,
    InventarioUsuarioTransferir,
    InventarioUsuarioResponse,
)
from app.schemas.descarte import DescarteResponse
from app.services.validacao_service import validar_quantidade, validar_residuo
from app.services.localizacao_service import validar_localizacao
from app.services.ponto_coleta_service import validar_ponto_disponivel_para_descarte

router = APIRouter(prefix="/me/inventario", tags=["Inventário do Usuário"])

STATUS_PERMITIDOS = {"disponivel", "em_transferencia", "finalizado", "cancelado"}


def _normalizar_tipo_residuo(tipo: str) -> str:
    return tipo.strip().lower()


def _quantidade_disponivel(item: InventarioUsuario) -> float:
    return max(float(item.quantidade or 0) - float(item.quantidade_reservada or 0), 0)


def _recalcular_status(item: InventarioUsuario) -> None:
    if item.status == "cancelado":
        return

    disponivel = _quantidade_disponivel(item)
    reservada = float(item.quantidade_reservada or 0)
    total = float(item.quantidade or 0)

    if total <= 0 and reservada <= 0:
        item.status = "finalizado"
    elif disponivel <= 0 and reservada > 0:
        item.status = "em_transferencia"
    else:
        item.status = "disponivel"


@router.post("", response_model=InventarioUsuarioResponse)
def cadastrar_item_inventario(
    obj_in: InventarioUsuarioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Cadastra um resíduo no inventário pessoal do usuário autenticado."""
    tipo_residuo = _normalizar_tipo_residuo(obj_in.tipo_residuo)

    if not validar_residuo(tipo_residuo):
        raise HTTPException(status_code=400, detail="Tipo de resíduo não aceito.")

    if not validar_quantidade(obj_in.quantidade):
        raise HTTPException(status_code=400, detail="Quantidade inválida. O valor deve estar entre 1 e 1000.")

    item = InventarioUsuario(
        usuario_id=usuario.id,
        tipo_residuo=tipo_residuo,
        quantidade=obj_in.quantidade,
        quantidade_reservada=0,
        descricao=obj_in.descricao,
        observacao=obj_in.observacao,
        status="disponivel",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[InventarioUsuarioResponse])
def listar_inventario(
    status: str | None = Query(default=None, description="Filtra por status do item."),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Lista os resíduos cadastrados no inventário do usuário autenticado."""
    query = db.query(InventarioUsuario).filter(InventarioUsuario.usuario_id == usuario.id)

    if status:
        query = query.filter(InventarioUsuario.status == status)

    return query.order_by(InventarioUsuario.data_cadastro.desc()).all()


@router.get("/{item_id}", response_model=InventarioUsuarioResponse)
def obter_item_inventario(
    item_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")

    return item


@router.put("/{item_id}", response_model=InventarioUsuarioResponse)
def atualizar_item_inventario(
    item_id: int,
    obj_in: InventarioUsuarioUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Atualiza dados do item. Não permite reduzir abaixo da quantidade reservada."""
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")

    if item.status == "cancelado":
        raise HTTPException(status_code=400, detail="Item cancelado não pode ser atualizado.")

    if obj_in.tipo_residuo is not None:
        tipo_residuo = _normalizar_tipo_residuo(obj_in.tipo_residuo)
        if not validar_residuo(tipo_residuo):
            raise HTTPException(status_code=400, detail="Tipo de resíduo não aceito.")
        item.tipo_residuo = tipo_residuo

    if obj_in.quantidade is not None:
        if not validar_quantidade(obj_in.quantidade):
            raise HTTPException(status_code=400, detail="Quantidade inválida. O valor deve estar entre 1 e 1000.")
        if obj_in.quantidade < float(item.quantidade_reservada or 0):
            raise HTTPException(
                status_code=400,
                detail="A quantidade total não pode ser menor que a quantidade reservada em descartes pendentes.",
            )
        item.quantidade = obj_in.quantidade

    if obj_in.descricao is not None:
        item.descricao = obj_in.descricao
    if obj_in.observacao is not None:
        item.observacao = obj_in.observacao
    if obj_in.status is not None:
        if obj_in.status not in STATUS_PERMITIDOS:
            raise HTTPException(status_code=400, detail="Status inválido.")
        item.status = obj_in.status
    else:
        _recalcular_status(item)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}")
def remover_item_inventario(
    item_id: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Remove logicamente o item do inventário, desde que não haja quantidade reservada."""
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")

    if float(item.quantidade_reservada or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover item com quantidade reservada em descarte pendente.",
        )

    item.status = "cancelado"
    db.commit()

    return {"mensagem": "Item removido do inventário com sucesso.", "id": item.id, "status": item.status}


@router.post("/{item_id}/descartar", response_model=DescarteResponse)
def descartar_item_inventario(
    item_id: int,
    obj_in: InventarioUsuarioTransferir,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """
    Cria um descarte pendente usando um item do inventário pessoal.

    O item fica reservado até a confirmação pela cooperativa/admin. Na confirmação,
    a quantidade confirmada é baixada do inventário do usuário e transferida para
    o inventário do ponto de coleta.
    """
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")

    if item.status in {"cancelado", "finalizado"}:
        raise HTTPException(status_code=400, detail="Item indisponível para descarte.")

    if not validar_quantidade(obj_in.quantidade):
        raise HTTPException(status_code=400, detail="Quantidade inválida. O valor deve estar entre 1 e 1000.")

    disponivel = _quantidade_disponivel(item)
    if obj_in.quantidade > disponivel:
        raise HTTPException(
            status_code=400,
            detail=f"Quantidade indisponível no inventário. Disponível: {disponivel} kg.",
        )

    ponto = db.query(PontoColeta).filter(PontoColeta.id == obj_in.ponto_coleta_id).first()
    if not ponto:
        raise_not_found("Ponto de coleta não encontrado.")
    validar_ponto_disponivel_para_descarte(ponto)

    validacao_qrcode = False
    qr_token = None

    if obj_in.qrcode_token:
        qr_token = db.query(QRCodeToken).filter(
            QRCodeToken.token == obj_in.qrcode_token,
            QRCodeToken.ponto_coleta_id == obj_in.ponto_coleta_id,
            QRCodeToken.ativo == 1,
            QRCodeToken.data_expiracao > datetime.utcnow(),
        ).first()
        if not qr_token:
            raise HTTPException(status_code=403, detail="Token QR Code inválido ou expirado.")
        validacao_qrcode = True
    else:
        if not validar_localizacao(
            obj_in.usuario_lat,
            obj_in.usuario_long,
            ponto.latitude,
            ponto.longitude,
            ponto.raio_operacao,
        ):
            raise HTTPException(status_code=403, detail="Muito longe do ponto de coleta.")

    novo_descarte = Descarte(
        quantidade=obj_in.quantidade,
        tipo_residuo=item.tipo_residuo,
        observacao=obj_in.observacao,
        status="pendente",
        usuario_id=usuario.id,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
        ponto_lat=ponto.latitude,
        ponto_long=ponto.longitude,
        ponto_coleta_id=ponto.id,
        qrcode_token_id=qr_token.id if validacao_qrcode else None,
        inventario_usuario_id=item.id,
    )

    item.quantidade_reservada = float(item.quantidade_reservada or 0) + float(obj_in.quantidade)
    _recalcular_status(item)

    db.add(novo_descarte)
    db.commit()
    db.refresh(novo_descarte)

    if validacao_qrcode and qr_token:
        qr_token.descarte_id = novo_descarte.id_descarte
        qr_token.ativo = 0
        db.commit()
        db.refresh(qr_token)

    return novo_descarte
