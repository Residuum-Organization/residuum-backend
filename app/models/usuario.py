"""
Modelo de Usuário

Define a estrutura da tabela 'usuario' no banco de dados.
Representa um usuário do sistema com informações pessoais e autenticação.
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Usuario(Base):
    """
    Modelo SQLAlchemy para a tabela de usuários.

    Contém dados pessoais, credenciais e relacionamento com endereço.
    """
    __tablename__ = "usuario"

    # Chave primária
    id = Column(Integer, primary_key=True, index=True)

    # Dados pessoais
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)  # Email único para login
    telefone = Column(String, nullable=False)

    # Credenciais de segurança
    senha_hash = Column(String, nullable=False)  # Senha hasheada com bcrypt

    # Pontuação acumulada do usuário
    pontuacao_total = Column(Integer, default=0)

    role = Column(String, nullable=False, default="usuario", server_default="usuario")

    # Relacionamento com endereço e outras tabelas
    endereco_id = Column(Integer, ForeignKey("endereco.id_end"))
    endereco = relationship("Endereco")
    pontuacoes = relationship("Pontuacao", back_populates="usuario")
    resgates_pontuacao = relationship("ResgatePontuacao", back_populates="usuario")
    descartes = relationship("Descarte", back_populates="usuario")
    inventarios = relationship("InventarioUsuario", back_populates="usuario")
