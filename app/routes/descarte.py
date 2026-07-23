"""Registro, consulta e confirmação de descartes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions import raise_bad_request
from app.database import get_db
from app.dependencies.auth import get_current_user, require_role, validar_acesso_operacional_ao_ponto
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.pontuacao import Pontuacao
from app.models.ponto_coleta import PontoColeta
from app.models.usuario import Usuario
from app.schemas.descarte import DescarteConfirmar, DescarteCreate, DescarteResponse
from app.services.identificacao_residuo_service import (
    normalizar_codigo_barras,
    validar_identificacao_confirmacao,
)
from app.services.localizacao_service import validar_localizacao
from app.services.notificacao_service import verificar_capacidade_e_notificar
from app.services.ponto_coleta_service import (
    validar_ponto_disponivel_para_descarte,
    validar_residuo_aceito_no_ponto,
)
from app.services.pontuacao_service import calcular_pontos_proporcionais
from app.services.serializacao_service import serializar_descarte
from app.services.transferencia_service import transferir_residuo_para_ponto_coleta
from app.services.transferencia_lote_service import atualizar_status_transferencia_lote
from app.services.validacao_service import validar_quantidade, validar_residuo

router = APIRouter(prefix="/descarte", tags=["Descarte"])


@router.post("/", response_model=DescarteResponse)
async def registrar_descarte(
    obj_in: DescarteCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    """Registra um descarte pendente, com presença validada exclusivamente por GPS."""
    if not validar_quantidade(obj_in.quantidade):
        raise HTTPException(
            status_code=400,
            detail="Quantidade inválida. O valor deve estar entre 1 e 1000.",
        )
    tipo_residuo = obj_in.tipo_residuo.strip().lower()
    if not validar_residuo(tipo_residuo):
        raise HTTPException(status_code=400, detail="Tipo de resíduo não aceito.")

    usuario_bd = db.query(Usuario).filter(Usuario.id == usuario.id).first()
    if not usuario_bd:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    ponto = db.query(PontoColeta).filter(PontoColeta.id == obj_in.ponto_coleta_id).first()
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto de coleta não encontrado.")
    validar_ponto_disponivel_para_descarte(ponto)
    validar_residuo_aceito_no_ponto(ponto, tipo_residuo)
    if not validar_localizacao(
        obj_in.usuario_lat,
        obj_in.usuario_long,
        ponto.latitude,
        ponto.longitude,
        ponto.raio_operacao,
    ):
        raise HTTPException(status_code=403, detail="Você está muito longe do ponto de coleta.")

    novo_descarte = Descarte(
        quantidade=obj_in.quantidade,
        quantidade_confirmada=obj_in.quantidade,
        tipo_residuo=tipo_residuo,
        observacao=obj_in.observacao,
        status="confirmado",
        usuario_id=usuario_bd.id,
        usuario_lat=obj_in.usuario_lat,
        usuario_long=obj_in.usuario_long,
        usuario_precisao=obj_in.usuario_precisao,
        ponto_lat=ponto.latitude,
        ponto_long=ponto.longitude,
        ponto_coleta_id=ponto.id,
        identificado_em=datetime.now(timezone.utc),
    )
    
    pontos = calcular_pontos_proporcionais(obj_in.quantidade, obj_in.quantidade)
    if pontos > 0:
        usuario_bd.pontuacao_total = (usuario_bd.pontuacao_total or 0) + pontos
        db.add(Pontuacao(pontos=pontos, usuario_id=usuario_bd.id))
    db.add(novo_descarte)
    db.commit()
    db.refresh(novo_descarte)
    return novo_descarte


@router.get("/historico")
async def ver_historico(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_current_user),
):
    descartes = (
        db.query(Descarte)
        .filter(Descarte.usuario_id == usuario.id)
        .order_by(Descarte.data_desc.desc())
        .all()
    )
    return [serializar_descarte(descarte, db) for descarte in descartes]


@router.get("/historico/geral")
async def ver_historico_geral(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_role("admin")),
):
    descartes = db.query(Descarte).order_by(Descarte.data_desc.desc()).all()
    return [serializar_descarte(descarte, db) for descarte in descartes]


@router.get("/pendentes")
async def listar_descartes_pendentes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(require_role("admin", "cooperativa")),
):
    """Lista o histórico de descartes do ponto de coleta."""
    query = db.query(Descarte)

    if usuario.role == "cooperativa":
        query = query.join(PontoColeta, Descarte.ponto_coleta_id == PontoColeta.id).filter(
            PontoColeta.cooperativa_id == usuario.id
        )
    descartes = query.order_by(Descarte.data_desc.desc()).all()
    return [serializar_descarte(descarte, db) for descarte in descartes]


def _validar_identificacao_do_ponto(
    descarte: Descarte,
    item: InventarioUsuario | None,
    obj_in: DescarteConfirmar,
) -> tuple[str | None, bool, str | None]:
    if item:
        return validar_identificacao_confirmacao(
            codigo_cadastrado=item.codigo_barras,
            item_sem_rotulo=bool(item.sem_rotulo),
            codigo_validado=obj_in.codigo_barras_validado,
            confirmado_sem_rotulo=obj_in.sem_rotulo,
            identificacao_manual=obj_in.identificacao_manual,
        )

    codigo = normalizar_codigo_barras(obj_in.codigo_barras_validado)
    descricao = (obj_in.identificacao_manual or "").strip() or None
    if obj_in.sem_rotulo:
        if codigo:
            raise ValueError("Não informe código de barras para uma embalagem sem rótulo.")
        if not descricao:
            raise ValueError("Descreva manualmente o produto sem rótulo.")
        return None, True, descricao
    if not codigo:
        raise ValueError("Escaneie o código de barras antes de confirmar o descarte.")
    return codigo, False, None


@router.put("/{id_descarte}/confirmar")
async def confirmar_descarte(
    id_descarte: int,
    obj_in: DescarteConfirmar,
    db: Session = Depends(get_db),
    usuario_operador: Usuario = Depends(require_role("admin", "cooperativa"))
):
    """
    Confirma o descarte e calcula pontos (RF014).
    
    Apenas admin ou a conta do ponto de coleta podem confirmar.
    O sistema calcula 10 pontos por cada 1kg confirmado.
    """
    descarte = db.query(Descarte).filter(Descarte.id_descarte == id_descarte).first()
    if not descarte:
        raise HTTPException(status_code=404, detail="Descarte não encontrado.")
    if descarte.ponto_coleta_id is None:
        raise_bad_request("Descarte sem ponto de coleta vinculado.")

    usuario = db.query(Usuario).filter(
        Usuario.id == descarte.usuario_id
    ).with_for_update().first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário do descarte não encontrado.")

    ponto = db.query(PontoColeta).filter(
        PontoColeta.id == descarte.ponto_coleta_id
    ).with_for_update().first()
    if not ponto:
        raise HTTPException(status_code=404, detail="Ponto de coleta não encontrado.")

    validar_acesso_operacional_ao_ponto(usuario_operador, ponto)
    if descarte.status != "pendente":
        raise HTTPException(status_code=409, detail="Apenas descartes pendentes podem ser confirmados.")
    if obj_in.quantidade_confirmada > float(descarte.quantidade):
        raise HTTPException(
            status_code=400,
            detail="A quantidade confirmada não pode ser maior que a quantidade declarada.",
        )

    item_inventario = None
    if descarte.inventario_usuario_id:
        item_inventario = db.query(InventarioUsuario).filter(
            InventarioUsuario.id == descarte.inventario_usuario_id,
            InventarioUsuario.usuario_id == descarte.usuario_id,
        ).with_for_update().first()

    try:
        codigo, sem_rotulo, descricao_manual = _validar_identificacao_do_ponto(
            descarte,
            item_inventario,
            obj_in,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    descarte.codigo_barras_validado = codigo
    descarte.sem_rotulo_validado = sem_rotulo
    descarte.identificacao_manual = descricao_manual
    descarte.identificado_em = datetime.now(timezone.utc)
    descarte.identificado_por_id = usuario_operador.id

    pontos = calcular_pontos_proporcionais(descarte.quantidade, obj_in.quantidade_confirmada)
    descarte.quantidade_confirmada = obj_in.quantidade_confirmada
    descarte.status = "confirmado"
    usuario.pontuacao_total = (usuario.pontuacao_total or 0) + pontos
    if pontos > 0:
        db.add(Pontuacao(pontos=pontos, usuario_id=usuario.id))

    if item_inventario:
        item_inventario.quantidade_reservada = max(
            float(item_inventario.quantidade_reservada or 0) - float(descarte.quantidade),
            0,
        )
        item_inventario.quantidade = max(
            float(item_inventario.quantidade or 0) - float(obj_in.quantidade_confirmada),
            0,
        )
        if item_inventario.quantidade <= 0 and item_inventario.quantidade_reservada <= 0:
            item_inventario.status = "finalizado"
        elif item_inventario.quantidade - item_inventario.quantidade_reservada <= 0:
            item_inventario.status = "em_transferencia"
        else:
            item_inventario.status = "disponivel"

    transferir_residuo_para_ponto_coleta(
        descarte.tipo_residuo,
        obj_in.quantidade_confirmada,
        descarte.ponto_coleta_id,
        db,
    )

    atualizar_status_transferencia_lote(db, descarte.transferencia_lote_id)

    db.commit()
    db.refresh(descarte)
    if descarte.ponto_coleta:
        verificar_capacidade_e_notificar(db, descarte.ponto_coleta)

    return {
        "mensagem": "Descarte confirmado com sucesso!",
        "id_descarte": descarte.id_descarte,
        "status": descarte.status,
        "quantidade_confirmada": descarte.quantidade_confirmada,
        "pontos_gerados": pontos,
        "pontuacao_total_usuario": usuario.pontuacao_total,
    }
