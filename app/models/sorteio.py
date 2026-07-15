"""Modelo de sorteios."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Sorteio(Base):
    """Sorteio disponivel para consulta no frontend."""

    __tablename__ = "sorteios"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    premio = Column(String(255), nullable=False)
    custo_pontos = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(30), nullable=False, default="ativo", server_default="ativo")
    data_inicio = Column(DateTime(timezone=True), nullable=True)
    data_fim = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    bilhetes = relationship(
        "BilheteSorteio",
        back_populates="sorteio",
        cascade="all, delete-orphan",
    )

    @property
    def total_bilhetes(self) -> int:
        return len(self.bilhetes)
