"""Regras de uso do voucher: instrucoes e validade do codigo."""

from datetime import datetime, timedelta, timezone

from app.models.resgate_voucher import ResgateVoucher
from app.models.voucher import Voucher

STATUS_EXPIRADO = "expirado"
# Data exibida ao morador: horario de Manaus (UTC-4, sem horario de verao).
FUSO_EXIBICAO = timezone(timedelta(hours=-4))


def calcular_validade(voucher: Voucher, agora: datetime) -> datetime | None:
    """Data limite de uso de um codigo resgatado agora; None se nao ha prazo."""
    if not voucher.validade_codigo_dias:
        return None
    return agora + timedelta(days=int(voucher.validade_codigo_dias))


def _como_utc(valor: datetime) -> datetime:
    return valor if valor.tzinfo else valor.replace(tzinfo=timezone.utc)


def status_do_resgate(resgate: ResgateVoucher, agora: datetime | None = None) -> str:
    """Status exibido: um codigo ativo vencido aparece como expirado."""
    agora = agora or datetime.now(timezone.utc)
    if (
        resgate.status == "ativo"
        and resgate.valido_ate is not None
        and _como_utc(resgate.valido_ate) < agora
    ):
        return STATUS_EXPIRADO
    return resgate.status


def montar_instrucoes(voucher: Voucher, valido_ate: datetime | None = None) -> str:
    """Instrucoes objetivas de uso.

    Usa o texto do admin quando existe; senao, os passos padrao. A linha de
    validade vem sempre que houver prazo: a data exata se o codigo ja foi
    resgatado, ou o numero de dias se ainda nao foi.
    """
    texto = (voucher.instrucoes or "").strip()
    if not texto:
        texto = "\n".join(
            [
                "1. Resgate o voucher. O código aparece em Meus resgates.",
                f"2. Informe o código ao parceiro {voucher.parceiro} na hora de usar o benefício.",
                "3. Cada código vale uma única vez.",
            ]
        )

    if valido_ate is not None:
        texto += f"\nUse até {_como_utc(valido_ate).astimezone(FUSO_EXIBICAO).strftime('%d/%m/%Y')}."
    elif voucher.validade_codigo_dias:
        texto += f"\nO código vale por {int(voucher.validade_codigo_dias)} dias a partir do resgate."
    return texto
