"""Schemas de pontuacao e extrato de pontos."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PontuacaoCreate(BaseModel):
    """Modelo legado para criação manual de pontuação."""

    pontos: int


class PontuacaoResgateCreate(BaseModel):
    """Payload para registrar um resgate de pontos do usuario."""

    pontos: int = Field(..., gt=0, description="Quantidade de pontos a consumir no resgate")
    descricao: str = Field(..., min_length=3, max_length=255)
    referencia: Optional[str] = Field(default=None, max_length=255)


class ResgatePontuacaoResponse(BaseModel):
    """Resposta padrao de um resgate de pontuacao."""

    id_resgate: int
    usuario_id: int
    pontos_utilizados: int
    descricao: str
    referencia: Optional[str]
    status: str
    data_resgate: datetime

    class Config:
        from_attributes = True


class ExtratoPontosItemResponse(BaseModel):
    """Item do extrato consolidado de pontos do usuario."""

    origem: str
    status: str
    data_evento: datetime
    pontos: int
    descricao: Optional[str] = None
    referencia: Optional[str] = None
    quantidade: Optional[float] = None
    tipo_residuo: Optional[str] = None
    ponto_coleta_id: Optional[int] = None
    ponto_coleta_nome: Optional[str] = None
    ponto_coleta_endereco: Optional[str] = None
    id_descarte: Optional[int] = None
    id_resgate: Optional[int] = None
    inventario_usuario_id: Optional[int] = None
    inventario_item_descricao: Optional[str] = None


class ExtratoPontosResponse(BaseModel):
    """Resposta do extrato consolidado de pontos."""

    pontuacao_total: int
    itens: list[ExtratoPontosItemResponse]
