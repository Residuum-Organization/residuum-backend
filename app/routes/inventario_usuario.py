"""Rotas do inventário pessoal e transferências para pontos de coleta."""

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.ponto_coleta import PontoColeta
from app.models.pontuacao import Pontuacao
from app.models.transferencia_lote import TransferenciaLote
from app.models.usuario import Usuario
from app.schemas.descarte import DescarteResponse
from app.schemas.inventario_usuario import (
    InventarioLoteTransferir,
    InventarioUsuarioCreate,
    InventarioUsuarioResponse,
    InventarioUsuarioTransferir,
    InventarioUsuarioUpdate,
    TransferenciaLoteResponse,
)
from app.services.identificacao_residuo_service import validar_identificacao_cadastro
from app.services.localizacao_service import validar_localizacao
from app.services.ponto_coleta_service import (
    validar_ponto_disponivel_para_descarte,
    validar_residuo_aceito_no_ponto,
)
from app.services.pontuacao_service import calcular_pontos_proporcionais
from app.services.validacao_service import validar_quantidade, validar_residuo

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


def _validar_ponto_e_gps(
    db: Session,
    *,
    ponto_coleta_id: int,
    usuario_lat: float,
    usuario_long: float,
) -> PontoColeta:
    ponto = db.query(PontoColeta).filter(PontoColeta.id == ponto_coleta_id).first()
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto de coleta não encontrado.")

    validar_ponto_disponivel_para_descarte(ponto)
    if not validar_localizacao(
        usuario_lat,
        usuario_long,
        ponto.latitude,
        ponto.longitude,
        ponto.raio_operacao,
    ):
        raise HTTPException(status_code=403, detail="Você está muito longe do ponto de coleta.")

    return ponto


def _validar_item_para_transferencia(item: InventarioUsuario, quantidade: float) -> None:
    if item.status in {"cancelado", "finalizado"}:
        raise HTTPException(status_code=400, detail=f"Item #{item.id} indisponível para descarte.")
    if not validar_quantidade(quantidade):
        raise HTTPException(
            status_code=400,
            detail=f"Quantidade inválida para o item #{item.id}. O valor deve estar entre 1 e 1000.",
        )

    disponivel = _quantidade_disponivel(item)
    if quantidade > disponivel:
        raise HTTPException(
            status_code=400,
            detail=f"Quantidade indisponível no item #{item.id}. Disponível: {disponivel} kg.",
        )


def _serializar_lote(lote: TransferenciaLote) -> dict:
    return {
        "id": lote.id,
        "status": lote.status,
        "ponto_coleta_id": lote.ponto_coleta_id,
        "ponto_coleta_nome": lote.ponto_coleta.nome,
        "total_itens": lote.total_itens,
        "peso_total": lote.peso_total,
        "pontos_estimados": lote.pontos_estimados,
        "descarte_ids": [descarte.id_descarte for descarte in lote.descartes],
        "data_criacao": lote.data_criacao,
    }


def _buscar_lote_por_idempotencia(
    db: Session,
    usuario_id: int,
    chave_idempotencia: str,
) -> TransferenciaLote | None:
    return db.query(TransferenciaLote).filter(
        TransferenciaLote.usuario_id == usuario_id,
        TransferenciaLote.chave_idempotencia == chave_idempotencia,
    ).first()


