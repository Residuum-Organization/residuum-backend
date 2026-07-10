"""Modelo de bilhete/cupom de sorteio.

Cada bilhete tem uma numeracao sequencial dentro do sorteio (usada para
realizar o sorteio a partir das numerações) e é limitado a 1 por usuário
por sorteio.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class BilheteSorteio(Base):
    __tablename__ = "bilhete_sorteio"
    __table_args__ = (
        # Regra: somente 1 cupom por usuário por sorteio.
        UniqueConstraint("sorteio_id", "usuario_id", name="uq_bilhete_sorteio_usuario"),
        # Numeração única dentro do sorteio.
        UniqueConstraint("sorteio_id", "numero", name="uq_bilhete_sorteio_numero"),
    )

    id = Column(Integer, primary_key=True, index=True)
    sorteio_id = Column(Integer, ForeignKey("sorteios.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)

    numero = Column(Integer, nullable=False)
    pontos_utilizados = Column(Integer, nullable=False)

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    sorteio = relationship("Sorteio")
    usuario = relationship("Usuario")
