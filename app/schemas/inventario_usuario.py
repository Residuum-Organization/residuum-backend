"""Schemas do inventário pessoal de resíduos."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from app.services.identificacao_residuo_service import validar_identificacao_cadastro


class InventarioUsuarioCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_residuo: str
    quantidade: float = Field(..., gt=0)
    descricao: Optional[str] = None
    observacao: Optional[str] = None
    codigo_barras: Optional[str] = Field(default=None, max_length=64)
    sem_rotulo: bool = False

    @model_validator(mode="after")
    def validar_identificacao(self):
        self.codigo_barras = validar_identificacao_cadastro(
            self.codigo_barras,
            self.sem_rotulo,
        )
        return self


class InventarioUsuarioUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo_residuo: Optional[str] = None
    quantidade: Optional[float] = Field(default=None, gt=0)
    descricao: Optional[str] = None
    observacao: Optional[str] = None
    status: Optional[str] = None
    codigo_barras: Optional[str] = Field(default=None, max_length=64)
    sem_rotulo: Optional[bool] = None


class InventarioUsuarioTransferir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quantidade: float = Field(..., gt=0)
    ponto_coleta_id: int
    usuario_lat: float = Field(..., ge=-90, le=90)
    usuario_long: float = Field(..., ge=-180, le=180)
    usuario_precisao: Optional[float] = Field(default=None, ge=0)
    observacao: Optional[str] = "Transferência via inventário do usuário"


class InventarioLoteItem(BaseModel):
    item_id: int
    quantidade: float = Field(..., gt=0)


class InventarioLoteTransferir(BaseModel):
    model_config = ConfigDict(extra="forbid")

    itens: list[InventarioLoteItem] = Field(..., min_length=1, max_length=100)
    ponto_coleta_id: int
    usuario_lat: float = Field(..., ge=-90, le=90)
    usuario_long: float = Field(..., ge=-180, le=180)
    usuario_precisao: Optional[float] = Field(default=None, ge=0)
    chave_idempotencia: str = Field(..., min_length=8, max_length=128)
    observacao: Optional[str] = "Transferência em lote do inventário do usuário"

    @model_validator(mode="after")
    def validar_itens_unicos(self):
        ids = [item.item_id for item in self.itens]
        if len(ids) != len(set(ids)):
            raise ValueError("Cada item pode aparecer apenas uma vez na transferência.")
        return self


class TransferenciaLoteResponse(BaseModel):
    id: str
    status: str
    ponto_coleta_id: int
    ponto_coleta_nome: str
    total_itens: int
    peso_total: float
    pontos_estimados: int
    descarte_ids: list[int]
    data_criacao: datetime


class InventarioUsuarioResponse(BaseModel):
    id: int
    usuario_id: int
    tipo_residuo: str
    quantidade: float
    quantidade_reservada: float
    descricao: Optional[str]
    observacao: Optional[str]
    codigo_barras: Optional[str]
    sem_rotulo: bool
    status: str
    data_cadastro: datetime
    data_atualizacao: datetime

    @computed_field
    @property
    def quantidade_disponivel(self) -> float:
        return max(float(self.quantidade or 0) - float(self.quantidade_reservada or 0), 0)

    class Config:
        from_attributes = True
