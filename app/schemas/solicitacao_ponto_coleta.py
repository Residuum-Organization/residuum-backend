"""Schemas para solicitacoes de ponto de coleta."""

from datetime import datetime
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class SolicitacaoPontoColetaCreate(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tipo_solicitante: str = Field(
        ...,
        validation_alias=AliasChoices("tipo_solicitante", "tipo_responsavel"),
        min_length=1,
        max_length=50,
    )
    documento: str = Field(..., min_length=1, max_length=30)
    responsavel_nome: str = Field(
        ...,
        validation_alias=AliasChoices("responsavel_nome", "nome_responsavel"),
        min_length=1,
        max_length=255,
    )
    responsavel_telefone: str = Field(
        ...,
        validation_alias=AliasChoices("responsavel_telefone", "telefone"),
        min_length=1,
        max_length=30,
    )
    email: str = Field(..., min_length=1, max_length=255)
    senha: str = Field(..., min_length=6, max_length=72)
    nome_ponto: str = Field(..., min_length=1, max_length=255)
    endereco: str = Field(..., min_length=1, max_length=500)
    latitude: float
    longitude: float
    horario_funcionamento: Optional[str] = Field(default=None, max_length=255)
    tipos_residuos_aceitos: List[str] = Field(default_factory=list)
    capacidade_maxima: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("capacidade_maxima", "capacidade_estimada"),
    )


class SolicitacaoPontoColetaResponse(BaseModel):
    id: int
    nome_ponto: str
    endereco: str
    status: str
    criado_em: datetime
    observacao_admin: Optional[str] = None
    motivo_rejeicao: Optional[str] = None
    ponto_coleta_id: Optional[int] = None

    class Config:
        from_attributes = True
