"""
Modelo de Ponto de Coleta

Define a estrutura da tabela 'ponto_coleta' no banco de dados.
Armazena informações dos pontos de coleta de resíduos com localização, inventário
e dados operacionais usados na visualização do mapa/detalhes.
"""

from sqlalchemy import JSON, Column, DateTime, Float, Integer, String, Time, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class HorarioDisponibilidade(Base):
    __tablename__ = "horarios_disponibilidade"

    id = Column(Integer, primary_key=True, index=True)
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id", ondelete="CASCADE"), nullable=False)    
    # 0 = Domingo, 1 = Segunda, ..., 6 = Sábado
    dia_semana = Column(Integer, nullable=False) 
    hora_abertura = Column(Time, nullable=False)
    hora_fechamento = Column(Time, nullable=False)

    # Relacionamento de volta para o ponto de coleta
    ponto_coleta = relationship("PontoColeta", back_populates="horarios")
    
class PontoColeta(Base):
    """
    Modelo SQLAlchemy para a tabela de pontos de coleta.

    Contém localização (latitude/longitude), informações operacionais do ponto,
    tipos aceitos, capacidade e inventário.
    """
    __tablename__ = "ponto_coleta"

    # Chave primária
    id = Column(Integer, primary_key=True, index=True)

    # Informações do ponto de coleta
    nome = Column(String(255), nullable=False)
    endereco = Column(String(500))

    # Coordenadas (GPS)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    # Raio de operação em metros (padrão: 1000m = 1km)
    raio_operacao = Column(Float, default=1000.0)

    # Informações adicionais exigidas para detalhes do ponto (RF008)
    capacidade_maxima = Column(Float, nullable=True)  # capacidade total estimada em kg
    tipos_residuos_aceitos = Column(JSON, default=list)  # ex.: ["plastico", "papel"]
    horario_funcionamento = Column(String(255), nullable=True)
    status = Column(String(20), default="ativo")  # ativo, cheio, inativo
    cooperativa_id = Column(Integer, ForeignKey("usuario.id"), nullable=True, index=True)

    # Inventário de resíduos (tipo_residuo -> quantidade)
    inventario = Column(JSON, default=dict)

    # Controle de criação e atualização
    data_criacao = Column(DateTime(timezone=True), server_default=func.now())
    data_atualizacao = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
    data_final = Column(DateTime(timezone=True), nullable=True)
    # Compatibilidade com versões anteriores: 1 = ativo, 0 = inativo
    ativo = Column(Integer, default=1)

    # Relationships
    cooperativa_responsavel = relationship("Usuario", foreign_keys=[cooperativa_id])
    descartes = relationship("Descarte", back_populates="ponto_coleta")
    qrcode_tokens = relationship("QRCodeToken", back_populates="ponto_coleta")
    horarios = relationship("HorarioDisponibilidade", back_populates="ponto_coleta")