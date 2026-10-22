"""Modelo de vouchers."""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Voucher(Base):
    """Voucher disponivel para consulta no frontend."""

    __tablename__ = "vouchers"

    id = Column(Integer, primary_key=True, index=True)
    titulo = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)
    parceiro = Column(String(255), nullable=False)
    custo_pontos = Column(Integer, nullable=False, default=0, server_default="0")
    quantidade_disponivel = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(String(30), nullable=False, default="ativo", server_default="ativo")
    # Texto de uso escrito pelo admin; vazio usa as instrucoes padrao.
    instrucoes = Column(Text, nullable=True)
    # Dias de validade do codigo contados do resgate; vazio = sem prazo definido.
    validade_codigo_dias = Column(Integer, nullable=True)
    data_inicio = Column(DateTime(timezone=True), nullable=True)
    data_fim = Column(DateTime(timezone=True), nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    atualizado_em = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class VoucherCodigo(Base):
    """Codigo enviado pelo parceiro e cadastrado pelo admin.

    Quando o voucher tem codigos cadastrados, cada resgate entrega um deles.
    O codigo e unico no sistema todo, para nunca colidir no resgate.
    """

    __tablename__ = "voucher_codigo"

    id = Column(Integer, primary_key=True, index=True)
    voucher_id = Column(
        Integer, ForeignKey("vouchers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    codigo = Column(String(40), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default="disponivel", server_default="disponivel")
    resgate_id = Column(Integer, ForeignKey("resgate_voucher.id"), nullable=True)
    criado_em = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
