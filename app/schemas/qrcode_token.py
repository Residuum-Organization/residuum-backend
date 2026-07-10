"""
Schemas para QR Code Token

Define os modelos Pydantic para criação e validação de tokens QR Code.
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class QRCodeTokenCreate(BaseModel):
    """Modelo para criação de um novo token QR Code."""
    ponto_coleta_id: int


class QRCodeTokenValidate(BaseModel):
    """Modelo para validação de um token QR Code."""
    token: str


class QRCodeTokenResponse(BaseModel):
    """Modelo de resposta para um token QR Code."""
    id: int
    token: str
    ponto_coleta_id: int
    data_geracao: datetime
    data_expiracao: datetime
    ativo: int

    class Config:
        from_attributes = True