@router.post("", response_model=InventarioUsuarioResponse)
def cadastrar_item_inventario(
    obj_in: InventarioUsuarioCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    tipo_residuo = _normalizar_tipo_residuo(obj_in.tipo_residuo)
    if not validar_residuo(tipo_residuo):
        raise HTTPException(status_code=400, detail="Tipo de resíduo não aceito.")
    if not validar_quantidade(obj_in.quantidade):
        raise HTTPException(
            status_code=400,
            detail="Quantidade inválida. O valor deve estar entre 1 e 1000.",
        )

    item = InventarioUsuario(
        usuario_id=usuario.id,
        tipo_residuo=tipo_residuo,
        quantidade=obj_in.quantidade,
        quantidade_reservada=0,
        descricao=obj_in.descricao,
        observacao=obj_in.observacao,
        codigo_barras=obj_in.codigo_barras,
        sem_rotulo=obj_in.sem_rotulo,
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
    query = db.query(InventarioUsuario).filter(InventarioUsuario.usuario_id == usuario.id)
    if status:
        query = query.filter(InventarioUsuario.status == status)
    return query.order_by(InventarioUsuario.data_cadastro.desc()).all()


@router.post("/transferencias", response_model=TransferenciaLoteResponse)
def transferir_itens_em_lote(
    obj_in: InventarioLoteTransferir,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Reserva vários itens em uma única transação idempotente."""
    lote_existente = _buscar_lote_por_idempotencia(
        db,
        usuario.id,
        obj_in.chave_idempotencia,
    )
    if lote_existente:
        return _serializar_lote(lote_existente)

    ponto = _validar_ponto_e_gps(
        db,
        ponto_coleta_id=obj_in.ponto_coleta_id,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
    )
    itens_por_id = {
        item.id: item
        for item in db.query(InventarioUsuario)
        .filter(
            InventarioUsuario.usuario_id == usuario.id,
            InventarioUsuario.id.in_([entrada.item_id for entrada in obj_in.itens]),
        )
        .with_for_update()
        .all()
    }
    if len(itens_por_id) != len(obj_in.itens):
        raise HTTPException(status_code=404, detail="Um ou mais itens do inventário não foram encontrados.")

    # Uma requisição concorrente pode ter criado o lote enquanto aguardávamos
    # o bloqueio dos itens. A repetição deve devolver o resultado original.
    lote_existente = _buscar_lote_por_idempotencia(
        db,
        usuario.id,
        obj_in.chave_idempotencia,
    )
    if lote_existente:
        return _serializar_lote(lote_existente)

    peso_total = 0.0
    for entrada in obj_in.itens:
        item = itens_por_id[entrada.item_id]
        _validar_item_para_transferencia(item, entrada.quantidade)
        validar_residuo_aceito_no_ponto(ponto, item.tipo_residuo)
        peso_total += float(entrada.quantidade)

    lote = TransferenciaLote(
        id=str(uuid4()),
        usuario_id=usuario.id,
        ponto_coleta_id=ponto.id,
        chave_idempotencia=obj_in.chave_idempotencia,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
        usuario_precisao=obj_in.usuario_precisao,
        status="confirmado",
        total_itens=len(obj_in.itens),
        peso_total=peso_total,
        pontos_estimados=calcular_pontos_proporcionais(peso_total, peso_total),
    )
    db.add(lote)

    pontos_totais_ganhos = lote.pontos_estimados
    if pontos_totais_ganhos > 0:
        usuario.pontuacao_total = (usuario.pontuacao_total or 0) + pontos_totais_ganhos
        db.add(Pontuacao(pontos=pontos_totais_ganhos, usuario_id=usuario.id))

    for entrada in obj_in.itens:
        item = itens_por_id[entrada.item_id]
        item.quantidade = max(float(item.quantidade or 0) - float(entrada.quantidade), 0.0)
        _recalcular_status(item)
        db.add(
            Descarte(
                quantidade=entrada.quantidade,
                quantidade_confirmada=entrada.quantidade,
                tipo_residuo=item.tipo_residuo,
                observacao=obj_in.observacao,
                status="confirmado",
                usuario_id=usuario.id,
                usuario_lat=obj_in.usuario_lat,
                usuario_long=obj_in.usuario_long,
                usuario_precisao=obj_in.usuario_precisao,
                ponto_lat=ponto.latitude,
                ponto_long=ponto.longitude,
                ponto_coleta_id=ponto.id,
                inventario_usuario_id=item.id,
                transferencia_lote_id=lote.id,
                identificado_em=datetime.now(timezone.utc) if hasattr(datetime, 'now') else None,
            )
        )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        lote = _buscar_lote_por_idempotencia(
            db,
            usuario.id,
            obj_in.chave_idempotencia,
        )
        if not lote:
            raise
        return _serializar_lote(lote)

    db.refresh(lote)
    return _serializar_lote(lote)


@router.get("/transferencias/{lote_id}", response_model=TransferenciaLoteResponse)
def obter_transferencia_em_lote(
    lote_id: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    lote = db.query(TransferenciaLote).filter(
        TransferenciaLote.id == lote_id,
        TransferenciaLote.usuario_id == usuario.id,
    ).first()
    if not lote:
        raise HTTPException(status_code=404, detail="Transferência não encontrada.")
    return _serializar_lote(lote)


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
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")
    if item.status == "cancelado":
        raise HTTPException(status_code=400, detail="Item cancelado não pode ser atualizado.")

    campos = obj_in.model_fields_set
    identificacao_alterada = bool({"codigo_barras", "sem_rotulo"} & campos)
    if identificacao_alterada and float(item.quantidade_reservada or 0) > 0:
        raise HTTPException(
            status_code=409,
            detail="A identificação não pode ser alterada enquanto houver descarte pendente.",
        )

    if identificacao_alterada:
        sem_rotulo = obj_in.sem_rotulo if "sem_rotulo" in campos else bool(item.sem_rotulo)
        codigo_barras = obj_in.codigo_barras if "codigo_barras" in campos else item.codigo_barras
        try:
            codigo_barras = validar_identificacao_cadastro(codigo_barras, sem_rotulo)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        item.sem_rotulo = sem_rotulo
        item.codigo_barras = codigo_barras

    if obj_in.tipo_residuo is not None:
        tipo_residuo = _normalizar_tipo_residuo(obj_in.tipo_residuo)
        if not validar_residuo(tipo_residuo):
            raise HTTPException(status_code=400, detail="Tipo de resíduo não aceito.")
        item.tipo_residuo = tipo_residuo
    if obj_in.quantidade is not None:
        if not validar_quantidade(obj_in.quantidade):
            raise HTTPException(
                status_code=400,
                detail="Quantidade inválida. O valor deve estar entre 1 e 1000.",
            )
        if obj_in.quantidade < float(item.quantidade_reservada or 0):
            raise HTTPException(
                status_code=400,
                detail="A quantidade total não pode ser menor que a quantidade reservada.",
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
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")
    if float(item.quantidade_reservada or 0) > 0:
        raise HTTPException(
            status_code=400,
            detail="Não é possível remover item com quantidade reservada.",
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
    item = db.query(InventarioUsuario).filter(
        InventarioUsuario.id == item_id,
        InventarioUsuario.usuario_id == usuario.id,
    ).with_for_update().first()
    if not item:
        raise HTTPException(status_code=404, detail="Item do inventário não encontrado.")

    _validar_item_para_transferencia(item, obj_in.quantidade)
    ponto = _validar_ponto_e_gps(
        db,
        ponto_coleta_id=obj_in.ponto_coleta_id,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
    )
    validar_residuo_aceito_no_ponto(ponto, item.tipo_residuo)
    novo_descarte = Descarte(
        quantidade=obj_in.quantidade,
        quantidade_confirmada=obj_in.quantidade,
        tipo_residuo=item.tipo_residuo,
        observacao=obj_in.observacao,
        status="confirmado",
        usuario_id=usuario.id,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
        usuario_precisao=obj_in.usuario_precisao,
        ponto_lat=ponto.latitude,
        ponto_long=ponto.longitude,
        ponto_coleta_id=ponto.id,
        inventario_usuario_id=item.id,
    )
    
    pontos = calcular_pontos_proporcionais(obj_in.quantidade, obj_in.quantidade)
    if pontos > 0:
        usuario.pontuacao_total = (usuario.pontuacao_total or 0) + pontos
        db.add(Pontuacao(pontos=pontos, usuario_id=usuario.id))
        
    item.quantidade = max(float(item.quantidade or 0) - float(obj_in.quantidade), 0.0)
    _recalcular_status(item)

    db.add(novo_descarte)
    db.commit()
    db.refresh(novo_descarte)
    return novo_descarte
