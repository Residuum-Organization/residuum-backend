"""
Schemas para Ponto de Coleta

Define os modelos Pydantic para criação, atualização e resposta de pontos de coleta.
"""

from pydantic import BaseModel, Field
from datetime import datetime, time
from typing import Optional, Dict, Any, List


TIPOS_RESIDUOS_EXEMPLO = [
    "plastico",
    "papel",
    "papelao",
    "metal",
    "vidro",
    "aluminio",
    "cobre",
    "pilhas",
    "baterias",
]

class HorarioBase(BaseModel):
    dia_semana: int = Field(..., ge=0, le=6, description="0=Dom, 1=Seg, 2=Ter, 3=Qua, 4=Qui, 5=Sex, 6=Sáb")
    hora_abertura: time
    hora_fechamento: time

class HorarioCreate(HorarioBase):
    pass

class HorarioResponse(HorarioBase):
    id: int
    ponto_coleta_id: int

    class Config:
        from_attributes = True
        
class PontoColetaCreate(BaseModel):
    """Modelo para criação de um novo ponto de coleta."""
    nome: str
    endereco: Optional[str] = None
    latitude: float
    longitude: float
    raio_operacao: Optional[float] = 1000.0
    capacidade_maxima: Optional[float] = Field(default=None, description="Capacidade máxima estimada em kg")
    tipos_residuos_aceitos: Optional[List[str]] = Field(default=None, description="Tipos de resíduos aceitos pelo ponto")
    horario_funcionamento: Optional[str] = None
    status: Optional[str] = Field(default="ativo", description="ativo, cheio ou inativo")
    data_final: Optional[datetime] = Field(default=None, description="Data limite para pontos temporários")
    cooperativa_id: Optional[int] = Field(default=None, description="Usuário com role=cooperativa responsável pelo ponto")

class PontoColetaUpdate(BaseModel):
    """Modelo para atualização de um ponto de coleta."""
    nome: Optional[str] = None
    endereco: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raio_operacao: Optional[float] = None
    capacidade_maxima: Optional[float] = None
    tipos_residuos_aceitos: Optional[List[str]] = None
    horario_funcionamento: Optional[str] = None
    status: Optional[str] = None
    ativo: Optional[int] = None
    data_final: Optional[datetime] = None
    cooperativa_id: Optional[int] = None

class PontoColetaResponse(BaseModel):
    """Modelo de resposta para um ponto de coleta."""
    id: int
    nome: str
    endereco: Optional[str]
    latitude: float
    longitude: float
    raio_operacao: float
    capacidade_maxima: Optional[float] = None
    tipos_residuos_aceitos: List[str] = []
    status: str = "ativo"
    status_calculado: Optional[str] = None
    cooperativa_id: Optional[int] = None
    inventario: Dict[str, Any]
    total_inventario: Optional[float] = None
    percentual_ocupacao: Optional[float] = None
    distancia_km: Optional[float] = None
    ativo: int
    data_criacao: datetime
    data_atualizacao: datetime
    data_final: Optional[datetime] = None
    horarios: List[HorarioResponse] = []
    class Config:
        from_attributes = True


class VolumePorTipoPontoColeta(BaseModel):
    """Volume acumulado por tipo de residuo no inventario atual do ponto."""
    tipo_residuo: str
    quantidade: float


class HistoricoRecentePontoColeta(BaseModel):
    """Evento recente confirmado para exibicao no dashboard operacional."""
    id: int
    usuario_id: Optional[int] = None
    tipo_residuo: Optional[str] = None
    quantidade: float
    status: str
    data: Optional[datetime] = None


class PontoColetaDashboardResponse(BaseModel):
    """Resposta consolidada para dashboard operacional do ponto de coleta."""
    ponto_id: int
    nome: str
    endereco: Optional[str] = None
    status: str
    capacidade_maxima: Optional[float] = None
    quantidade_total: float
    percentual_ocupacao: float
    status_capacidade: str
    volume_por_tipo: List[VolumePorTipoPontoColeta] = Field(default_factory=list)
    usuarios_atendidos: int
    descartes_pendentes: int
    historico_recente: List[HistoricoRecentePontoColeta] = Field(default_factory=list)
