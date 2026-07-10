from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class DescarteCreate(BaseModel):
    quantidade: float
    tipo_residuo: str
    observacao: Optional[str] = "Descarte via APP"
    usuario_lat: float
    usuario_long: float
    ponto_coleta_id: int
    qrcode_token: Optional[str] = None  # Token QR Code para validação presencial (opcional)

class DescarteConfirmar(BaseModel):
    quantidade_confirmada: float

class DescarteResponse(BaseModel):
    id_descarte: int
    status: str
    quantidade: float
    data_desc: datetime

    class Config:
        from_attributes = True