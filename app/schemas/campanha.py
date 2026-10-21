"""Schemas de campanhas."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Acesso = Literal["publica", "privada"]
PapelRequisito = Literal["entrada", "missao"]


class RequisitoInput(BaseModel):
    papel: PapelRequisito
    descricao: Optional[str] = Field(default=None, max_length=255)
    tipo_residuo: Optional[str] = Field(default=None, max_length=50)
    codigos_barras: list[str] = Field(default_factory=list)
    quantidade: int = Field(..., ge=1)

    @field_validator("tipo_residuo", mode="before")
    @classmethod
    def _limpar_tipo(cls, valor):
        if isinstance(valor, str):
            return valor.strip() or None
        return valor

    @field_validator("codigos_barras", mode="before")
    @classmethod
    def _limpar_codigos(cls, valor):
        if valor is None:
            return []
        limpos = []
        for codigo in valor:
            texto = str(codigo).strip()
            if texto and texto not in limpos:
                limpos.append(texto)
        return limpos


class RequisitoResponse(RequisitoInput):
    id: int

    class Config:
        from_attributes = True


class CampanhaCreate(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descricao: Optional[str] = None
    patrocinador: str = Field(..., min_length=1, max_length=255)
    patrocinador_logo_url: Optional[str] = Field(default=None, max_length=500)
    pontos_recompensa: int = Field(0, ge=0)
    acesso: Acesso = "publica"
    condicoes: Optional[str] = None
    requisitos: list[RequisitoInput] = Field(default_factory=list)
    status: str = Field("ativa", max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CampanhaUpdate(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    patrocinador: Optional[str] = Field(None, min_length=1, max_length=255)
    patrocinador_logo_url: Optional[str] = Field(default=None, max_length=500)
    pontos_recompensa: Optional[int] = Field(None, ge=0)
    acesso: Optional[Acesso] = None
    condicoes: Optional[str] = None
    # None mantém os requisitos atuais; uma lista (mesmo vazia) substitui todos.
    requisitos: Optional[list[RequisitoInput]] = None
    status: Optional[str] = Field(None, max_length=30)
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None


class CampanhaResponse(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str] = None
    patrocinador: str
    patrocinador_logo_url: Optional[str] = None
    pontos_recompensa: int
    acesso: str = "publica"
    condicoes: Optional[str] = None
    requisitos: list[RequisitoResponse] = Field(default_factory=list)
    status: str
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    criado_em: datetime
    atualizado_em: datetime

    class Config:
        from_attributes = True


class InscricaoCampanhaResponse(BaseModel):
    id: int
    campanha_id: int
    pontos_concedidos: int
    criado_em: datetime
    titulo: Optional[str] = None
    patrocinador: Optional[str] = None

    class Config:
        from_attributes = True


class RequisitoProgresso(BaseModel):
    id: int
    papel: str
    descricao: Optional[str] = None
    tipo_residuo: Optional[str] = None
    codigos_barras: list[str] = Field(default_factory=list)
    quantidade: int
    atual: int
    cumprido: bool


class CampanhaProgressoResponse(BaseModel):
    campanha_id: int
    acesso: str
    participando: bool
    entrada: list[RequisitoProgresso]
    missoes: list[RequisitoProgresso]
    entrada_cumprida: bool
    missoes_cumpridas: bool
    acesso_liberado: bool
    pode_participar: bool
    recompensa_pontos: int
    recompensa_disponivel: bool
    recompensa_concedida: bool
