from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field

class AgendaCreate(BaseModel):
    ponto_coleta_id: int
    data: date
    turno_id: str = Field(..., max_length=50)

class AgendaUpdate(BaseModel):
    ponto_coleta_id: Optional[int] = None
    data: Optional[date] = None
    turno_id: Optional[str] = Field(None, max_length=50)
    status: Optional[str] = Field(None, max_length=50)

class AgendaResponse(BaseModel):
    id: int
    ponto_coleta_id: int
    data: date
    turno_id: str
    status: str
    criado_em: datetime

    class Config:
        from_attributes = True
