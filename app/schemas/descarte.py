"""Schemas do fluxo de descarte."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DescarteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantidade: float = Field(..., gt=0)
    tipo_residuo: str
    observacao: Optional[str] = "Descarte via APP"
    usuario_lat: float = Field(..., ge=-90, le=90)
    usuario_long: float = Field(..., ge=-180, le=180)
    usuario_precisao: Optional[float] = Field(default=None, ge=0)
    ponto_coleta_id: int


class DescarteConfirmar(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantidade_confirmada: float = Field(..., gt=0)
    codigo_barras_validado: Optional[str] = Field(default=None, max_length=64)
    sem_rotulo: bool = False
    identificacao_manual: Optional[str] = Field(default=None, max_length=255)


class DescarteResponse(BaseModel):
    id_descarte: int
    status: str
    quantidade: float
    data_desc: datetime

    class Config:
        from_attributes = True
