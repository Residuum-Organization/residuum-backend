from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base

class Cooperativa(Base):
    __tablename__ = "cooperativa"
    id = Column(Integer, primary_key=True, index=True)
    nome_razaoSocial = Column(String(100), nullable=False)
    cnpj_cpf = Column(String(20), nullable=False, unique=True)
    endereco = Column(String(200), nullable=False)
    telefone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    residuos_aceitos = Column(String(200), nullable=True)
    agenda_funcionamento = Column(String(200), nullable=True)
    historico_coleta = Column(String(500), nullable=True)
    status = Column(String(20), nullable=False, default="ativo")

    # Relationships
    pontos_coleta = relationship("PontoColeta", back_populates="cooperativa")