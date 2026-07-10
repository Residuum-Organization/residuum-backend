"""
Schemas do Inventário do Usuário.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, computed_field


class InventarioUsuarioCreate(BaseModel):
    tipo_residuo: str
    quantidade: float = Field(..., gt=0)
    descricao: Optional[str] = None
    observacao: Optional[str] = None


class InventarioUsuarioUpdate(BaseModel):
    tipo_residuo: Optional[str] = None
    quantidade: Optional[float] = Field(default=None, gt=0)
    descricao: Optional[str] = None
    observacao: Optional[str] = None
    status: Optional[str] = None


class InventarioUsuarioTransferir(BaseModel):
    quantidade: float = Field(..., gt=0)
    ponto_coleta_id: int
    usuario_lat: float
    usuario_long: float
    observacao: Optional[str] = "Transferência via inventário do usuário"
    qrcode_token: Optional[str] = None


class InventarioUsuarioResponse(BaseModel):
    id: int
    usuario_id: int
    tipo_residuo: str
    quantidade: float
    quantidade_reservada: float
    descricao: Optional[str]
    observacao: Optional[str]
    status: str
    data_cadastro: datetime
    data_atualizacao: datetime

    @computed_field
    @property
    def quantidade_disponivel(self) -> float:
        return max(float(self.quantidade or 0) - float(self.quantidade_reservada or 0), 0)

    class Config:
        from_attributes = True
