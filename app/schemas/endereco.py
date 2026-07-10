"""
Schemas de Endereço

Define os modelos Pydantic para criação e manipulação de endereços.
Usados na validação de dados de endereço nas APIs.
"""

from pydantic import BaseModel, field_validator

class EnderecoCreate(BaseModel):
    """
    Modelo para criação de um novo endereço.

    Contém todos os campos necessários para registrar um endereço.
    """
    rua: str
    bairro: str
    numero: int
    cep: str
    cidade: str

    @field_validator("cep")
    @classmethod
    def normalizar_cep(cls, v: str) -> str:
        cep_limpo = v.replace("-", "").strip()
        if len(cep_limpo) != 8 or not cep_limpo.isdigit():
            raise ValueError("CEP deve conter 8 dígitos numéricos.")
        return cep_limpo