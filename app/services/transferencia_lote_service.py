"""Atualização consistente do estado de transferências em lote."""

from sqlalchemy.orm import Session

from app.models.descarte import Descarte
from app.models.transferencia_lote import TransferenciaLote


def calcular_status_lote(status_descartes: list[str]) -> str:
    if not status_descartes or "pendente" in status_descartes:
        return "pendente"
    if all(status == "confirmado" for status in status_descartes):
        return "confirmado"
    if all(status == "rejeitado" for status in status_descartes):
        return "rejeitado"
    return "parcial"


def atualizar_status_transferencia_lote(db: Session, lote_id: str | None) -> None:
    if not lote_id:
        return

    lote = db.query(TransferenciaLote).filter(TransferenciaLote.id == lote_id).first()
    if not lote:
        return

    status_descartes = [
        status
        for (status,) in db.query(Descarte.status).filter(
            Descarte.transferencia_lote_id == lote_id
        ).all()
    ]
    lote.status = calcular_status_lote(status_descartes)
