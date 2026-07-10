"""Modelos de campanhas e inscrições.

Uma campanha é uma forma de gerar engajamento, com a marca do patrocinador
em evidência. No momento, participar de uma campanha acumula pontos para o
usuário.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Campanha(Base):
    __tablename__ = "campanhas"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)

    # Patrocinador em evidência na campanha.
    patrocinador = Column(String(255), nullable=False)
    patrocinador_logo_url = Column(String(500), nullable=True)

    # Pontos concedidos ao participar da campanha.
    pontos_recompensa = Column(Integer, nullable=False, default=0, server_default="0")

    status = Column(String(30), nullable=False, default="ativa", server_default="ativa")
    data_inicio = Column(DateTime(timezone=True), nullable=True)
    data_fim = Column(DateTime(timezone=True), nullable=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    inscricoes = relationship(
        "InscricaoCampanha", back_populates="campanha", cascade="all, delete-orphan"
    )


class InscricaoCampanha(Base):
    __tablename__ = "inscricao_campanha"
    __table_args__ = (
        # Um usuário participa de cada campanha uma única vez.
        UniqueConstraint("campanha_id", "usuario_id", name="uq_inscricao_campanha_usuario"),
    )

    id = Column(Integer, primary_key=True, index=True)
    campanha_id = Column(Integer, ForeignKey("campanhas.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)

    pontos_concedidos = Column(Integer, nullable=False, default=0, server_default="0")
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    campanha = relationship("Campanha", back_populates="inscricoes")
    usuario = relationship("Usuario")
