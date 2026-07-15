"""
Modelo de solicitacao de ponto de coleta.

Armazena pedidos feitos por usuarios autenticados para cadastro futuro de
pontos de coleta, sem ativar o ponto diretamente.
"""

from sqlalchemy import JSON, CheckConstraint, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SolicitacaoPontoColeta(Base):
    __tablename__ = "solicitacao_ponto_coleta"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendente', 'aprovada', 'rejeitada', 'cancelada')",
            name="ck_solicitacao_ponto_coleta_status",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)

    tipo_solicitante = Column(String(50), nullable=False)
    documento = Column(String(30), nullable=False)
    responsavel_nome = Column(String(255), nullable=False)
    responsavel_telefone = Column(String(30), nullable=False)
    email = Column(String(255), nullable=False)

    nome_ponto = Column(String(255), nullable=False)
    endereco = Column(String(500), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    horario_funcionamento = Column(String(255), nullable=True)
    tipos_residuos_aceitos = Column(JSON, default=list, nullable=False)
    capacidade_maxima = Column(Float, nullable=True)

    status = Column(String(20), nullable=False, default="pendente", server_default="pendente")
    motivo_rejeicao = Column(String(500), nullable=True)
    observacao_admin = Column(String(500), nullable=True)

    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=True, index=True)
    revisado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)

    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    revisado_em = Column(DateTime(timezone=True), nullable=True)

    usuario = relationship("Usuario", foreign_keys=[usuario_id])
    ponto_coleta = relationship("PontoColeta", foreign_keys=[ponto_coleta_id])
    revisado_por = relationship("Usuario", foreign_keys=[revisado_por_id])
