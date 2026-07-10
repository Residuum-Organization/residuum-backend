"""
Modelo de Pontuação

Define a estrutura da tabela 'pontuacao' no banco de dados.
Registra pontos ganhos pelos usuários ao longo do tempo.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Pontuacao(Base):
    """
    Modelo SQLAlchemy para a tabela de pontuações.

    Registra cada ganho de pontos de um usuário com data e hora.
    """
    __tablename__ = "pontuacao"

    # Chave primária
    id_pontuacao = Column(Integer, primary_key=True, index=True)

    # Pontos ganhos (obrigatório)
    pontos = Column(Integer, nullable=False)

    # Data e hora do registro (padrão: agora)
    data_reg = Column(DateTime(timezone=True), server_default=func.now())

    # Relacionamento com usuário
    usuario_id = Column(Integer, ForeignKey("usuario.id"))
    usuario = relationship("Usuario", back_populates="pontuacoes")