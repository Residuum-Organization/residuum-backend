"""
Schemas de Usuário

Define os modelos Pydantic para criação e manipulação de usuários.
"""

from pydantic import BaseModel, EmailStr, Field


class UsuarioCreate(BaseModel):
    """Modelo para criação de um novo usuário."""

    nome: str = Field(..., min_length=2, description="Nome deve ter pelo menos 2 caracteres")
    email: EmailStr = Field(..., description="Email deve ser um endereço de email válido")
    telefone: str = Field(..., min_length=8, description="Telefone deve ter no mínimo 8 caracteres")
    senha: str = Field(..., min_length=6, description="Senha deve ter no mínimo 6 caracteres")

class UsuarioUpdate(BaseModel):
    """Modelo para atualizacao dos dados basicos do usuario autenticado."""

    nome: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    telefone: str | None = Field(default=None, min_length=8)
