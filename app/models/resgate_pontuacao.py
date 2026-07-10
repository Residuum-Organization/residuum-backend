"""
Modelo de Resgate de Pontuacao.

Registra eventos de consumo de pontos pelo usuario para compor o extrato
com status `resgatado`.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ResgatePontuacao(Base):
    """Modelo SQLAlchemy para resgates de pontos."""

    __tablename__ = "resgate_pontuacao"

    id_resgate = Column(Integer, primary_key=True, index=True)
    pontos_utilizados = Column(Integer, nullable=False)
    descricao = Column(String(255), nullable=False)
    referencia = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="resgatado", server_default="resgatado")
    data_resgate = Column(DateTime(timezone=True), server_default=func.now())

    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    usuario = relationship("Usuario", back_populates="resgates_pontuacao")
