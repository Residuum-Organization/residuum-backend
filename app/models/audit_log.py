"""
Modelo de Audit Log para ações administrativas.

Registra quem fez o quê, sobre qual recurso e quando — para rastreabilidade
de operações sensíveis (mudança de role, ajuste de pontuação, remoção, etc.).
"""

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    action = Column(String(60), nullable=False, index=True)
    target_type = Column(String(40), nullable=True, index=True)
    target_id = Column(Integer, nullable=True, index=True)
    motivo = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
