"""
Schemas para rotas administrativas.
"""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class UpdateRoleRequest(BaseModel):
    role: Literal["usuario", "cooperativa", "admin"]


class AjustePontuacaoRequest(BaseModel):
    delta: int = Field(..., description="Valor a somar (positivo) ou subtrair (negativo) da pontuação")
    motivo: str = Field(..., min_length=3, max_length=255)


class UsuarioAdminUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None


class RejeitarDescarteRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=255)


class ReverterDescarteRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=255)


class AprovarSolicitacaoPontoColetaRequest(BaseModel):
    observacao: Optional[str] = Field(default=None, max_length=500)


class RejeitarSolicitacaoPontoColetaRequest(BaseModel):
    motivo: str = Field(..., min_length=3, max_length=500)
