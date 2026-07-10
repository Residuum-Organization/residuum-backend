from sqlalchemy import Column, ForeignKey, Integer, String, Boolean, DateTime
from datetime import datetime
from app.database import Base

class Notificacao(Base):
    __tablename__ = "notificacoes"

    id = Column(Integer, primary_key=True, index=True)
    mensagem = Column(String, nullable=False)
    tipo = Column(String, default="ponto_cheio")
    lida = Column(Boolean, default=False)
    criado_em = Column(DateTime(timezone=True), default=datetime.utcnow)
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=True)