"""
Serviço de auditoria — grava entradas de AuditLog para ações administrativas.
"""

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def registrar_acao(
    db: Session,
    *,
    admin_id: int,
    action: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    motivo: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> AuditLog:
    """Cria uma entrada no audit log. Não faz commit — o caller decide."""
    entry = AuditLog(
        admin_id=admin_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        motivo=motivo,
        payload=payload,
    )
    db.add(entry)
    db.flush()
    return entry
