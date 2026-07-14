from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship

from app.database import Base

class Agenda(Base):
    __tablename__ = "agendas"

    id = Column(Integer, primary_key=True, index=True)
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=False)
    data = Column(Date, nullable=False)
    turno_id = Column(String(50), nullable=False)
    status = Column(String(50), default="agendado", nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)

    ponto_coleta = relationship("PontoColeta")
