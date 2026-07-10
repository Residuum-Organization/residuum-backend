"""
Modelo de Token QR Code

Define a estrutura da tabela 'qrcode_token' no banco de dados.
Armazena tokens únicos gerados pelos pontos de coleta para validação presencial.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class QRCodeToken(Base):
    """
    Modelo SQLAlchemy para tokens de QR Code.

    Cada ponto de coleta gera um token único que serve como validação presencial.
    """
    __tablename__ = "qrcode_token"

    # Chave primária
    id = Column(Integer, primary_key=True, index=True)

    # Token único (UUID em formato string)
    token = Column(String(36), unique=True, nullable=False, index=True)

    # Referência ao ponto de coleta
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=False)

    # Data de geração e expiração
    data_geracao = Column(DateTime(timezone=True), server_default=func.now())
    data_expiracao = Column(DateTime(timezone=True), nullable=False)

    # Status do token (1 = ativo, 0 = expirado/usado)
    ativo = Column(Integer, default=1)

    # Referência ao descarte que usou este token (se houver)
    descarte_id = Column(Integer, ForeignKey("descarte.id_descarte"), nullable=True)

    # Relationships
    ponto_coleta = relationship("PontoColeta", back_populates="qrcode_tokens")
    descarte = relationship("Descarte", back_populates="qrcode_token", uselist=False, foreign_keys="[Descarte.qrcode_token_id]")

