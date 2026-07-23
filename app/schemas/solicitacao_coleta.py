from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SolicitacaoColetaCreate(BaseModel):
    cooperativa_id: int = Field(..., gt=0)
    observacao: Optional[str] = None


class SolicitacaoColetaRecusar(BaseModel):
    motivo: str = Field(..., min_length=1, max_length=500)


class SolicitacaoColetaResponse(BaseModel):
    id: int
    admin_id: int
    cooperativa_id: int
    ponto_coleta_id: int
    status: str
    percentual_ocupacao: Optional[float] = None
    quantidade_inventario: float
    inventario_solicitado: Dict[str, Any]
    quantidade_coletada: Optional[float] = None
    capacidade_maxima: Optional[float] = None
    observacao: Optional[str] = None
    motivo_recusa: Optional[str] = None
    data_solicitacao: datetime
    data_aceite: Optional[datetime] = None
    data_conclusao: Optional[datetime] = None
    data_atualizacao: datetime

    class Config:
        from_attributes = True
