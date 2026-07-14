"""Schemas de vouchers."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VoucherCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    parceiro: str = Field(..., min_length=1, max_length=255)
    custo_pontos: int = Field(..., ge=0)
    quantidade_disponivel: int = Field(0, ge=0)
    status: str = Field("ativo", max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class VoucherUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    parceiro: Optional[str] = Field(None, min_length=1, max_length=255)
    custo_pontos: Optional[int] = Field(None, ge=0)
    quantidade_disponivel: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class ResgateVoucherResponse(BaseModel):
    id: int
    voucher_id: int
    codigo: str
    pontos_utilizados: int
    status: str
    criado_em: datetime
    titulo: Optional[str] = None
    parceiro: Optional[str] = None

    class Config:
        from_attributes = True


class VoucherResponse(BaseModel):
    id: int
    titulo: str
    descricao: str | None = None
    parceiro: str
    custo_pontos: int
    quantidade_disponivel: int
    status: str
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True
