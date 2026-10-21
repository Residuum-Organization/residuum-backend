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
from types import SimpleNamespace

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import raise_bad_request, raise_forbidden, raise_not_found
from app.models.campanha import Campanha, CampanhaBonus, CampanhaRequisito, InscricaoCampanha
from app.services.pontuacao_service import calcular_pontos_proporcionais
from app.models.descarte import Descarte
from app.models.inventario_usuario import InventarioUsuario
from app.models.pontuacao import Pontuacao
from app.models.usuario import Usuario


def _aware(valor: datetime | None) -> datetime | None:
    if valor is not None and valor.tzinfo is None:
        return valor.replace(tzinfo=timezone.utc)
    return valor


def normalizar_config_mecanica(tipo: str, config: dict) -> dict:
    """Valida e normaliza a configuração de uma mecânica."""
    if tipo == "dobro_pontos":
        try:
            quantidade = int(config.get("quantidade"))
        except (TypeError, ValueError):
            quantidade = 0
        if quantidade < 1:
            raise_bad_request("Dobro de pontos: informe a quantidade de unidades necessária (1 ou mais).")
        tipo_residuo = str(config.get("tipo_residuo") or "").strip() or None
        codigos = []
        for codigo in config.get("codigos_barras") or []:
            texto = str(codigo).strip()
            if texto and texto not in codigos:
                codigos.append(texto)
        if not tipo_residuo and not codigos:
            raise_bad_request("Dobro de pontos: informe o resíduo (material e/ou código de barras).")
        return {"tipo_residuo": tipo_residuo, "codigos_barras": codigos, "quantidade": quantidade}
    raise_bad_request(f"Mecânica desconhecida: {tipo}.")


def validar_mecanicas(mecanicas: list) -> list[dict]:
    """Normaliza as mecânicas de uma campanha (uma por tipo)."""
    tipos = [m.tipo for m in mecanicas]
    if len(tipos) != len(set(tipos)):
        raise_bad_request("Cada mecânica só pode aparecer uma vez por campanha.")
    return [
        {"tipo": m.tipo, "ativa": m.ativa, "config": normalizar_config_mecanica(m.tipo, m.config)}
        for m in mecanicas
    ]


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


def _progresso_dobro_pontos(db, usuario_id, mecanica, desde, fim, participando, acesso_liberado, concedida) -> dict:
    """Meta de unidades do resíduo definido; o bônus é o dobro dos pontos dessas unidades."""
    config = mecanica.config or {}
    quantidade = int(config.get("quantidade") or 0)
    filtro = SimpleNamespace(
        tipo_residuo=config.get("tipo_residuo"),
        codigos_barras=list(config.get("codigos_barras") or []),
    )
    atual = contar_unidades(db, usuario_id, filtro, desde, fim) if participando else 0
    cumprida = quantidade > 0 and atual >= quantidade
    return {
        "tipo": mecanica.tipo,
        "atual": min(atual, quantidade),
        "quantidade": quantidade,
        "cumprida": cumprida,
        # Bônus = mesmos pontos básicos das unidades da meta (dobra o que elas valem).
        "pontos": calcular_pontos_proporcionais(quantidade, quantidade),
        "disponivel": acesso_liberado and cumprida and not concedida,
        "concedida": concedida,
        "tipo_residuo": filtro.tipo_residuo,
        "codigos_barras": filtro.codigos_barras,
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

    bonus_pagos = set()
    if participando:
        bonus_pagos = {
            linha.mecanica
            for linha in db.query(CampanhaBonus).filter(CampanhaBonus.inscricao_id == inscricao.id).all()
        }
    mecanicas = [
        _progresso_dobro_pontos(db, usuario.id, m, desde, fim, participando, acesso_liberado, m.tipo in bonus_pagos)
        for m in campanha.mecanicas
        if m.ativa and m.tipo == "dobro_pontos"
    ]

    return {
        "campanha_id": campanha.id,
        "acesso": campanha.acesso,
        "participando": participando,
        "entrada": entrada,
        "missoes": missoes,
        "mecanicas": mecanicas,
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


def conceder_bonus_mecanica(db: Session, campanha: Campanha, usuario: Usuario, tipo: str) -> CampanhaBonus:
    """Paga o bônus de uma mecânica ligada, uma única vez por adesão."""
    # Trava a adesão para que dois cliques simultâneos não paguem duas vezes.
    inscricao = obter_inscricao(db, campanha.id, usuario.id, bloquear=True)
    if inscricao is None:
        raise_forbidden("Participe da campanha para receber os bônus.")

    estado = avaliar(db, campanha, usuario)
    item = next((m for m in estado["mecanicas"] if m["tipo"] == tipo), None)
    if item is None:
        raise_not_found("Esta mecânica não está ativa nesta campanha.")
    if item["concedida"]:
        raise_bad_request("O bônus desta mecânica já foi recebido.")
    if not estado["acesso_liberado"]:
        raise_forbidden("Cumpra os requisitos de entrada para liberar os bônus desta campanha privada.")
    if not item["cumprida"]:
        raise_bad_request("Conclua a meta da mecânica para receber o bônus.")

    dono = db.query(Usuario).filter(Usuario.id == usuario.id).with_for_update().first()
    dono.pontuacao_total = int(dono.pontuacao_total or 0) + item["pontos"]
    db.add(Pontuacao(pontos=item["pontos"], usuario_id=dono.id))
    bonus = CampanhaBonus(inscricao_id=inscricao.id, mecanica=tipo, pontos=item["pontos"])
    db.add(bonus)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise_bad_request("O bônus desta mecânica já foi recebido.")
    db.refresh(bonus)
    return bonus


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
