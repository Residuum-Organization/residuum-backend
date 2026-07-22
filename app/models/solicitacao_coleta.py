from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SolicitacaoColeta(Base):
    __tablename__ = "solicitacao_coleta"

    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True)
    cooperativa_id = Column(Integer, ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False, index=True)
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id", ondelete="RESTRICT"), nullable=False, index=True)

    status = Column(String(30), nullable=False, server_default="solicitada", index=True)
    percentual_ocupacao = Column(Float, nullable=True)
    quantidade_inventario = Column(Float, nullable=False)
    inventario_solicitado = Column(JSON, nullable=False, default=dict)
    quantidade_coletada = Column(Float, nullable=True)
    capacidade_maxima = Column(Float, nullable=True)
    observacao = Column(Text, nullable=True)
    motivo_recusa = Column(Text, nullable=True)
    data_solicitacao = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    data_aceite = Column(DateTime(timezone=True), nullable=True)
    data_conclusao = Column(DateTime(timezone=True), nullable=True)
    data_atualizacao = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    admin = relationship("Usuario", foreign_keys=[admin_id])
    cooperativa = relationship("Usuario", foreign_keys=[cooperativa_id])
    ponto_coleta = relationship("PontoColeta", back_populates="solicitacoes_coleta")
