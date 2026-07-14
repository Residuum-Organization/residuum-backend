"""Schemas de sorteios."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SorteioCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    premio: str = Field(..., min_length=1, max_length=255)
    custo_pontos: int = Field(..., ge=0)
    status: str = Field("ativo", max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class SorteioUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    premio: Optional[str] = Field(None, min_length=1, max_length=255)
    custo_pontos: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class BilheteSorteioResponse(BaseModel):
    id: int
    sorteio_id: int
    numero: int
    pontos_utilizados: int
    criado_em: datetime
    titulo: Optional[str] = None
    premio: Optional[str] = None

    class Config:
        from_attributes = True


class SorteioResponse(BaseModel):
    id: int
    titulo: str
    descricao: str | None = None
    premio: str
    custo_pontos: int
    status: str
    data_inicio: datetime | None = None
    data_fim: datetime | None = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True
