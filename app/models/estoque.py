from sqlalchemy import Column, Integer, Float, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class Estoque(Base):
    __tablename__ = "estoque"
    
    id_estoque = Column(Integer, primary_key=True, index=True)
    tipo_residuo = Column(String(50), unique=True, nullable=False)
    quantidade_total = Column(Float, default=0.0)
    ultima_atualizacao = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())