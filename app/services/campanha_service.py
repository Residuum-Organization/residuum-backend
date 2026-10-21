"""Regras de campanhas: acesso, requisitos medidos em descartes e recompensa.

Regras (definidas pelo produto em 2026-10-21):
- participar é gratuito, mas só quem aperta "Participar" recebe os bônus;
- aderir não paga pontos; a recompensa vem de cumprir as missões;
- NENHUM descarte conta para a campanha antes da adesão (entrada e missões);
- campanha privada: os requisitos de entrada são o primeiro desafio depois da
  adesão e liberam os bônus quando cumpridos;
- requisitos contam descartes confirmados (por material e/ou código de barras).

A mecânica atual é a de missões. Outras mecânicas (ex.: dobro de pontos) virão
conforme as parcerias e entram neste módulo.
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import raise_bad_request, raise_forbidden
from app.models.campanha import Campanha, CampanhaRequisito, InscricaoCampanha
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.pontuacao import Pontuacao
from app.models.usuario import Usuario


def _aware(valor: datetime | None) -> datetime | None:
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


def validar_definicao(acesso: str, pontos_recompensa: int, requisitos: list) -> None:
    """Valida a combinação acesso/requisitos/recompensa de uma campanha."""
    entrada = [r for r in requisitos if r.papel == "entrada"]
    missoes = [r for r in requisitos if r.papel == "missao"]
    if acesso == "privada" and not entrada:
        raise_bad_request("Campanha privada precisa de ao menos um requisito de entrada.")
    if acesso == "publica" and entrada:
        raise_bad_request("Requisito de entrada só existe em campanha privada.")
    if (pontos_recompensa or 0) > 0 and not missoes:
        raise_bad_request("Defina ao menos uma missão para a campanha pagar pontos de recompensa.")


def contar_unidades(
    db: Session,
    usuario_id: int,
    requisito: CampanhaRequisito,
    desde: datetime | None,
    ate: datetime | None,
) -> int:
    """Soma as unidades de descartes confirmados que atendem ao requisito."""
    codigo = func.coalesce(Descarte.codigo_barras_validado, InventarioUsuario.codigo_barras)
    consulta = (
        db.query(func.coalesce(func.sum(func.coalesce(Descarte.quantidade_confirmada, Descarte.quantidade)), 0))
        .outerjoin(InventarioUsuario, Descarte.inventario_usuario_id == InventarioUsuario.id)
        .filter(Descarte.usuario_id == usuario_id, Descarte.status == "confirmado")
    )
    if desde is not None:
        consulta = consulta.filter(Descarte.data_desc >= desde)
    if ate is not None:
        consulta = consulta.filter(Descarte.data_desc <= ate)
    if requisito.tipo_residuo:
        consulta = consulta.filter(func.lower(Descarte.tipo_residuo) == requisito.tipo_residuo.lower())
    codigos = list(requisito.codigos_barras or [])
    if codigos:
        consulta = consulta.filter(codigo.in_(codigos))
    return int(consulta.scalar() or 0)


def obter_inscricao(db: Session, campanha_id: int, usuario_id: int, bloquear: bool = False):
    consulta = db.query(InscricaoCampanha).filter(
        InscricaoCampanha.campanha_id == campanha_id,
        InscricaoCampanha.usuario_id == usuario_id,
    )
    if bloquear:
        consulta = consulta.with_for_update()
    return consulta.first()


def _progresso_requisito(requisito: CampanhaRequisito, atual: int) -> dict:
    return {
        "id": requisito.id,
        "papel": requisito.papel,
        "descricao": requisito.descricao,
        "tipo_residuo": requisito.tipo_residuo,
        "codigos_barras": list(requisito.codigos_barras or []),
        "quantidade": requisito.quantidade,
        "atual": min(atual, requisito.quantidade),
        "cumprido": atual >= requisito.quantidade,
    }


def avaliar(db: Session, campanha: Campanha, usuario: Usuario) -> dict:
    """Progresso do morador na campanha.

    Nada conta antes da adesão: quem não aperta "Participar" não acumula
    progresso nem recebe bônus. Entrada e missões contam descartes confirmados
    a partir do momento da adesão, dentro da vigência.
    """
    inscricao = obter_inscricao(db, campanha.id, usuario.id)
    participando = inscricao is not None
    inicio = _aware(campanha.data_inicio)
    fim = _aware(campanha.data_fim)

    desde = None
    if participando:
        adesao = _aware(inscricao.criado_em)
        desde = max(inicio, adesao) if inicio else adesao

    def progresso(papel: str) -> list[dict]:
        return [
            _progresso_requisito(
                r,
                contar_unidades(db, usuario.id, r, desde, fim) if participando else 0,
            )
            for r in campanha.requisitos
            if r.papel == papel
        ]

    entrada = progresso("entrada")
    missoes = progresso("missao")

    entrada_cumprida = all(item["cumprido"] for item in entrada)
    missoes_cumpridas = bool(missoes) and all(item["cumprido"] for item in missoes)
    # Na campanha privada, os bônus só valem depois de cumprir a entrada.
    acesso_liberado = participando and (campanha.acesso != "privada" or entrada_cumprida)
    concedida = bool(inscricao and inscricao.recompensa_concedida_em)
    pontos = int(campanha.pontos_recompensa or 0)

    return {
        "campanha_id": campanha.id,
        "acesso": campanha.acesso,
        "participando": participando,
        "entrada": entrada,
        "missoes": missoes,
        "entrada_cumprida": entrada_cumprida,
        "missoes_cumpridas": missoes_cumpridas,
        "acesso_liberado": acesso_liberado,
        "pode_participar": not participando,
        "recompensa_pontos": pontos,
        "recompensa_disponivel": acesso_liberado and not concedida and missoes_cumpridas and pontos > 0,
        "recompensa_concedida": concedida,
    }


def aderir(db: Session, campanha: Campanha, usuario: Usuario) -> InscricaoCampanha:
    """Registra a participação (gratuita, também nas privadas). Não credita pontos."""
    if obter_inscricao(db, campanha.id, usuario.id):
        raise_bad_request("Você já participa desta campanha.")

    inscricao = InscricaoCampanha(campanha_id=campanha.id, usuario_id=usuario.id, pontos_concedidos=0)
    db.add(inscricao)
    try:
        db.commit()
    except IntegrityError:
        # Reenvio simultâneo: a restrição única já garante uma adesão por usuário.
        db.rollback()
        raise_bad_request("Você já participa desta campanha.")
    db.refresh(inscricao)
    return inscricao


def conceder_recompensa(db: Session, campanha: Campanha, usuario: Usuario) -> InscricaoCampanha:
    """Paga a recompensa uma única vez, se a adesão existe e as missões estão cumpridas."""
    # Trava a adesão para que dois cliques simultâneos não paguem duas vezes.
    inscricao = obter_inscricao(db, campanha.id, usuario.id, bloquear=True)
    if inscricao is None:
        raise_forbidden("Participe da campanha para receber os bônus.")
    if inscricao.recompensa_concedida_em is not None:
        raise_bad_request("A recompensa desta campanha já foi recebida.")

    estado = avaliar(db, campanha, usuario)
    if not estado["acesso_liberado"]:
        raise_forbidden("Cumpra os requisitos de entrada para liberar os bônus desta campanha privada.")
    if not estado["missoes_cumpridas"]:
        raise_bad_request("Conclua todas as missões da campanha para receber a recompensa.")
    pontos = estado["recompensa_pontos"]
    if pontos <= 0:
        raise_bad_request("Esta campanha não paga pontos de recompensa.")

    dono = db.query(Usuario).filter(Usuario.id == usuario.id).with_for_update().first()
    dono.pontuacao_total = int(dono.pontuacao_total or 0) + pontos
    db.add(Pontuacao(pontos=pontos, usuario_id=dono.id))
    inscricao.pontos_concedidos = pontos
    inscricao.recompensa_concedida_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(inscricao)
    return inscricao
