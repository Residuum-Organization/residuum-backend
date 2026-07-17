"""Modelo da transferência atômica de itens do inventário."""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class TransferenciaLote(Base):
    __tablename__ = "transferencia_lote"
    __table_args__ = (
        UniqueConstraint(
            "usuario_id",
            "chave_idempotencia",
            name="uq_transferencia_lote_usuario_idempotencia",
        ),
    )

    id = Column(String(36), primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=False)
    chave_idempotencia = Column(String(128), nullable=False)
    usuario_lat = Column(Float, nullable=False)
    usuario_long = Column(Float, nullable=False)
    usuario_precisao = Column(Float, nullable=True)
    status = Column(String(20), nullable=False, default="pendente", server_default="pendente")
    total_itens = Column(Integer, nullable=False)
    peso_total = Column(Float, nullable=False)
    pontos_estimados = Column(Integer, nullable=False)
    data_criacao = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    usuario = relationship("Usuario")
    ponto_coleta = relationship("PontoColeta")
    descartes = relationship("Descarte", back_populates="transferencia_lote")
