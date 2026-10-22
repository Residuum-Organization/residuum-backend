"""Operacoes de saldo de pontos com a linha do usuario travada.

Todo debito passa por aqui: a linha do usuario e bloqueada (SELECT ... FOR
UPDATE), o saldo e relido do banco e o debito entra no extrato com a origem.
Assim dois resgates paralelos nao gastam o mesmo saldo duas vezes.
"""

from sqlalchemy.orm import Session

from app.models.resgate_pontuacao import ResgatePontuacao
from app.models.usuario import Usuario

ORIGEM_RESGATE = "resgate"
ORIGEM_VOUCHER = "voucher"
ORIGEM_SORTEIO = "sorteio"


class SaldoInsuficiente(Exception):
    """O usuario nao tem pontos suficientes para a operacao."""


def travar_usuario(db: Session, usuario_id: int) -> Usuario:
    """Bloqueia a linha do usuario e recarrega o saldo atual do banco."""
    return (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id)
        .populate_existing()
        .with_for_update()
        .one()
    )


def debitar_pontos(
    db: Session,
    usuario_id: int,
    pontos: int,
    *,
    origem: str,
    descricao: str,
    referencia: str | None = None,
) -> ResgatePontuacao:
    """Debita pontos do usuario e registra o evento no extrato.

    Levanta SaldoInsuficiente se o saldo nao cobre o valor. Nao faz commit.
    """
    if pontos < 0:
        raise ValueError("O valor a debitar nao pode ser negativo.")

    usuario = travar_usuario(db, usuario_id)
    saldo = int(usuario.pontuacao_total or 0)
    if pontos > saldo:
        raise SaldoInsuficiente()

    usuario.pontuacao_total = saldo - pontos
    resgate = ResgatePontuacao(
        usuario_id=usuario.id,
        pontos_utilizados=pontos,
        descricao=descricao,
        referencia=referencia,
        origem=origem,
        status="resgatado",
    )
    db.add(resgate)
    return resgate
