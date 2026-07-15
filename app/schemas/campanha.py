"""Schemas de campanhas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CampanhaCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    patrocinador: str = Field(..., min_length=1, max_length=255)
    patrocinador_logo_url: Optional[str] = Field(default=None, max_length=500)
    pontos_recompensa: int = Field(0, ge=0)
    status: str = Field("ativa", max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CampanhaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    patrocinador: Optional[str] = Field(None, min_length=1, max_length=255)
    patrocinador_logo_url: Optional[str] = Field(default=None, max_length=500)
    pontos_recompensa: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CampanhaResponse(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    patrocinador: str
    patrocinador_logo_url: Optional[str] = None
    pontos_recompensa: int
    status: str
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class InscricaoCampanhaResponse(BaseModel):
    id: int
    campanha_id: int
    pontos_concedidos: int
    criado_em: datetime
    titulo: Optional[str] = None
    patrocinador: Optional[str] = None

    class Config:
        from_attributes = True
