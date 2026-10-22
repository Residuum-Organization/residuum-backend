"""Modelo de resgate de voucher.

Registra o resgate de um voucher por um usuario, guardando o codigo
promocional gerado e a quantidade de pontos consumida.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ResgateVoucher(Base):
    __tablename__ = "resgate_voucher"
    __table_args__ = (
        # Reenvio com a mesma chave devolve o resgate existente.
        UniqueConstraint("usuario_id", "chave_idempotencia", name="uq_resgate_voucher_chave"),
    )

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(Integer, ForeignKey("vouchers.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)

    codigo = Column(String(40), nullable=False, unique=True, index=True)
    pontos_utilizados = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="ativo", server_default="ativo")
    chave_idempotencia = Column(String(80), nullable=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    voucher = relationship("Voucher")
    usuario = relationship("Usuario")
