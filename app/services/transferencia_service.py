from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.models.ponto_coleta import PontoColeta
from fastapi import HTTPException
import json


def transferir_residuo_para_ponto_coleta(
    tipo_residuo: str,
    quantidade: float,
    ponto_coleta_id: int,
    db: Session
) -> dict:
    if not tipo_residuo or quantidade <= 0:
        raise HTTPException(
            status_code=400,
            detail="Tipo de resíduo ou quantidade inválida."
        )

    ponto = db.query(PontoColeta).filter(PontoColeta.id == ponto_coleta_id).first()

    if not ponto:
        raise HTTPException(
            status_code=404,
            detail="Ponto de coleta não encontrado."
        )

    inventario_atual = ponto.inventario or {}

    if isinstance(inventario_atual, str):
        try:
            inventario_atual = json.loads(inventario_atual)
        except Exception:
            inventario_atual = {}

    # cria uma nova cópia para o SQLAlchemy perceber a alteração
    novo_inventario = dict(inventario_atual)

    quantidade_atual = float(novo_inventario.get(tipo_residuo, 0))
    novo_inventario[tipo_residuo] = quantidade_atual + float(quantidade)

    ponto.inventario = novo_inventario

    # força o SQLAlchemy a reconhecer alteração no campo JSON
    flag_modified(ponto, "inventario")

    return {
        "tipo_residuo": tipo_residuo,
        "quantidade_transferida": quantidade,
        "novo_estoque": novo_inventario.get(tipo_residuo, 0),
        "ponto_coleta_id": ponto_coleta_id,
        "inventario_atualizado": novo_inventario,
        "status": "transferencia_registrada"
    }


def debitar_residuo_do_ponto_coleta(
    tipo_residuo: str,
    quantidade: float,
    ponto_coleta_id: int,
    db: Session
) -> dict:
    """
    Estorna (debita) uma quantidade de resíduo do inventário de um ponto de coleta.

    Espelha `transferir_residuo_para_ponto_coleta`, mas subtrai do estoque sem
    permitir saldo negativo. Usado ao reverter um descarte já confirmado.
    Não faz commit — o caller decide quando comitar.
    """
    if not tipo_residuo or quantidade <= 0:
        raise HTTPException(
            status_code=400,
            detail="Tipo de resíduo ou quantidade inválida."
        )

    ponto = db.query(PontoColeta).filter(PontoColeta.id == ponto_coleta_id).first()

    if not ponto:
        raise HTTPException(
            status_code=404,
            detail="Ponto de coleta não encontrado."
        )

    inventario_atual = ponto.inventario or {}

    if isinstance(inventario_atual, str):
        try:
            inventario_atual = json.loads(inventario_atual)
        except Exception:
            inventario_atual = {}

    # cria uma nova cópia para o SQLAlchemy perceber a alteração
    novo_inventario = dict(inventario_atual)

    quantidade_atual = float(novo_inventario.get(tipo_residuo, 0))
    novo_inventario[tipo_residuo] = max(quantidade_atual - float(quantidade), 0.0)

    ponto.inventario = novo_inventario

    # força o SQLAlchemy a reconhecer alteração no campo JSON
    flag_modified(ponto, "inventario")

    return {
        "tipo_residuo": tipo_residuo,
        "quantidade_debitada": quantidade,
        "novo_estoque": novo_inventario.get(tipo_residuo, 0),
        "ponto_coleta_id": ponto_coleta_id,
        "inventario_atualizado": novo_inventario,
        "status": "estorno_registrado"
    }
