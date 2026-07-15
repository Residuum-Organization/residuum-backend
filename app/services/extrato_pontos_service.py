"""Servicos para montar o extrato consolidado de pontos do usuario."""

from sqlalchemy.orm import Session

from app.models.descarte import Descarte
from app.models.campanha import InscricaoCampanha
from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.usuario import Usuario
from app.services.serializacao_service import (
    serializar_evento_extrato_descarte,
    serializar_evento_extrato_resgate,
)


def montar_extrato_pontos_usuario(
    usuario: Usuario,
    db: Session,
    limit: int | None = None,
) -> dict[str, object]:
    """Retorna o extrato consolidado de pontos do usuario autenticado."""
    descartes = (
        db.query(Descarte)
        .filter(Descarte.usuario_id == usuario.id)
        .order_by(Descarte.data_desc.desc())
        .all()
    )
    resgates = (
        db.query(ResgatePontuacao)
        .filter(ResgatePontuacao.usuario_id == usuario.id)
        .order_by(ResgatePontuacao.data_resgate.desc())
        .all()
    )
    inscricoes = (
        db.query(InscricaoCampanha)
        .filter(InscricaoCampanha.usuario_id == usuario.id)
        .order_by(InscricaoCampanha.criado_em.desc())
        .all()
    )

    itens = [serializar_evento_extrato_descarte(descarte, db) for descarte in descartes]
    itens.extend(serializar_evento_extrato_resgate(resgate) for resgate in resgates)
    itens.extend(
        {
            "origem": "campanha",
            "status": "confirmado",
            "data_evento": inscricao.criado_em,
            "pontos": int(inscricao.pontos_concedidos or 0),
            "descricao": f"Participacao na campanha: {inscricao.campanha.titulo}",
            "referencia": f"campanha:{inscricao.campanha_id}",
            "quantidade": None,
            "tipo_residuo": None,
            "ponto_coleta_id": None,
            "ponto_coleta_nome": None,
            "ponto_coleta_endereco": None,
            "id_descarte": None,
            "id_resgate": None,
            "id_inscricao": inscricao.id,
            "inventario_usuario_id": None,
            "inventario_item_descricao": f"Campanha: {inscricao.campanha.titulo}",
        }
        for inscricao in inscricoes
    )
    itens.sort(key=lambda item: item["data_evento"], reverse=True)

    if limit is not None:
        itens = itens[:limit]

    return {
        "pontuacao_total": int(usuario.pontuacao_total or 0),
        "itens": itens,
    }
