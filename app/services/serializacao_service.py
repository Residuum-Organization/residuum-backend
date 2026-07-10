"""
Serviços auxiliares de serialização de respostas da API.

Centraliza a montagem de respostas enriquecidas para evitar que o front-end
receba apenas IDs em telas como histórico, pendentes e perfil.
"""

from typing import Any
from sqlalchemy.orm import Session

from app.models.descarte import Descarte
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.usuario import Usuario
from app.models.ponto_coleta import PontoColeta
from app.models.inventario_usuario import InventarioUsuario
from app.services.pontuacao_service import calcular_pontos_proporcionais


def serializar_endereco(usuario: Usuario) -> dict[str, Any] | None:
    """Retorna o endereço do usuário em JSON simples."""
    if usuario.endereco is None:
        return None

    return {
        "id_end": usuario.endereco.id_end,
        "rua": usuario.endereco.rua,
        "bairro": usuario.endereco.bairro,
        "numero": usuario.endereco.numero,
        "cep": usuario.endereco.cep,
        "cidade": usuario.endereco.cidade,
    }


def serializar_usuario_basico(usuario: Usuario) -> dict[str, Any]:
    """Retorna os dados básicos do usuário autenticado."""
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "telefone": usuario.telefone,
        "pontuacao_total": usuario.pontuacao_total or 0,
        "role": usuario.role,
        "endereco": serializar_endereco(usuario),
    }


def serializar_inventario_item(item: InventarioUsuario) -> dict[str, Any]:
    """Retorna um item de inventário com quantidade disponível calculada."""
    quantidade = float(item.quantidade or 0)
    quantidade_reservada = float(item.quantidade_reservada or 0)

    return {
        "id": item.id,
        "usuario_id": item.usuario_id,
        "tipo_residuo": item.tipo_residuo,
        "quantidade": quantidade,
        "quantidade_reservada": quantidade_reservada,
        "quantidade_disponivel": max(quantidade - quantidade_reservada, 0),
        "descricao": item.descricao,
        "observacao": item.observacao,
        "status": item.status,
        "data_cadastro": item.data_cadastro,
        "data_atualizacao": item.data_atualizacao,
    }


def serializar_descarte(descarte: Descarte, db: Session) -> dict[str, Any]:
    """
    Retorna um descarte enriquecido com nomes reais.

    Antes, o front recebia apenas usuario_id e ponto_coleta_id. Agora a resposta
    inclui usuario_nome e ponto_coleta_nome, mantendo os IDs para rastreabilidade.
    """
    usuario = None
    if descarte.usuario_id:
        usuario = db.query(Usuario).filter(Usuario.id == descarte.usuario_id).first()

    ponto = None
    if descarte.ponto_coleta_id:
        ponto = db.query(PontoColeta).filter(PontoColeta.id == descarte.ponto_coleta_id).first()

    item_inventario = None
    if descarte.inventario_usuario_id:
        item_inventario = db.query(InventarioUsuario).filter(
            InventarioUsuario.id == descarte.inventario_usuario_id
        ).first()

    return {
        "id_descarte": descarte.id_descarte,
        "data_desc": descarte.data_desc,
        "quantidade": descarte.quantidade,
        "tipo_residuo": descarte.tipo_residuo,
        "observacao": descarte.observacao,
        "status": descarte.status,
        "quantidade_confirmada": descarte.quantidade_confirmada,
        "usuario_id": descarte.usuario_id,
        "usuario_nome": usuario.nome if usuario else None,
        "usuario_email": usuario.email if usuario else None,
        "ponto_coleta_id": descarte.ponto_coleta_id,
        "ponto_coleta_nome": ponto.nome if ponto else None,
        "ponto_coleta_endereco": ponto.endereco if ponto else None,
        "usuario_lat": descarte.usuario_lat,
        "usuario_long": descarte.usuario_long,
        "ponto_lat": descarte.ponto_lat,
        "ponto_long": descarte.ponto_long,
        "qrcode_token_id": descarte.qrcode_token_id,
        "inventario_usuario_id": descarte.inventario_usuario_id,
        "inventario_item_descricao": item_inventario.descricao if item_inventario else None,
    }


def serializar_evento_extrato_descarte(descarte: Descarte, db: Session) -> dict[str, Any]:
    """Converte um descarte em um item de extrato de pontos."""
    evento = serializar_descarte(descarte, db)
    quantidade_base = float(descarte.quantidade or 0)
    pontos = 0

    if descarte.status == "confirmado":
        pontos = calcular_pontos_proporcionais(
            quantidade_base,
            float(descarte.quantidade_confirmada or 0),
        )
    elif descarte.status == "pendente":
        pontos = calcular_pontos_proporcionais(quantidade_base, quantidade_base)

    return {
        "origem": "descarte",
        "status": descarte.status,
        "data_evento": descarte.data_desc,
        "pontos": pontos,
        "descricao": descarte.observacao,
        "referencia": None,
        "quantidade": float(descarte.quantidade or 0),
        "tipo_residuo": descarte.tipo_residuo,
        "ponto_coleta_id": evento["ponto_coleta_id"],
        "ponto_coleta_nome": evento["ponto_coleta_nome"],
        "ponto_coleta_endereco": evento["ponto_coleta_endereco"],
        "id_descarte": descarte.id_descarte,
        "id_resgate": None,
        "inventario_usuario_id": descarte.inventario_usuario_id,
        "inventario_item_descricao": evento["inventario_item_descricao"],
    }


def serializar_resgate_pontuacao(resgate: ResgatePontuacao) -> dict[str, Any]:
    """Serializa um resgate de pontos para respostas da API."""
    return {
        "id_resgate": resgate.id_resgate,
        "usuario_id": resgate.usuario_id,
        "pontos_utilizados": resgate.pontos_utilizados,
        "descricao": resgate.descricao,
        "referencia": resgate.referencia,
        "status": resgate.status,
        "data_resgate": resgate.data_resgate,
    }


def serializar_evento_extrato_resgate(resgate: ResgatePontuacao) -> dict[str, Any]:
    """Converte um resgate em um item de extrato de pontos."""
    return {
        "origem": "resgate",
        "status": resgate.status,
        "data_evento": resgate.data_resgate,
        "pontos": -abs(int(resgate.pontos_utilizados or 0)),
        "descricao": resgate.descricao,
        "referencia": resgate.referencia,
        "quantidade": None,
        "tipo_residuo": None,
        "ponto_coleta_id": None,
        "ponto_coleta_nome": None,
        "ponto_coleta_endereco": None,
        "id_descarte": None,
        "id_resgate": resgate.id_resgate,
        "inventario_usuario_id": None,
        "inventario_item_descricao": resgate.descricao,
    }
