"""Modelos de campanhas e inscrições.

Uma campanha é uma forma de gerar engajamento, com a marca do patrocinador
em evidência. No momento, participar de uma campanha acumula pontos para o
usuário.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
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

    # "publica": os bônus valem para quem participa. "privada": além de
    # participar, é preciso cumprir os requisitos de entrada (papel "entrada").
    acesso = Column(String(20), nullable=False, default="publica", server_default="publica")

    # Texto livre exibido ao morador antes da adesão (TSK-MOR-023).
    condicoes = Column(Text, nullable=True)

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
    requisitos = relationship(
        "CampanhaRequisito",
        back_populates="campanha",
        cascade="all, delete-orphan",
        order_by="CampanhaRequisito.id",
    )
    mecanicas = relationship(
        "CampanhaMecanica",
        back_populates="campanha",
        cascade="all, delete-orphan",
        order_by="CampanhaMecanica.id",
    )


class CampanhaMecanica(Base):
    """Mecânica de bônus que o admin liga ou desliga em cada campanha.

    Cada campanha pode ter uma mecânica de cada tipo. A configuração (`config`)
    depende do tipo. Tipos atuais: "dobro_pontos" (config: tipo_residuo,
    codigos_barras, quantidade). Novas mecânicas entram como novos tipos.
    """

    __tablename__ = "campanha_mecanica"
    __table_args__ = (
        UniqueConstraint("campanha_id", "tipo", name="uq_campanha_mecanica_tipo"),
    )

    id = Column(Integer, primary_key=True, index=True)
    campanha_id = Column(Integer, ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)
    ativa = Column(Boolean, nullable=False, default=True, server_default="true")
    config = Column(JSON, nullable=False, default=dict)

    campanha = relationship("Campanha", back_populates="mecanicas")


class CampanhaRequisito(Base):
    """Condição medida em descartes confirmados.

    papel "entrada": em campanha privada, precisa estar cumprido para liberar
    os bônus. papel "missao": precisa estar cumprido para receber a recompensa.
    Ambos contam só descartes feitos depois da adesão. Filtros vazios
    significam "qualquer descarte confirmado".
    """

    __tablename__ = "campanha_requisito"

    id = Column(Integer, primary_key=True, index=True)
    campanha_id = Column(Integer, ForeignKey("campanhas.id", ondelete="CASCADE"), nullable=False, index=True)
    papel = Column(String(20), nullable=False)
    descricao = Column(String(255), nullable=True)
    tipo_residuo = Column(String(50), nullable=True)
    codigos_barras = Column(JSON, nullable=True)
    quantidade = Column(Integer, nullable=False)

    campanha = relationship("Campanha", back_populates="requisitos")


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
    # Preenchido quando a recompensa da campanha é paga (uma única vez).
    recompensa_concedida_em = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    campanha = relationship("Campanha", back_populates="inscricoes")
    usuario = relationship("Usuario")


class CampanhaBonus(Base):
    """Bônus de uma mecânica já pago a uma adesão (no máximo um por mecânica)."""

    __tablename__ = "campanha_bonus"
    __table_args__ = (
        UniqueConstraint("inscricao_id", "mecanica", name="uq_campanha_bonus_inscricao_mecanica"),
    )

    id = Column(Integer, primary_key=True, index=True)
    inscricao_id = Column(Integer, ForeignKey("inscricao_campanha.id", ondelete="CASCADE"), nullable=False, index=True)
    mecanica = Column(String(30), nullable=False)
    pontos = Column(Integer, nullable=False)
    concedido_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
