"""
Configuração do Banco de Dados

Este módulo configura a conexão com o banco de dados usando SQLAlchemy.
Define o engine, a sessão e a base para os modelos.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Carrega variáveis de ambiente
load_dotenv()

# URL do banco de dados obtida das variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Crie um arquivo .env na raiz do projeto "
        "com DATABASE_URL=postgresql://usuario:senha@host:porta/banco"
    )

# Cria o engine do SQLAlchemy com a URL do banco
engine = create_engine(
    DATABASE_URL,
    echo=True  # Habilita logs das queries SQL para depuração
)

# Configura a fábrica de sessões do banco
SessionLocal = sessionmaker(
    autocommit=False,  # Não confirma automaticamente as transações
    autoflush=False,   # Não flushe automaticamente as mudanças
    bind=engine        # Vincula ao engine criado
)

# Base declarativa para definir modelos
Base = declarative_base()

def get_db():
    """
    Gerador de sessão de banco de dados.

    Fornece uma sessão para uso em dependências do FastAPI.
    Garante que a sessão seja fechada após o uso.
    """
    db = SessionLocal()
    try:
        yield db  # Retorna a sessão para o contexto
    finally:
        db.close()  # Fecha a sessão ao final