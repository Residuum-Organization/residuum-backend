from sqlalchemy import Boolean, Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Descarte(Base):
    __tablename__ = "descarte"
    id_descarte = Column(Integer, primary_key=True, index=True)
    data_desc = Column(DateTime(timezone=True), server_default=func.now())
    quantidade = Column(Float, nullable=False)
    tipo_residuo = Column(String(50))
    observacao = Column(String(500))
    status = Column(String(20), default='pendente')
    quantidade_confirmada = Column(Float, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    usuario_lat = Column(Float, nullable=True)
    usuario_long = Column(Float, nullable=True)
    usuario_precisao = Column(Float, nullable=True)
    ponto_lat = Column(Float, nullable=True)
    ponto_long = Column(Float, nullable=True)
    # Referência ao ponto de coleta
    ponto_coleta_id = Column(Integer, ForeignKey("ponto_coleta.id"), nullable=True)
    # Token QR Code usado (se validação presencial)
    qrcode_token_id = Column(Integer, ForeignKey("qrcode_token.id"), nullable=True)
    codigo_barras_validado = Column(String(64), nullable=True)
    sem_rotulo_validado = Column(Boolean, nullable=False, default=False, server_default="false")
    identificacao_manual = Column(String(255), nullable=True)
    identificado_em = Column(DateTime(timezone=True), nullable=True)
    identificado_por_id = Column(Integer, ForeignKey("usuario.id"), nullable=True)
    transferencia_lote_id = Column(
        String(36),
        ForeignKey("transferencia_lote.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Item do inventário do usuário que originou o descarte, quando aplicável

    # Relationships
    usuario = relationship("Usuario", back_populates="descartes", foreign_keys=[usuario_id])
    identificado_por = relationship("Usuario", foreign_keys=[identificado_por_id])
    ponto_coleta = relationship("PontoColeta", back_populates="descartes")
    qrcode_token = relationship("QRCodeToken", back_populates="descarte", foreign_keys=[qrcode_token_id])
    inventario_usuario = relationship("InventarioUsuario", back_populates="descartes")
    inventario_usuario_id = Column(Integer, ForeignKey("inventario_usuario.id"), nullable=True)
    transferencia_lote = relationship("TransferenciaLote", back_populates="descartes")
