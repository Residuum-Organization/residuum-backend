"""
Modelo de Endereço

Define a estrutura da tabela 'endereco' no banco de dados.
Armazena informações de localização dos usuários.
"""

from sqlalchemy import Column, Integer, String
from app.database import Base

class Endereco(Base):
    """
    Modelo SQLAlchemy para a tabela de endereços.

    Contém os componentes de um endereço residencial.
    """
    __tablename__ = "endereco"

    # Chave primária (id_end para diferenciar de id padrão)
    id_end = Column(Integer, primary_key=True, index=True)

    # Componentes do endereço
    rua = Column(String)
    bairro = Column(String)
    numero = Column(Integer)
    cep = Column(String)
    cidade = Column(String)