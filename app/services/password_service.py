"""Password hashing helpers shared by authentication and onboarding flows."""

from passlib.context import CryptContext


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_senha(senha: str) -> str:
    """Hash a password while respecting bcrypt's 72-byte input limit."""
    return pwd_context.hash(senha[:72])


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Check a plain-text password against a stored bcrypt hash."""
    return pwd_context.verify(senha[:72], senha_hash)
