"""
Modelo de Inventário do Usuário

Armazena os resíduos cadastrados pelo usuário antes da transferência
para um ponto de coleta.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class InventarioUsuario(Base):
    """
    Inventário temporário de resíduos vinculados ao usuário.

    quantidade: total ainda pertencente ao usuário.
    quantidade_reservada: quantidade vinculada a descartes pendentes.
    status:
      - disponivel: possui saldo disponível para transferência.
      - em_transferencia: todo o saldo está reservado em descarte pendente.
      - finalizado: sem saldo e sem reserva.
      - cancelado: item cancelado/removido logicamente.
    """
    __tablename__ = "inventario_usuario"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=False, index=True)
    tipo_residuo = Column(String(50), nullable=False)
    quantidade = Column(Float, nullable=False, default=0)
    quantidade_reservada = Column(Float, nullable=False, default=0)
    descricao = Column(String(255), nullable=True)
    observacao = Column(String(500), nullable=True)
    status = Column(String(30), nullable=False, default="disponivel")
    data_cadastro = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    usuario = relationship("Usuario", back_populates="inventarios")
    descartes = relationship("Descarte", back_populates="inventario_usuario")
